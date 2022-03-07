import pymysql
from time import sleep
from selenium import webdriver
import traceback

# file "acc-data" rows format:
# 日期  代码  资金  持股数量  沪股通占比  总市值
#day code zj cgsl per zsz , split by \t

#导出命令
#select _day _code, _zj, _cgsl, _per, _zsz from _hgt_acc into outfile 'D:/vscode/py/acc-data';

def readData():
    f = open('acc-data', 'r')
    data = f.readlines()
    f.close()
    return data

mysql_conn = pymysql.connect(host= '127.0.0.1', port= 3306, user= 'root', password= 'root', db= 'tdx_f10')

def mergeItem(items, cursor):
    sql = 'select _id, _zj, _cgsl, _per, _zsz from _hgt_acc where _code = "{0}" and _day = {1} '.format(items[1], items[0])
    cursor.execute(sql)
    res = cursor.fetchall()
    if len(res) == 0:
        sql = 'insert into _hgt_acc (_code, _day, _zj, _cgsl, _per, _zsz) values ("{0}", {1}, {2}, {3}, {4}, {5}) '.format(items[1], items[0], items[2], items[3], items[4], items[5])
        cursor.execute(sql)
        #print(sql)
        return 1
       
    zj = res[0][1] if int(items[2]) == 0 else int(items[2])
    cgsl = res[0][2] if int(items[3]) == 0 else int(items[3])
    per = res[0][3] if float(items[4]) == 0 else float(items[4])
    zsz = res[0][4] if int(items[5]) == 0 else int(items[5])
    if zj == res[0][1] and cgsl == res[0][2] and per == res[0][3] and zsz == res[0][4]:
        return 2
    sql = 'update _hgt_acc set _zj = {}, _cgsl = {}, _per = {}, _zsz = {} where _id = {}'.format(zj, cgsl, per, zsz, res[0][0])
    #print(sql)
    cursor.execute(sql)
    return 3

def main():
    cursor = mysql_conn.cursor()
    rows = readData()
    insertNum = 0
    updateNum = 0
    exitsNum = 0
    for i in rows:
        items = i.strip().split('\t')
        if len(items) != 6:
            continue
        status = mergeItem(items, cursor)
        insertNum += 1 if status == 1 else 0
        updateNum += 1 if status == 3 else 0
        exitsNum += 1 if status == 2 else 0
        an = insertNum + updateNum + exitsNum
        if an % 100 == 0:
            print('  insert {}, update {}, exists {}'.format(insertNum, updateNum, exitsNum))
        
    mysql_conn.commit()
    print('OK, All {} rows, insert {}, update {}, exists {}'.format(len(rows), insertNum, updateNum, exitsNum))

try:
    main()
except Exception as e:
    traceback.print_exc()
input('Press Enter To Exit')


