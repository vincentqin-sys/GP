import sqlite3
from time import sleep
from selenium import webdriver
import traceback

options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])

browser = webdriver.Chrome( options = options)
# browser.implicitly_wait(30)  # 隐性等待，最长等30秒
# open mysql
db = sqlite3.connect('hgt.db')

def formatMoney(text):
    lastChar = text[-1:]
    money = float(text[0: -1])

    if lastChar == '亿':
        money = money * 10000
    elif lastChar != '万':
        input('Format money error: ' + text)
    return int(money)

def alreadyExists(code, day):
    cursor = db.cursor()
    sql = 'select id, zj from hgtacc where code = "{0}" and day = {1} '.format(code, day)
    cursor.execute(sql)
    res = cursor.fetchall()
    if len(res) == 0:
        return 0
    zj = int(res[0][1])
    if zj != 0:
        return -1
    return res[0][0]

def existsCode(code):
    cursor = db.cursor()
    sql = 'select count(*) from hgtacc where code = "{0}"  '.format(code)
    cursor.execute(sql)
    res = cursor.fetchall()
    cc = int(res[0][0])
    return cc > 0

def saveMysql(data, day):
    num = 0
    cursor = db.cursor()
    for v in data:
        # skip not exists code
        #if (not existsCode(v['code'])) and (v['zsz'] < 800): # 总市值小于 800 亿
        #    print('    skip {}'.format(v))
        #   continue
        id = alreadyExists(v['code'], day)
        if id == -1:
            print('    exists {}'.format(v))
            continue
        elif id == 0:
            sql = 'insert into hgtacc (day, code, zj, zsz) values ({0}, "{1}", {2}, {3}) '.format( day, v['code'], formatMoney(v['zj']), v['zsz'])
        else:
            sql = 'update hgtacc set zj = {}, zsz = {} where id = {}'.format(formatMoney(v['zj']), v['zsz'], id)
        print('[{}] update {}'.format(num, v))
        num += 1
        cursor.execute(sql)

    db.commit()
    return True

def queryLastDay():
    cursor = db.cursor()
    sql = 'select max(day) from hgtacc'
    cursor.execute(sql)
    res = cursor.fetchall()
    # if len(res) == 1 and len(res[0]) == 1:
    if res[0][0] is not None:
        return res[0][0]
    return 20230101


def load_gj_table():
    div = browser.find_element_by_class_name('dataview-body')
    table = div.find_element_by_tag_name('table')
    trs = table.find_elements_by_xpath('.//tbody/tr')
    data = []
    for tr in trs:
        row = {}
        tds = tr.find_elements_by_xpath('.//td')
        row['code'] = tds[1].find_element_by_xpath('.//a').text
        row['name'] = tds[2].find_element_by_xpath('.//a').text
        row['zj'] = tds[11].find_element_by_xpath('.//span').text
        sz = tds[7].text
        if sz[-1:] != '亿' :
            continue
        sz = float(sz[0: -1])
        bl = float(tds[8].text[0:-1])
        row['zsz'] = int(sz * 100 / bl) # 总市值. 亿
        
        data.append(row)
    return data


def main(auto):
    lastDay = queryLastDay()
    if lastDay == False:
        return

    # 沪深港通持股 估计
    browser.get('http://data.eastmoney.com/hsgtcg/list.html')
    # sleep(10)
    # input('Press Enter key to Load Day')
    day = browser.find_element_by_class_name('title').find_element_by_tag_name('span').text[1: -1]
    print('Fetch acc day:', day)
    dayi = day.replace('-', '')
    if len(dayi) != 8:
        input('Load day error.')
        return
        
    sleep(3)
    #input('Press Enter key to Load Current Page')
    data_1_day = load_gj_table()
    for i in data_1_day:
        print(i)
    saveMysql(data_1_day, dayi)
    
    # 
    szOpt = browser.find_element_by_xpath('//th[@data-field="ADD_MARKET_CAP"]/div')
    print('szOpt = ', szOpt)
    browser.execute_script("arguments[0].click();", szOpt)
    sleep(3)
    data_1_day = load_gj_table()
    #for i in data_1_day:
    #    print(i)
    saveMysql(data_1_day, dayi)
    
    db.close()
    if not auto:
        input('Press Enter To Exit')
    browser.quit()
    
if __name__ == '__main__':
    main(True)

