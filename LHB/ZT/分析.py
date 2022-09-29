import os, struct
import peewee as pw

db = pw.SqliteDatabase('ZT.db')
cursor = db.cursor()

def fenxiByMonth(dayBegin, dayEnd, lianBan):
    cursor.execute('select count(*) from ztzb where day >= ? and day <= ? and 第几板 = ? and complete = 1', (dayBegin, dayEnd, lianBan))
    data = cursor.fetchone()
    count = data[0]
    cursor.execute('select count(*) from ztzb where day >= ? and day <= ? and tag = "ZT" and 第几板 = ? and complete = 1', (dayBegin, dayEnd, lianBan))
    data = cursor.fetchone()
    countZT = data[0]
    cursor.execute('select count(*) from ztzb where day >= ? and day <= ? and tag = "ZB" and 第几板 = ? and complete = 1', (dayBegin, dayEnd, lianBan))
    data = cursor.fetchone()
    countZB = data[0]
    print('ZongLiang:', count, 'ShangBan:', countZT, 'ZaBan:', countZB)
    
    nums = []
    params = [(-25, 0), (0, 1), (1, 2), (2, 3), (3,4), (4,5), (5,6), (6,7), (7,8), (8,9), (9,10), (10,25)]
    for p in params:
        cursor.execute('select count(*) from ztzb where day >= ? and day <= ? and 第几板 = ? and complete = 1 and tag == "ZT" and `1日最高涨幅` >= ? and  `1日最高涨幅` < ? ', (dayBegin, dayEnd, lianBan, *p))
        data = cursor.fetchone()
        nums.append(data[0])
    print('ShangBan:')
    [ print(n, end = ' ') for n in nums ]
    print(countZT)
    
    nums = []
    params = [(-25, 0), (0, 1), (1, 2), (2, 3), (3,4), (4,5), (5,6), (6,7), (7,8), (8,9), (9,10), (10,25)]
    for p in params:
        cursor.execute('select count(*) from ztzb where day >= ? and day <= ? and 第几板 = ? and complete = 1 and tag == "ZB" and `1日最高涨幅` >= ? and  `1日最高涨幅` < ? ', (dayBegin, dayEnd, lianBan, *p))
        data = cursor.fetchone()
        nums.append(data[0])
    print('ZaBan:')
    [ print(n, end = ' ') for n in nums ]
    print(countZB)
    
def fenxiByDay(day, lianBan):
    nums = []
    ## ZT
    cursor.execute('select count(*) from ztzb where day = ? and 第几板 = ? and complete = 1 and tag = "ZT" ', (day, lianBan))
    data = cursor.fetchone()
    if data[0] == 0:
        return
    ztNum = data[0]
    nums.append(data[0]) # 上板量
    cursor.execute('select count(*) from ztzb where day = ? and 第几板 = ? and complete = 1 and tag = "ZT" and `1日最高涨幅` >= 0 ', (day, lianBan))
    data = cursor.fetchone()
    nums.append(data[0]) # 上涨量
    nums.append(data[0]/ztNum) # 上涨比率
    cursor.execute('select count(*) from ztzb where day = ? and 第几板 = ? and complete = 1 and tag = "ZT" and `1日最高涨幅` < 0 ', (day, lianBan))
    data = cursor.fetchone()
    nums.append(data[0]) # 下跌量
    nums.append(data[0]/ztNum) # 下跌比率
    
    ## ZB
    zbNum = 0
    cursor.execute('select count(*) from ztzb where day = ? and 第几板 = ? and complete = 1 and tag = "ZB" ', (day, lianBan))
    data = cursor.fetchone()
    zbNum = data[0]
    nums.append(data[0]) # 炸板量
    cursor.execute('select count(*) from ztzb where day = ? and 第几板 = ? and complete = 1 and tag = "ZB" and `1日最高涨幅` >= 0 ', (day, lianBan))
    data = cursor.fetchone()
    nums.append(data[0]) # 上涨量
    nums.append(data[0] / zbNum if zbNum > 0 else 0) # 上涨比率
    cursor.execute('select count(*) from ztzb where day = ? and 第几板 = ? and complete = 1 and tag = "ZB" and `1日最高涨幅` < 0 ', (day, lianBan))
    data = cursor.fetchone()
    nums.append(data[0]) # 下跌量
    nums.append(data[0] / zbNum if zbNum > 0 else 0) # 下跌比率
    
    cursor.execute('select count(*) from ztzb where day = ? and 第几板 = ? and complete = 1', (day, lianBan))
    data = cursor.fetchone()
    zNum = data[0]
    nums.append(zNum) # 总量
    nums.append(zbNum / zNum) # 炸板率
    print(day, end = ' ')
    [print(n, end=' ') for n in nums]
    print('')


    
"""
# 月份
for i in range(9, 0, -1):    
    print(f'20220{i} -->')
    fenxiByMonth(20220001 + i * 100, 20220031 + i * 100, 2)
for i in range(12, 8, -1):
    print(f'20210{i} -->')
    fenxiByMonth(20210001 + i * 100, 20210031 + i * 100, 2)
"""

# 日
lianBan = 2
cursor.execute('select distinct(day) as dd from ztzb where 第几板 = ? and complete = 1 and day >= ? order by dd desc ', (lianBan, 20220925))
data = cursor.fetchall()
for d in data:
    fenxiByDay(d[0], lianBan)




