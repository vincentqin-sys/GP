# -*- coding: utf-8 -*-

import requests, json, time, random, datetime, os, subprocess
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import base64

#CHROME_PORT = random.randint(5000, 35000)
CHROME_PORT = 95273

headers = {
        "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
        "Content-Type" : "application/json;charset=UTF-8",
        #"Origin": "http://10.99.9.26:2080"
    }

driver = None
def init():
    cmd = f'chrome.exe  --remote-debugging-port={CHROME_PORT}'
    # chrome --remote-debugging-port=95273 "http://xxx"
    #os.system(cmd)
    #pp = subprocess.Popen(args = cmd)
    #print(pp)
    time.sleep(3)
    global driver
    options = webdriver.ChromeOptions()
    #options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.debugger_address = f"127.0.0.1:{CHROME_PORT}"
    driver = webdriver.Chrome( options = options)
    print('driver=', driver)
    #driver.get('http://www.iwencai.com/unifiedwap/result?w=个股热度排名<%3D200且个股热度从大到小排名&querytype=stock&&addSign=1684401939179')
    #time.sleep(8)

# return JSON object
def loadCode(code):
    js = 'return getdUrl_henxin(arguments[0])'
    up = '17' if code[0] == '6' else '33'
    url = f'http://d.10jqka.com.cn/v6/line/{up}_{code}/01/last1800.js'
    url = driver.execute_script(js, url)
    resp = requests.get(url) # , headers = headers
    if resp.status_code != 200:
        print('loadCode Fail: ', resp.status_code, 'code=', code)
        return None
    txt = resp.text
    begin = txt.index('(')
    end = txt.index(')')
    txt = txt[begin + 1 : end]
    rs = json.loads(txt)
    return rs

def main():
    init()
    
    data = loadCode('600310')
    print(data)
    
    driver.quit()
   

if __name__ == '__main__':
    main()
    pass