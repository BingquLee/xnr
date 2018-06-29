#!/usr/bin/env python
# encoding: utf-8

# 确定能够爬取哪些字段（至少需要：标题、正文、发布时间、发布者、url）

import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
# from lxml import etree
import json
from newspaper import Article
from pybloom import BloomFilter   # pip install pybloom
import re
from readability.readability import Document    #pip install readability-lxml
import os
from bs4 import BeautifulSoup
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

driver = webdriver.Chrome()
#driver = webdriver.Firefox()
driver.get('http://weixin.sogou.com/')
time.sleep(1)
driver.find_element_by_xpath('//a[@id="loginBtn"]').click()
time.sleep(10)

req = requests.Session()
cookies = driver.get_cookies()
for cookie in cookies:
	req.cookies.set(cookie['name'],cookie['value'])

headers = {
	'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
	'Connection':'keep-alive',
	'Accept-Language':'zh-CN,zh;q=0.8,en;q=0.6',
	'Host':'weixin.sogou.com',
	'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
}

# 根据关键词找文章
offset = 101
keyword_list = []
startDate_list = []
endDate_list = []

b = BloomFilter(capacity=100000,error_rate=0.001)
with open('keyword.txt','rb') as fr:
	for f in fr.readlines():
		keywords_para = f.decode('utf-8').strip().split('|')

		keyword_list.append(keywords_para[0])
		startDate_list.append(keywords_para[1])
		endDate_list.append(keywords_para[2])

for k in range(0,len(keyword_list)):
	print 'begin'
	wz_list = []
	startDate = startDate_list[k]
	endDate = endDate_list[k]
	try:
		search_wz_url = 'http://weixin.sogou.com/weixin?type=2&query=' + keyword_list[k] + '&page=1'
		driver.get(search_wz_url)
		time.sleep(1)
		driver.find_element_by_xpath('//div[@id="tool_show"]/a').click()
		driver.find_element_by_xpath('//a[@id="time"]').click()
		driver.find_element_by_xpath('//input[@id="date_start"]').clear()
		driver.find_element_by_xpath('//input[@id="date_start"]').send_keys(startDate)
		driver.find_element_by_xpath('//input[@id="date_end"]').clear()
		driver.find_element_by_xpath('//input[@id="date_end"]').send_keys(endDate)
		driver.find_element_by_xpath('//a[@id="time_enter"]').click()
		wait = WebDriverWait(driver,10)
	except:
		time.sleep(20)
	for i in range(2,offset):
		# 无结果跳过此关键词
		try:
			driver.find_element_by_xpath('//div[@id="noresult_part1_container"]')
			break
		except:
			pass
		# 遇到验证码暂停15秒
		try:
			driver.find_element_by_xpath('//img[@id="seccodeImage"]')
			time.sleep(15)
		except Exception as e:
			# 无下一页跳过此关键词
			try:
				driver.find_element_by_xpath('//a[@id="sogou_next"]')
			except:
				print("break")
				break
		finally:
			for url in [each.find_element_by_xpath('./h3/a').get_attribute('href') for each in driver.find_elements_by_xpath('//ul[@class="news-list"]/li/div[2]')]:
				wz_list.append(url)

			try:
				driver.find_element_by_xpath('//a[@id="sogou_page_%d"]'%i).click()
			except Exception as e:
				pass
			time.sleep(1)


	for url in wz_list:
		try:
			driver.get(url)
			article = Article(url)
			article.download()
			article.parse()
			title = article.title

			try:
				da = driver.find_element_by_xpath('//div[@id="img-content"]/div[1]/em')
				date = da.text
			except Exception as e:
				da = driver.find_element_by_xpath('//span[@id="publish_time"]')
				date = da.text
			try:
				gz = driver.find_element_by_xpath('//div[@id="img-content"]/div[1]/a')
				gzh = gz.text
			except Exception as e:
				try:
					gzh = driver.find_element_by_xpath('//strong[@class="account_nickname_inner"]').text
				except:
					gzh = driver.find_element_by_xpath('//span[@id="profileBt"]').text
			try:
				doc = Document(driver.find_element_by_xpath('//div[@id="img-content"]').text)
				content = doc.summary().replace('<html><body><div><body id=\"readabilityBody\"><p>','').replace('</p></body></div></body></html>','').replace('\n','')
			except Exception as e:
				driver.find_element_by_xpath('//a[@id="js_share_source"]').click()
				doc = Document(driver.find_element_by_xpath('//div[@id="js_content"]').text)
				content = doc.summary().replace('<html><body><div><body id=\"readabilityBody\"><p>','').replace('</p></body></div></body></html>','').replace('\n','')

			wz_url = url

			wz_dict = {}
			wz_dict.update({'keyword':keyword_list[k],'title':title,'date':date,'gzh':gzh,'content':content,'url':wz_url})
			with open(keyword_list[k]+'.json','a+') as f:
				f.write(json.dumps(wz_dict,ensure_ascii=False) + '\n')
		except Exception as e:
			print(e)

print 'end'






