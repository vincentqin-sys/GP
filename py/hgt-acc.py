import pymysql
from time import sleep
from selenium import webdriver
import traceback

options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])

browser = webdriver.Chrome( options = options)
# open mysql
mysql_conn = pymysql.connect(host= '127.0.0.1', port= 3306, user= 'root', password= 'root', db= 'tdx_f10')

def formatMoney(text):
    lastChar = text[-1:]
    money = float(text[0: -1])

    if lastChar == '亿':
        money = money * 10000
    elif lastChar != '万':
        input('Format money error: ' + text)
    return int(money)

def alreadyExists(code, day):
    cursor = mysql_conn.cursor()
    sql = 'select _id, _zj from _hgt_acc where _code = "{0}" and _day = {1} '.format(code, day)
    cursor.execute(sql)
    res = cursor.fetchall()
    if len(res) == 0:
        return 0
    zj = int(res[0][1])
    if zj != 0:
        return -1
    return res[0][0]

def existsCode(code):
    cursor = mysql_conn.cursor()
    sql = 'select count(*) from _hgt_acc where _code = "{0}"  '.format(code)
    cursor.execute(sql)
    res = cursor.fetchall()
    cc = int(res[0][0])
    return cc > 0

def saveMysql(data, day):
    global mysql_conn
    num = 0
    try:
        cursor = mysql_conn.cursor()
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
                sql = 'insert into _hgt_acc (_day, _code, _zj, _zsz) values ({0}, "{1}", {2}, {3}) '.format( day, v['code'], formatMoney(v['zj']), v['zsz'])
            else:
                sql = 'update _hgt_acc set _zj = {}, _zsz = {} where _id = {}'.format(formatMoney(v['zj']), v['zsz'], id)
            print('[{}] update {}'.format(num, v))
            num += 1
            cursor.execute(sql)

        mysql_conn.commit()
        return True
    except Exception as e:
        print('DB save error: ', str(e))
        traceback.print_exc()
        mysql_conn.rollback()
        return False

def queryLastDay():
    global mysql_conn
    try:
        cursor = mysql_conn.cursor()
        sql = 'select max(_day) from _hgt_acc'
        cursor.execute(sql)
        res = cursor.fetchall()
        # if len(res) == 1 and len(res[0]) == 1:
        if res[0][0] is not None:
            return res[0][0]
        return 20000101
    except Exception as e:
        print('DB query last day error: ', str(e))
    return False


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


def main():
    lastDay = queryLastDay()
    if lastDay == False:
        return

    # 沪深港通持股 估计
    browser.get('http://data.eastmoney.com/hsgtcg/list.html')
    # sleep(10)
    input('Press Enter key to Load Day')
    day = browser.find_element_by_class_name('title').find_element_by_tag_name('span').text[1: -1]
    print('Fetch acc day:', day)
    dayi = day.replace('-', '')
    if len(dayi) != 8:
        input('Load day error.')
        return

    while True:
        input('Press Enter key to Load Current Page')
        data_1_day = load_gj_table()
        #for i in data_1_day:
        #    print(i)
        saveMysql(data_1_day, dayi)

main()
mysql_conn.close()

# browser.quit()
# input('Press Any Key To Exit')

