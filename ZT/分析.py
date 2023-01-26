import os, struct
import peewee as pw

db = pw.SqliteDatabase('D:/vscode/GP/db/ZT.db')
cursor = db.cursor()

def fenxiByMonth(dayBegin, dayEnd, lianBan, colCndName):
    cursor.execute('select count(*) from ztzb where day >= ? and day <= ? and 第几板 = ? and complete = 1 and complete_m30 = 1', (dayBegin, dayEnd, lianBan))
    data = cursor.fetchone()
    count = data[0]
    cursor.execute(f'select count(*) from ztzb where day >= ? and day <= ? and tag = "ZT" and 第几板 = ? and complete = 1 and complete_m30 = 1', (dayBegin, dayEnd, lianBan))
    data = cursor.fetchone()
    countZT = data[0]
    cursor.execute('select count(*) from ztzb where day >= ? and day <= ? and tag = "ZB" and 第几板 = ? and complete = 1 and complete_m30 = 1', (dayBegin, dayEnd, lianBan))
    data = cursor.fetchone()
    countZB = data[0]
    print('ZongLiang:', count, 'ShangBan:', countZT, 'ZaBan:', countZB)
    
    nums = []
    params = [(-25, 0), (0, 1), (1, 2), (2, 3), (3,4), (4,5), (5,6), (6,7), (7,8), (8,9), (9,10), (10,25)]
    for p in params:
        cursor.execute(f'select count(*) from ztzb where day >= ? and day <= ? and 第几板 = ? and complete = 1  and complete_m30 = 1 and tag == "ZT" and {colCndName} >= ? and  {colCndName} < ? ', (dayBegin, dayEnd, lianBan, *p))
        data = cursor.fetchone()
        nums.append(data[0])
    print('ShangBan:')
    for n in nums:
        print(n, end = '\t') 
    print(countZT)
    
    nums = []
    params = [(-25, 0), (0, 1), (1, 2), (2, 3), (3,4), (4,5), (5,6), (6,7), (7,8), (8,9), (9,10), (10,25)]
    for p in params:
        cursor.execute(f'select count(*) from ztzb where day >= ? and day <= ? and 第几板 = ? and complete = 1  and complete_m30 = 1 and tag == "ZB" and {colCndName} >= ? and  {colCndName} < ? ', (dayBegin, dayEnd, lianBan, *p))
        data = cursor.fetchone()
        nums.append(data[0])
    print('ZaBan:')
    for n in nums:
        print(n, end = '\t')
    print(countZB)
    
def fenxiByDay(day, lianBan):
    nums = []
    ## ZT
    cursor.execute('select count(*) from ztzb where day = ? and 第几板 = ? and complete = 1 and complete_m30 = 1 and tag = "ZT" ', (day, lianBan))
    data = cursor.fetchone()
    if data[0] == 0:
        return
    ztNum = data[0]
    nums.append(data[0]) # 上板量

    cursor.execute(f'select count(*) from ztzb where day = ? and 第几板 = ? and complete = 1 and complete_m30 = 1 and tag = "ZT" and 次日最高涨幅 > 0 ', (day, lianBan))
    data = cursor.fetchone()
    szNum = data[0]
    nums.append(data[0]) # 上涨量-全日
    nums.append(data[0]/ztNum) # 上涨比率
    
    cursor.execute(f'select count(*) from ztzb where day = ? and 第几板 = ? and complete = 1 and complete_m30 = 1 and tag = "ZT" and 次日30分钟内最高涨幅 > 0 ', (day, lianBan))
    data = cursor.fetchone()
    szNum30 = data[0]
    nums.append(data[0]) # 上涨量-前30分钟
    nums.append(data[0]/ztNum) # 上涨比率
    
    ## ZB
    zbNum = 0
    cursor.execute(f'select count(*) from ztzb where day = ? and 第几板 = ? and complete = 1 and complete_m30 = 1 and tag = "ZB" ', (day, lianBan))
    data = cursor.fetchone()
    zbNum = data[0]
    nums.append(data[0]) # 炸板量
    cursor.execute(f'select count(*) from ztzb where day = ? and 第几板 = ? and complete = 1 and complete_m30 = 1 and tag = "ZB" and 次日最高涨幅 > 0 ', (day, lianBan))
    data = cursor.fetchone()
    szNum += data[0]
    nums.append(data[0]) # 上涨量-全日
    nums.append(data[0] / zbNum if zbNum > 0 else 0) # 上涨比率
    cursor.execute(f'select count(*) from ztzb where day = ? and 第几板 = ? and complete = 1 and complete_m30 = 1 and tag = "ZB" and 次日30分钟内最高涨幅 > 0 ', (day, lianBan))
    data = cursor.fetchone()
    szNum30 += data[0]
    nums.append(data[0]) # 上涨量-前30分钟
    nums.append(data[0] / zbNum if zbNum > 0 else 0) # 上涨比率
    
    cursor.execute(f'select count(*) from ztzb where day = ? and 第几板 = ? and complete = 1 and complete_m30 = 1', (day, lianBan))
    data = cursor.fetchone()
    zNum = data[0]
    nums.append(zNum) # 总量
    nums.append(zbNum / zNum) # 炸板率
    nums.append(szNum / zNum) # 上涨率
    nums.append(szNum30 / zNum) # 上涨率-30分钟
    print(day, end = '\t')
    for n in nums:
        print(n, end='\t')
    print('')



""" 
# 按月份统计
yymm = 202207
lianBan = 2  #第几板
colCndName = '次日30分钟内平均涨幅' #  次日最高涨幅  次日30分钟内最高涨幅  次日30分钟内平均涨幅
print(f'{yymm} -->')
fenxiByMonth(yymm * 100 + 1, yymm * 100 + 31, lianBan, colCndName)
"""

#"""
# 按日统计
minDay = 20210901
lianBan = 1  #第几板
cursor.execute('select distinct(day) as dd from ztzb where 第几板 = ? and complete = 1  and complete_m30 = 1 and day >= ? order by dd desc ', (lianBan, minDay))
data = cursor.fetchall()
for d in data:
    fenxiByDay(d[0], lianBan)

#"""

