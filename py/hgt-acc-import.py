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
cursor = mysql_conn.cursor()

def mergeItem(items, orgData):
    res = findInOrgData(items[1], items[0], orgData)
    if not res:
        sql = 'insert into _hgt_acc (_code, _day, _zj, _cgsl, _per, _zsz) values ("{0}", {1}, {2}, {3}, {4}, {5}) '.format(     items[1], items[0], items[2], items[3], items[4], items[5])
        cursor.execute(sql)
        #print(sql)
        return 1
       
    zj = res[1] if int(items[2]) == 0 else int(items[2])
    cgsl = res[2] if int(items[3]) == 0 else int(items[3])
    per = res[3] if float(items[4]) == 0 else float(items[4])
    zsz = res[4] if int(items[5]) == 0 else int(items[5])
    if zj == res[1] and cgsl == res[2] and per == res[3] and zsz == res[4]:
        return 2
    if res[0] == 96611:
        print(f'dest => {zj}, {cgsl}, {per}, {zsz}')
        print('res=>', res)
        print('items=>', items)
    sql = 'update _hgt_acc set _zj = {}, _cgsl = {}, _per = {}, _zsz = {} where _id = {}'.format(zj, cgsl, per, zsz, res[0])
    #print(sql)
    cursor.execute(sql)
    return 3
    
def getOrgData(firstDay):
    sql = 'select _id, _zj, _cgsl, _per, _zsz, _code, _day from _hgt_acc where _day >= {} '.format(firstDay)
    cursor.execute(sql)
    orgData = cursor.fetchall()
    orgDataMap = {}
    for row in orgData:
        key = row[5] + '_' + str(row[6])
        orgDataMap[key] = row
    return orgDataMap

def findInOrgData(code, day, orgData):
    key = code + '_' + str(day)
    d = orgData.get(key, None)
    return d
        
def main():
    rows = readData()
    insertNum = 0
    updateNum = 0
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
        updateNum += 1 if status == 3 else 0
        exitsNum += 1 if status == 2 else 0
        an = insertNum + updateNum + exitsNum
        if an % 1000 == 0:
            print('  insert {}, update {}, exists {}'.format(insertNum, updateNum, exitsNum))
        
    mysql_conn.commit()
    mysql_conn.close()
    print('OK, All {} rows, insert {}, update {}, exists {}'.format(len(rows), insertNum, updateNum, exitsNum))

try:
    main()
except Exception as e:
    traceback.print_exc()
input('Press Enter To Exit')


