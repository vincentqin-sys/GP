import os
import io
import sys
import sqlite3
from time import sleep
from selenium import webdriver
import traceback

DAY = '20210401'

# open mysql
db = sqlite3.connect(host= '127.0.0.1', port= 3306, user= 'root', password= 'root', db= 'tdx_f10')
f = open('d.txt', 'w')

def queryHgt():
    cursor = db.cursor()
    sql = 'select hgt.code, count(*) cc from hgt  where hgt.day >= {}  group by hgt.code order by cc desc'.format(DAY)
    
    cursor.execute(sql)
    res = cursor.fetchall()
    idx = 0
    for r in res:
        idx += 1
        print(idx, r)
        #t = '1' if r[0][0:1] == '6' else '0'
        f.write(r[0] + '\n')
        

def queryHgtAcc():
    cursor = db.cursor()
    sql = 'select code, count(*) cc from hgtacc  where day >= {} and zj != 0 group by code order by cc desc limit 100'.format(DAY)
    
    cursor.execute(sql)
    res = cursor.fetchall()
    idx = 0
    for r in res:
        idx += 1
        print(idx, r)
        #t = '1' if r[0][0:1] == '6' else '0'
        f.write(r[0] + '\n')

        
try:
    print('----Show HGT Begin ----')
    queryHgt()
    print('----Show HGT End ------')
    print('\n\n')
    print('----Show HGT-Acc Begin ----')
    queryHgtAcc()
    print('----Show HGT-Acc End ------')
except Exception as e:
    traceback.print_exc()

f.close()
db.close()
input('End....')