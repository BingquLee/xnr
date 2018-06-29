# -*- coding: utf-8 -*-

import re
import time
from bs4 import BeautifulSoup, SoupStrainer
from retry import retry
from selenium import webdriver
from urllib import quote
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
import math
import datetime
import os
import json
import sys

reload(sys)
sys.setdefaultencoding("utf-8")

name = "baidu_ns_search"
keywords_file_list = ["keyword.txt"]

HOST_URL = "http://news.baidu.com"
LIST_URL = "http://news.baidu.com/ns?word={keyword}&pn={page}&cl=2&ct=1&tn=newsdy&rn=100&ie=utf-8&bt={start_ts}&et={end_ts}"


# scrapy recent data
class Spider(object):
    def __init__(self):
        self.spiders = []
        # self.client = webdriver.Firefox()
        self.client = webdriver.Chrome()
        print 'start'
        for keywords_file in keywords_file_list:
            print keywords_file, "begin"
            self.keywords = []
            self.start_datetime = []
            self.end_datetime = []
            f = open('./source/' + keywords_file)
            for line in f.readlines():
                keywords_para = line.decode('utf-8').strip().split('|')
                keywords = keywords_para[0]
                start_datetime = keywords_para[1]
                end_datetime = keywords_para[2]

                self.keywords.append(keywords)
                self.start_datetime.append(start_datetime)
                self.end_datetime.append(end_datetime)

            f.close()

            for i in range(len(self.keywords)):
                keyword = self.keywords[i]
                start_datetime = self.start_datetime[i]
                end_datetime = self.start_datetime[i]
                self.start_ts = self.datetime2ts(start_datetime)
                self.end_ts = self.datetime2ts(end_datetime)
                self.source_website = name
                self.category = keywords_file

                for page in range(0, 1000, 10):
                    print page
                    search_url = self.get_search_url(self.start_ts, self.end_ts, keyword, page)
                    print keyword, search_url
                    self.client.get(search_url)
                    soup = BeautifulSoup(self.client.page_source, "lxml")
                    # hits
                    hits = 0
                    nums_span = soup.find('span', {'class': 'nums'})
                    if nums_span:
                        try:
                            hits = int(
                                re.search(r'闻(.*?)篇', nums_span.text.encode('utf-8')).group(1).replace('约', '').decode(
                                    'utf8').replace(',', ''))
                        except:
                            hits = None
                    # items
                    items = []
                    content_left = soup.find('div', {'id': 'content_left'})
                    if content_left:
                        result_lis = content_left.findAll('div', {'class': 'result'})
                        if len(result_lis) == 0:
                            break
                        for li in result_lis:
                            title = li.find('h3', {'class': 'c-title'}).find('a').text
                            url = li.find('h3', {'class': 'c-title'}).find('a').get('href')
                            id = url
                            summary_div = li.find('div', {'class': 'c-summary c-row '})

                            if not summary_div:
                                summary_div = li.find('div', {'class': 'c-summary c-row c-gap-top-small'})

                            author_div = summary_div.find('p', {'class': 'c-author'})
                            author_div_text = author_div.text
                            author_div_splits = author_div_text.split()
                            if len(author_div_splits) == 2:
                                author = author_div_splits[0]
                                datetime_replace = author_div_splits[1]
                            else:
                                author = author_div_splits[0]
                                datetime_replace = author_div_splits[1] + ' ' + author_div_splits[2]

                            if u'小时前' in datetime_replace:
                                now_ts = time.time()
                                hour = int(datetime_replace.rstrip(u'小时前'))
                                timestamp = now_ts - hour * 3600
                                datetime = self.ts2datetime(timestamp)
                            elif u'分钟前' in datetime_replace:
                                now_ts = time.time()
                                minute = int(datetime_replace.rstrip(u'分钟前'))
                                timestamp = now_ts - minute * 60
                                datetime = self.ts2datetime(timestamp)
                            else:
                                datetime_re = datetime_replace.replace('  ', ' ')
                                datetime_year = datetime_re.replace(u'年', '-')
                                datetime_month = datetime_year.replace(u'月', '-')
                                datetime = datetime_month.replace(u'日', '')
                                try:
                                    timestamp = self.datetimeshort2ts(datetime)
                                except:
                                    print "datetime format error"

                            date = self.ts2date(timestamp)
                            # print '=====================================',summary_div
                            str_all = ''
                            str_list = str(summary_div).split('\n')
                            for temp in str_list:
                                str_all += temp

                            summary = re.findall(r'</p>(.*?)<a', str_all)
                            # print '-------------------------------------',summary
                            if summary:
                                summary = summary[0].decode('utf-8').replace('<em>', '').replace('</em>', '').replace(
                                    '<span class="c-info">', '')

                            more_same_link = None
                            same_news_num = 0
                            c_more_link_a = summary_div.find('a', {'class': 'c-more_link'})
                            if c_more_link_a:
                                more_same_link = HOST_URL + c_more_link_a.get('href')
                                # same_news_num = int(c_more_link_a.text.replace(u"条相同新闻",'').strip())
                                same_news_num = c_more_link_a.text.replace(u"条相同新闻", '').strip()
                            relative_news = None
                            # print same_news_num

                            news_item = {'_id': id, 'id': id, 'title': title, 'url': url, \
                                         'user_name': author, 'timestamp': timestamp, 'datetime': datetime, \
                                         'date': date, 'summary': summary, 'source_website': self.source_website,
                                         'category': self.category, 'same_news_num': same_news_num,
                                         'more_same_link': more_same_link, \
                                         'relative_news': relative_news}
                            self.write_item(news_item, keyword)

                        page_p = soup.find('p', {'id': 'page'})
                        if page_p:
                            n_as = page_p.findAll('a', {'class': 'n'})
                            # print n_as[-1].text, n_as[-1].text.replace('>', '') == u'下一页'
                            if len(n_as) > 0:
                                if n_as[-1].text.replace('>', '') == u'下一页':
                                    continue
                                else:
                                    break
                            else:
                                break
        print 'end'
        self.client.close()

    @retry()
    def get_search_url(self, start_ts, end_ts, keyword, page):
        return LIST_URL.format(start_ts=start_ts, end_ts=end_ts, keyword=keyword, page=page)

    def datetimeshort2ts(self, date):
        return int(time.mktime(time.strptime(date, '%Y-%m-%d %H:%M')))

    def datetime2ts(self, date):
        return int(time.mktime(time.strptime(date, '%Y-%m-%d %H:%M:%S')))

    def date2ts(self, date):
        return int(time.mktime(time.strptime(date, '%Y-%m-%d')))

    def ts2date(self, ts):
        return time.strftime('%Y-%m-%d', time.localtime(ts))

    def ts2datetime(self, ts):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))

    def write_item(self, item, keyword):
        print '--------save-----------'
        with open(keyword + '.json', 'a+') as f:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def main():
    s = Spider()


def date2ts(self, date):
    return int(time.mktime(time.strptime(date, '%Y-%m-%d')))


if __name__ == '__main__':
    print 'begin'
    main()
    print 'end'
