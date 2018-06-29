#!"D:\Documents\WeChat Files\BingquLee\Files\baidu_news\venv\Scripts\python.exe"
# EASY-INSTALL-ENTRY-SCRIPT: 'tldextract==1.5.1','console_scripts','tldextract'
__requires__ = 'tldextract==1.5.1'
import re
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw?|\.exe)?$', '', sys.argv[0])
    sys.exit(
        load_entry_point('tldextract==1.5.1', 'console_scripts', 'tldextract')()
    )
