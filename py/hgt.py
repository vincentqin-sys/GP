import pymysql
from time import sleep
from selenium import webdriver
import traceback

# chrome.exe --remote-debugging-port=9998 --user-data-dir="D://download/chrome"

options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
# options.add_experimental_option("debuggerAddress", "127.0.0.1:9998")
# options.add_argument("--user-data-dir=C:\\Users\\ROG\\AppData\\Local\\Google\\Chrome\\User Data")

# options.add_argument('-headless')
# options.add_argument('--no-sandbox')
# options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36')

browser = webdriver.Chrome( options = options)
# 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',

"""
with open('stealth.min.js') as f:
    js = f.read()
    browser.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": js
    })
"""

# open mysql
mysql_conn = pymysql.connect(host= '127.0.0.1', port= 3306, user= 'root', password= 'root', db= 'tdx_f10')

# 加载指数数据
def load_zs_data(url, tabId, lastDay) :
    browser.get(url)
    sleep(3) # 2 second
    # browser.find_element_by_id('page-50').click()
    # sleep(1)
    table = browser.find_element_by_id(tabId)
    headElems = table.find_elements_by_xpath('.//table/thead/tr/th')
    if headElems[0].text != '日期' or  headElems[3].text.find('当日成交净买额') == -1 or  \
                headElems[4].text.find('买入成交额') == -1 or  \
                headElems[5].text.find('卖出成交额') == -1:
        print('ZS Web page changed, update program first...')
        return False
    data = []
    while True:
        table = browser.find_element_by_id(tabId)
        bodyElems = table.find_elements_by_xpath('.//table/tbody/tr')
        # print('bodyElems.len = ', len(bodyElems))
        for e in bodyElems:
            tds = e.find_elements_by_xpath('.//td')
            item = {}
            item['day'] = tds[0].text
            item['jme'] = tds[3].text
            item['mrje'] = tds[4].text
            item['mcje'] = tds[5].text
            if item['day'] > lastDay:
                data.append(item)
            else:
                return data
        table.find_element_by_link_text('下一页').click()
        sleep(3)
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
    div = browser.find_element_by_id(divId)
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
    browser.get(url)
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
        item['mrje'] = formatMoney(item['mrje'], item)
        item['mcje'] = formatMoney(item['mcje'], item)
        if 'cjje' in item:
            item['cjje'] = formatMoney(item['cjje'], item)
        item['jme'] = item['mrje'] - item['mcje']
        item['day'] = item['day'].replace('-', '')
        if 'mrzb' in item:
            item['mrzb'] = int(float(item['mrzb'][0:-1]))
        if 'mczb' in item:
            item['mczb'] = int(float(item['mczb'][0:-1]))

def saveMysql(data999999, data399001, dataHGT):
    global mysql_conn
    try:
        cursor = mysql_conn.cursor()

        formatDBData(data999999)
        for v in data999999:
            sql = 'insert into _hgt (_code, _day, _jme, _mrje, _mcje) values ("999999", {0}, {1}, {2}, {3}) '.format(v['day'], v['jme']//10000, (v['mrje'])//10000, (v['mcje'])//10000)
            print(sql)
            cursor.execute(sql)

        formatDBData(data399001)
        for v in data399001:
            sql = 'insert into _hgt (_code, _day, _jme, _mrje, _mcje) values ("399001", {0}, {1}, {2}, {3}) '.format(v['day'], v['jme']//10000, (v['mrje'])//10000, (v['mcje'])//10000)
            print(sql)
            cursor.execute(sql)

        formatDBData(dataHGT)
        for v in dataHGT:
            sql = 'insert into _hgt (_code, _day, _jme, _mrje, _mcje, _cjje) values ("{0}", {1}, {2}, {3}, {4}, {5}) '.format(v['code'], v['day'], v['jme'], (v['mrje']), (v['mcje']), v['cjje'])
            print(sql)
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
        sql = 'select max(_day) from _hgt where _code = "999999" '
        cursor.execute(sql)
        res = cursor.fetchall()
        lastDay999999 = str(res[0][0])
        lastDay999999 = lastDay999999[0:4] + '-' + lastDay999999[4:6] + '-' + lastDay999999[6:]
        print('999999 last day: ', lastDay999999)

        sql = 'select max(_day) from _hgt where _code = "399001" '
        cursor.execute(sql)
        res = cursor.fetchall()
        lastDay399001 = str(res[0][0])
        lastDay399001 = lastDay399001[0:4] + '-' + lastDay399001[4:6] + '-' + lastDay399001[6:]
        print('399001 last day: ', lastDay399001)

        sql = 'select max(_day) from _hgt where _code != "999999" and  _code != "399001" '
        cursor.execute(sql)
        res = cursor.fetchall()
        lastDay = str(res[0][0])
        lastDay = lastDay[0:4] + '-' + lastDay[4:6] + '-' + lastDay[6:]
        print('GP last day: ', lastDay)
        
        return [lastDay999999, lastDay399001, lastDay]
        #mysql_conn.commit()
    except Exception as e:
        print('DB query error: ', str(e))
        #mysql_conn.rollback()
    return False
    

def queryCodeDays(lastDay):
    global mysql_conn
    try:
        lastDay = lastDay[0:4] + lastDay[5:7] + lastDay[8:]
        cursor = mysql_conn.cursor()
        sql = 'select _day from _hgt  where _code = "999999" and _day > {} order by _day asc'.format(lastDay)
        print(sql)
        cursor.execute(sql)
        res = cursor.fetchall()
        data = []
        for r in res:
            data.append(r[0])
        return data
    except Exception as e:
        print('DB query days error: ', str(e))
    return False

def main():
    lastDays = queryLastDay()
    if lastDays == False:
        return

    data999999 = load_zs_data('http://data.10jqka.com.cn/hgt/hgtb/', 'table1', lastDays[0])
    if data999999 == False :
        print('Load 999999 fail')
        return
    print('999999 --> ', len(data999999))
    for i in data999999:
        print('   ', i)

    data399001 = load_zs_data('http://data.10jqka.com.cn/hgt/sgtb/', 'table1', lastDays[1])
    if data399001 == False :
        print('Load 399001 fail')
        return
    print('399001 --> ', len(data399001))
    for i in data399001:
        print('   ', i)

    if saveMysql(data999999, data399001, [] ) == False:
        return
    
    days = queryCodeDays(lastDays[2])
    if days == False or len(days) == 0:
        return
    
    dataHGT = []
    for day in days:
        cur = load_top10_data(day)
        if cur == False:
            return
        dataHGT.extend(cur)
    print('HGT --> ', len(dataHGT))
    for i in dataHGT:
        print('   ', i)
    saveMysql([], [], dataHGT)
    

main()
    
mysql_conn.close()
input('Press Enter Key To Exit')
browser.quit()




