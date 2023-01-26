import os
import io
import sys
import sqlite3
import traceback

DAY = '20221001'

# open mysql
db = sqlite3.connect(r'D:\vscode\GP\db\HGT.db')

def formatName(name):
    name = str(name)
    ln = 0
    for i in range(len(name)):
        if ord(name[i]) < 256:
            ln += 1
        else:
            ln += 2
    rt = name + ' ' * (8 - ln)
    return rt

def query_hgt_count(maxNum = 20):
    cursor = db.cursor()
    sql = f'(select hgt.code, count(*) cc from hgt  where hgt.day >= {DAY}  group by hgt.code order by cc desc limit {maxNum}) as t '
    sql = f'select t.*, t2.name from {sql} left join tdxgpinfo as t2 on t.code = t2.code  '
    
    cursor.execute(sql)
    res = cursor.fetchall()
    print(f'[HGT前十]按数量统计前{maxNum}：')
    print('序号\t代码  \t名称    \t数量')
    for idx, r in enumerate(res):
        n = formatName(r[2])
        print(idx + 1, r[0], n, r[1], sep='\t')
    cursor.close()
        
def query_hgt_jme(maxNum = 20):
    cursor = db.cursor()
    sql = f'(select hgt.code, sum(jme) as _jme from hgt  where hgt.day >= {DAY}  group by hgt.code order by _jme desc limit {maxNum} ) as t'
    sql = f'select t.*, t2.name from {sql} left join tdxgpinfo as t2 on t.code = t2.code order by _jme desc'
    
    cursor.execute(sql)
    res = cursor.fetchall()
    print(f'[HGT前十]按买入金额统计前{maxNum}：')
    print('序号\t代码  \t名称    \t金额')
    for idx, r in enumerate(res):
        jme = r[1] / 10000
        jme = '%.1f亿' % jme
        n = formatName(r[2])
        print(idx + 1, r[0], n, jme, sep='\t')
    cursor.close()
        
def query_hgtacc_jme(maxNum = 20):
    cursor = db.cursor()
    sql = f'( select code, sum(zj) as _jme from hgtacc  where day >= {DAY}  group by code order by _jme desc limit {maxNum}) as t '
    sql = f'select t.*, t2.name from {sql}  left join  tdxgpinfo as t2 on t.code = t2.code order by _jme desc'
    
    cursor.execute(sql)
    res = cursor.fetchall()
    print(f'[HGT估计]按买入金额统计前{maxNum}：')
    print('序号\t代码  \t名称    \t金额')
    for idx, r in enumerate(res):
        jme = r[1] / 10000
        jme = '%.1f亿' % jme
        n = formatName(r[2])
        print(idx + 1, r[0], n, jme, sep='\t')
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