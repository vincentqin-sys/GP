import pymysql
from time import sleep
from selenium import webdriver
import traceback
import os
import shutil


# file "hgt-data" rows format:
# 日期  代码  净买  买入  卖出  成交
#_day, _code, _jme, _mrje, _mcje, _cjje , split by \t

#导出命令
#select _day, _code, _jme, _mrje, _mcje, _cjje from _hgt into outfile 'D:/hgt-data';


mysql_conn = pymysql.connect(host= '127.0.0.1', port= 3306, user= 'root', password= 'root', db= 'tdx_f10')


def main():
    if os.path.exists("hgt-data"):
        os.remove("hgt-data")
    if os.path.exists("D:/hgt-data"):
        os.remove("D:/hgt-data")
        
    cursor = mysql_conn.cursor()
    sql = "select _day, _code, _jme, _mrje, _mcje, _cjje from _hgt where _day >= {} into outfile 'D:/hgt-data' ".format(20211105)
    cursor.execute(sql)
    shutil.move("D:/hgt-data", "hgt-data")
    
try:
    main()
except Exception as e:
    traceback.print_exc()

mysql_conn.close()    
input('Press Enter To Exit')


