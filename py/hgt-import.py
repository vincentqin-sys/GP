import pymysql
from time import sleep
from selenium import webdriver
import traceback

# file "hgt-data" rows format:
# 日期  代码  净买  买入  卖出  成交
#_day, _code, _jme, _mrje, _mcje, _cjje , split by \t

#导出命令
#select _day, _code, _jme, _mrje, _mcje, _cjje from _hgt into outfile 'D:/hgt-data';

def readData():
    f = open('hgt-data', 'r')
    data = f.readlines()
    f.close()
    return data

mysql_conn = pymysql.connect(host= '127.0.0.1', port= 3306, user= 'root', password= 'root', db= 'tdx_f10')
cursor = mysql_conn.cursor()

def mergeItem(items, orgData):
    if items[5] == '\\N':
        items[5] = 0
    res = findInOrgData(items[0], items[1], orgData)
    
    if res is not None:
        # alreay exists
        return 2
    
    sql = 'insert into _hgt (_day, _code, _jme, _mrje, _mcje, _cjje) values ({0}, "{1}", {2}, {3}, {4}, {5}) '.format(items[0], items[1], items[2], items[3], items[4], items[5])
    cursor.execute(sql)
    print(sql)
    return 1
    
def findInOrgData(day, code, orgData):
    key = str(day) + '_' + code
    d = orgData.get(key, None)
    return d
    
def getOrgData(firstDay):
    sql = f'select _day, _code, _jme, _mrje, _mcje, _cjje from _hgt where _day >= {firstDay}'
    cursor.execute(sql)
    orgData = cursor.fetchall()
    orgDataMap = {}
    for row in orgData:
        key = str(row[0]) + '_' + row[1]
        orgDataMap[key] = row
    return orgDataMap

def main():
    rows = readData()
    insertNum = 0
    exitsNum = 0
    
    if len(rows) == 0:
        return
    firstDay = rows[0].split('\t')[0]
    orgData = getOrgData(firstDay)
    
    for i in rows:
        items = i.strip().split('\t')
        if len(items) != 6:
            continue
        status = mergeItem(items, orgData)
        insertNum += 1 if status == 1 else 0
        exitsNum += 1 if status == 2 else 0
        an = insertNum + exitsNum
        
    mysql_conn.commit()
    print('OK, All {} rows, insert {}, exists {}'.format(len(rows), insertNum, exitsNum))

try:
    main()
except Exception as e:
    traceback.print_exc()
input('Press Enter To Exit')


