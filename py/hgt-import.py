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

def mergeItem(items, cursor):
    if items[5] == '\\N':
        items[5] = 0
    sql = 'select count(*) from _hgt where _code = "{0}" and _day = {1} '.format(items[1], items[0])
    cursor.execute(sql)
    res = cursor.fetchall()
    if res[0][0] != 0:
        # alreay exists
        return 2
    
    sql = 'insert into _hgt (_day, _code, _jme, _mrje, _mcje, _cjje) values ({0}, "{1}", {2}, {3}, {4}, {5}) '.format(items[0], items[1], items[2], items[3], items[4], items[5])
    cursor.execute(sql)
    print(sql)
    return 1

def main():
    cursor = mysql_conn.cursor()
    rows = readData()
    insertNum = 0
    exitsNum = 0
    for i in rows:
        items = i.strip().split('\t')
        if len(items) != 6:
            continue
        status = mergeItem(items, cursor)
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


