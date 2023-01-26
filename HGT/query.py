import os
import io
import sys
import sqlite3
import traceback

DAY = '20221001'

# open mysql
db = sqlite3.connect(r'D:\vscode\GP\db\HGT.db')

def query_hgt_count(maxNum = 20):
    cursor = db.cursor()
    sql = f'select hgt.code, count(*) cc from hgt  where hgt.day >= {DAY}  group by hgt.code order by cc desc limit {maxNum}'
    
    cursor.execute(sql)
    res = cursor.fetchall()
    print(f'[HGT前十]按数量统计前{maxNum}：')
    print('序号\t代码\t数量')
    for idx, r in enumerate(res):
        print(idx + 1, r[0], r[1], sep='\t')
    cursor.close()
        
def query_hgt_jme(maxNum = 20):
    cursor = db.cursor()
    sql = f'select hgt.code, sum(jme) as _jme from hgt  where hgt.day >= {DAY}  group by hgt.code order by _jme desc limit {maxNum}'
    
    cursor.execute(sql)
    res = cursor.fetchall()
    print(f'[HGT前十]按买入金额统计前{maxNum}：')
    print('序号\t代码\t金额')
    for idx, r in enumerate(res):
        jme = r[1] / 10000
        jme = '%.1f亿' % jme
        print(idx + 1, r[0], jme, sep='\t')
    cursor.close()
        
def query_hgtacc_jme(maxNum = 20):
    cursor = db.cursor()
    sql = f'select code, sum(zj) as _jme from hgtacc  where day >= {DAY}  group by code order by _jme desc limit {maxNum}'
    
    cursor.execute(sql)
    res = cursor.fetchall()
    print(f'[HGT估计]按买入金额统计前{maxNum}：')
    print('序号\t代码\t金额')
    for idx, r in enumerate(res):
        jme = r[1] / 10000
        jme = '%.1f亿' % jme
        print(idx + 1, r[0], jme, sep='\t')
    cursor.close()
    
try:
    query_hgt_count()
    print('-------------\n')
    query_hgt_jme()
    print('-------------\n')
    query_hgtacc_jme()
    print('-------------\n')
    
except Exception as e:
    traceback.print_exc()

db.close()
input('End....')