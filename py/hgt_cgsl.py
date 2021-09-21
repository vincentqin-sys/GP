import pymysql
import time
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
browser.implicitly_wait(10)

mysql_conn = pymysql.connect(host= '127.0.0.1', port= 3306, user= 'root', password= 'root', db= 'tdx_f10')

needLoadCodes = []
loadIdx = 0

def load_code_cgsl(code):
    url = 'http://data.eastmoney.com/hsgtcg/StockHdStatistics.aspx?stock={}'.format(code)
    browser.get(url)
    div = browser.find_element_by_class_name('dataview-body')
    table = div.find_element_by_tag_name('table')
    trHead = table.find_elements_by_xpath('.//thead/tr/th')
    # check head column
    if trHead[0].get_attribute('data-field') != 'TRADE_DATE' or \
        trHead[2].get_attribute('data-field') != 'CLOSE_PRICE' or \
        trHead[4].get_attribute('data-field') != 'HOLD_SHARES' or \
        trHead[6].get_attribute('data-field') != 'A_SHARES_RATIO' :
            print('Web page change, update program first...')
            return False

    data = []
    trData = table.find_elements_by_xpath('.//tbody/tr')
    if len(trData) < 2:
        # no data
        return data;
    for tr in trData:
        tds = tr.find_elements_by_xpath('.//td')
        day = tds[0].text
        price = tds[2].find_element_by_xpath('.//span').text
        cgsl = tds[4].text
        per = tds[6].text
        data.append({'day': day, 'cgsl': cgsl, 'per': per, 'price': price})
    return data

def formatCgsl(text):
    lastChar = text[-1:]
    sl = float(text[0: -1])

    if lastChar == '亿':
        sl = sl * 10000
    elif lastChar == '万':
        sl = sl
    else:
        input('Format cgsl error: ' + text)
    return int(sl)

def save_cgsl(code, data):
    cursor = mysql_conn.cursor()
    n1 = 0
    n2 = 0
    n3 = 0
    for r in data:
        day = r['day'].replace('-', '')
        sql = 'select _id, _cgsl, _per, _zsz from _hgt_acc where _code = "{}" and _day = {}'.format(code, day)
        cursor.execute(sql)
        res = cursor.fetchall()
        
        cgsl = formatCgsl(r['cgsl'])
        per = float(r['per'])
        zsz = int(cgsl * 100 / per * float(r['price']) / 10000) # 亿元
        if len(res) == 0:
            sql = 'insert into _hgt_acc (_day, _code, _cgsl, _per, _zsz) values({}, "{}", {}, {}, {})'.format(day, code, cgsl, per, zsz)
            n1 += 1
        else:
            res = res[0]
            if res[1] != 0 and res[2] != 0:
                n3 += 1
                continue
            zsz = zsz if res[3] == 0 else res[3]
            sql = 'update _hgt_acc set _cgsl = {} , _per = {}, _zsz = {} where _id = {}'.format(cgsl, per, zsz, res[0])
            n2 += 1
        cursor.execute(sql)
    mysql_conn.commit()
    print('[{}] {}  insert:{}   update:{}  exists:{}'.format(loadIdx, code, n1, n2, n3) )

def load_one_code(code):
    try:
        data = load_code_cgsl(code)
        if data != False:
            if save_cgsl(code, data) != False:
                # load success
                return True
    except Exception as e:
        print('Load {} error: '.format(code), str(e))
        traceback.print_exc()
    # load fail
    return False

def load_all_codes():
    global loadIdx
    print('Total : {}'.format(len(needLoadCodes)))
    while len(needLoadCodes) > 0:
        target = needLoadCodes[0]
        ok = load_one_code(target)
        needLoadCodes.remove(target)
        if not ok:
            needLoadCodes.append(target)
        else:
            loadIdx += 1
        sleep(3)
    


def main():
    sql = 'select  _code, max(_zsz) from _hgt_acc group by _code'
    cursor = mysql_conn.cursor()
    cursor.execute(sql)
    res = cursor.fetchall()
    # res = [['002008', 500]]
    for r in res:
        code = r[0]
        zsz = r[1]
        if zsz > 350 or zsz == 0: #总市值大于350亿
            needLoadCodes.append(code)

    st = time.time()
    load_all_codes()
    ut = int(time.time() - st) # second
    mysql_conn.close()
    browser.quit()
    # print('Use Time: {}h  {}m  {}s'.format(ut // 3600, ut // 60, ut % 60))
    # input('Press Enter Key To Exit')

main()

#  查找沪股通占股比例最小、最大值，并排序
#  select a.*, a._max_per - a._min_per as _diff from hgt_acc_per_view a order by _diff desc;