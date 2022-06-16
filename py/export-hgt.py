import pymysql
from time import sleep
from selenium import webdriver
import traceback
import os
import shutil


# file FILE_NAME rows format:
# 日期  代码  净买  买入  卖出  成交
#_day, _code, _jme, _mrje, _mcje, _cjje , split by \t

#导出命令
#select _day, _code, _jme, _mrje, _mcje, _cjje from _hgt into outfile 'D:/hgt-data';


mysql_conn = pymysql.connect(host= '127.0.0.1', port= 3306, user= 'root', password= 'root', db= 'tdx_f10')

FILE_NAME = 'data-hgt'

def main():
    if os.path.exists(FILE_NAME):
        os.remove(FILE_NAME)
    curPath = os.path.dirname(__file__)
    filePath = curPath + '\\' +  FILE_NAME
    filePath = filePath.replace('\\', '/')
    
    cursor = mysql_conn.cursor()
    sql = "select _day, _code, _jme, _mrje, _mcje, _cjje from _hgt where _day >= {} into outfile '{}' ".format(20220120, filePath)
    
    cursor.execute(sql)
    
try:
    main()
except Exception as e:
    traceback.print_exc()

mysql_conn.close()    
print('Export End, Exit')
sleep(1)


