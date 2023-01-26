import sqlite3, os
from time import sleep
from selenium import webdriver
import traceback

# chrome.exe --remote-debugging-port=9998 --user-data-dir="D://download/chrome"

_browser = None
_db = None

def get_browser():
    global _browser
    if _browser:
        return _browser
    
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # options.add_experimental_option("debuggerAddress", "127.0.0.1:9998")
    # options.add_argument("--user-data-dir=C:\\Users\\ROG\\AppData\\Local\\Google\\Chrome\\User Data")

    # options.add_argument('-headless')
    # options.add_argument('--no-sandbox')
    # options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36')

    _browser = webdriver.Chrome( options = options)
    return _browser
    
def get_db():
    global _db
    if _db:
        return _db
    _db = sqlite3.connect('D:/vscode/GP/db/HGT.db')
    return _db
    
# 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',

"""
with open('stealth.min.js') as f:
    js = f.read()
    get_browser().execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": js
    })
"""

# 加载指数数据 北向资金流入
def load_zs_data(lastDay) :
    url = 'https://data.eastmoney.com/hsgtcg/gzcglist.html'
    get_browser().get(url)
    sleep(3) # 2 second
    # get_browser().find_element_by_id('page-50').click()
    # sleep(1)
    table = get_browser().find_element_by_css_selector('.dataview-body > table')
    headElems = table.find_elements_by_xpath('.//thead/tr/th')
    if headElems[0].text != '日期' or  headElems[2].text != '北向资金今日增持估计' or  headElems[6].text != '市值':
        print('ZS Web page changed, update program first... ', url)
        raise Exception('Error: page changed ')
        return False
    data = []
    while True:
        bodyElems = table.find_elements_by_xpath('.//tbody/tr')
        # print('bodyElems.len = ', len(bodyElems))
        for e in bodyElems:
            tds = e.find_elements_by_xpath('.//td')
            item = {'code': 'HGTALL'}
            item['day'] = tds[0].text
            item['jme'] = tds[2].text
            if item['day'] > lastDay:
                data.append(item)
            else:
                break
        #table.find_element_by_link_text('下一页').click()
        #sleep(3)
        #print('Wait for click 下一页')
        break
    return data


def load_top10_body(table, data, lastDay):
    bodyElems = table.find_elements_by_xpath('.//tbody/tr')
    for e in bodyElems:
        tds = e.find_elements_by_xpath('.//td')
        item = {}
        item['day'] = tds[0].text
        item['code'] = tds[1].find_element_by_xpath('.//a').text
        item['name'] = tds[2].find_element_by_xpath('.//a').text

        item['mrje'] = tds[5].find_element_by_xpath('.//i').text
        item['mrzb'] = tds[6].text

        item['mcje'] = tds[7].find_element_by_xpath('.//i').text
        item['mczb'] = tds[8].text

        item['cjje'] = tds[9].find_element_by_xpath('.//i').text
        item['cjzb'] = tds[10].text

        if item['day'] <= lastDay:
            return False
        data.append(item)
    return True

def load_top10_one_table(browser, divId, day):
    div = get_browser().find_element_by_id(divId)
    table = div.find_element_by_class_name('dataview-body').find_element_by_xpath('.//table')
    headElems = table.find_elements_by_xpath('.//thead/tr/th')
    if headElems[1].get_attribute('data-field') != 'SECURITY_CODE' or \
                headElems[2].get_attribute('data-field') != 'SECURITY_NAME' or  \
                headElems[6].get_attribute('data-field') != 'NET_BUY_AMT' or  headElems[7].get_attribute('data-field') != 'BUY_AMT' or \
                headElems[8].get_attribute('data-field') != 'SELL_AMT' or  headElems[9].get_attribute('data-field') != 'DEAL_AMT'  :
        print('Web page changed, update program first...')
        return False
    data = []
    bodyElems = table.find_elements_by_xpath('.//tbody/tr')
    for e in bodyElems:
        tds = e.find_elements_by_xpath('.//td')
        if len(tds) == 1:
            # no data
            print('No Data')
            break
        item = {}
        item['day'] = day
        item['code'] = tds[1].find_element_by_xpath('.//a').text
        item['name'] = tds[2].find_element_by_xpath('.//a').text
        item['jme'] = tds[6].find_element_by_xpath('.//span').text
        item['mrje'] = tds[7].text
        item['mcje'] = tds[8].text
        item['cjje'] = tds[9].text
        data.append(item)
    return data


# 十大成交股
def load_top10_data(day) :
    day = str(day)
    day = day[0:4] + '-' + day[4:6] + '-' + day[6:]
    url = 'http://data.eastmoney.com/hsgt/top10/{}.html'.format(day)
    get_browser().get(url)
    sleep(3) # 3 second
    
    data = []
    hgt = load_top10_one_table(browser, 'dataview_hgt', day)
    sgt = load_top10_one_table(browser, 'dataview_sgt', day)
    
    if hgt == False or sgt == False:
        return False
    data.extend(hgt)
    data.extend(sgt)
    return data

def formatMoney(text, info):
    if type(text) != str:
        return text
    lastChar = text[-1:]
    money = float(text[0: -1])

    if lastChar == '亿':
        money = money * 10000
    elif lastChar != '万':
        print(info)
        input('Format money error: ' + text)
    return int(money)

def formatDBData(p):
    for item in p:
        item['mrje'] = formatMoney(item.get('mrje', 0), item)
        item['mcje'] = formatMoney(item.get('mcje', 0), item)
        if 'cjje' in item:
            item['cjje'] = formatMoney(item['cjje'], item)
        else:
            item['cjje'] = item['mrje'] + item['mcje']
        if 'jme' not in item:
            item['jme'] = item['mrje'] - item['mcje']
        else:
            item['jme'] = formatMoney(item.get('jme', 0), item)
        item['day'] = item['day'].replace('-', '')
        if 'mrzb' in item:
            item['mrzb'] = int(float(item['mrzb'][0:-1]))
        if 'mczb' in item:
            item['mczb'] = int(float(item['mczb'][0:-1]))

        if item['code'] == 'HGTALL': #单位亿元
            item['jme'] = item['jme'] // 10000
            item['mrje'] = item['mrje'] // 10000
            item['mcje'] = item['mcje'] // 10000
            item['cjje'] = item['cjje'] // 10000


def saveDB(data):
    try:
        cursor = get_db().cursor()

        formatDBData(data)
        for v in data:
            sql = 'insert into hgt (code, day, jme, mrje, mcje, cjje) values ("{0}", {1}, {2}, {3}, {4}, {5}) '.format(v['code'], v['day'], v['jme'], (v['mrje']), (v['mcje']), v['cjje'])
            print(sql)
            cursor.execute(sql)
        get_db().commit()
        return True
    except Exception as e:
        print('DB save error: ', str(e))
        traceback.print_exc()
        get_db().rollback()
        return False

def queryLastDay():
    cursor = get_db().cursor()
    sql = 'select max(day) from hgt where code = "HGTALL" '
    cursor.execute(sql)
    res = cursor.fetchone()
    if not res[0]:
        zsLastDay = '20221010'
    else:
        zsLastDay = str(res[0])
    zsLastDay = zsLastDay[0:4] + '-' + zsLastDay[4:6] + '-' + zsLastDay[6:]
    print('指数 last day: ', zsLastDay)

    sql = 'select max(day) from hgt where  code != "HGTALL" '
    cursor.execute(sql)
    res = cursor.fetchone()
    lastDay = str(res[0])
    lastDay = lastDay[0:4] + '-' + lastDay[4:6] + '-' + lastDay[6:]
    print('GP last day: ', lastDay)
    
    return [zsLastDay, lastDay]
    #get_db().commit()
    print('DB query error: ', str(e))
    

def queryCodeDays(lastDay):
    lastDay = lastDay[0:4] + lastDay[5:7] + lastDay[8:]
    cursor = get_db().cursor()
    sql = 'select day from hgt  where code = "HGTALL" and day > {} order by day asc'.format(lastDay)
    print(sql)
    cursor.execute(sql)
    res = cursor.fetchall()
    data = []
    for r in res:
        data.append(r[0])
    return data

def main(auto):
    lastDays = queryLastDay()
    if lastDays == False:
        return

    dataZS = load_zs_data(lastDays[0])
    if dataZS == False :
        print('Load ZS fail')
        return
    print('ZS --> ', len(dataZS))
    for i in dataZS:
        print('   ', i)

    if saveDB(dataZS) == False:
        return
    
    days = queryCodeDays(lastDays[1])
    if days == False:
        return
    
    for day in days:
        dataHGT = load_top10_data(day)
        if not dataHGT:
            continue
        print('HGT --> ', len(dataHGT))
        for i in dataHGT:
            print('   ', i)
        saveDB(dataHGT)
    get_db().close()
    
    if (not auto) and (len(days) == 0):
        ld = str(lastDays[2])
        #ld = ld[0:4] + '-' + ld[4:6] + '-' + ld[6:]
        url = 'http://data.eastmoney.com/hsgt/top10/{}.html'.format(ld)
        get_browser().get(url)
    if not auto:
        input('Press Enter Key To Exit')
    
    get_browser().quit()

if __name__ == '__main__':
    main(True)
    

