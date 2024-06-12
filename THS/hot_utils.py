import peewee as pw
import sys, os

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from db.ths_orm import THS_Hot, THS_HotZH, THS_GNTC

# param day : int
def calcHotZHOnDay(day : int):
    qq = THS_Hot.select(THS_Hot.day, THS_Hot.code, pw.fn.avg(THS_Hot.hotValue), pw.fn.sum(THS_Hot.hotOrder), pw.fn.count()).group_by(THS_Hot.day, THS_Hot.code).where(THS_Hot.day == day).tuples()
    count = THS_Hot.select(THS_Hot.time).distinct().where(THS_Hot.day == day).count()
    rowDatas = []
    for row in qq:
        _day, _code, _hotVal, _hotOrder, _count = row
        _hotOrder = (_hotOrder + (count - _count) * 200) / count
        item = {'code': _code, 'day': _day, 'avgHotValue': _hotVal, 'avgHotOrder': _hotOrder, 'zhHotOrder': 0}
        rowDatas.append(item)
    rowDatas = sorted(rowDatas, key = lambda d: d['avgHotOrder'])
    for i, rd in enumerate(rowDatas):
        rd['zhHotOrder'] = i + 1
    return rowDatas

def calcHotZHOnDayCode(day, code):
    if type(day) == str:
        day = day.replace('-', '')
        day = int(day)
    if type(code) == str:
        code = int(code)
    rowDatas = calcHotZHOnDay(day)
    for rd in rowDatas:
        if rd['code'] == code:
            return rd
    return None

def calcAllHotZHAndSave():
    fromDay = 20230101
    fd = THS_HotZH.select(pw.fn.max(THS_HotZH.day)).scalar()
    if fd:
        fromDay = fd
    daysQuery = THS_Hot.select(THS_Hot.day).distinct().where(THS_Hot.day > fromDay).tuples()
    #print(days.sql())
    days = [d[0] for d in daysQuery]
    for day in days:
        rowDatas = calcHotZHOnDay(day)
        zhDatas = [THS_HotZH(**d) for d in rowDatas]
        THS_HotZH.bulk_create(zhDatas, 50)

def calcHotZHAndSave(day):
    rowDatas = calcHotZHOnDay(day)
    zhDatas = [THS_HotZH(**d) for d in rowDatas]
    THS_HotZH.bulk_create(zhDatas, 50)

def getNameByCode(code):
    if type(code) == int:
        code = f'{code :06d}'
    name = THS_GNTC.select(THS_GNTC.name).where(THS_GNTC.code == code).scalar()
    return name

# 取得有热度排行的交易日期 从小到大排列
# return [20230101, ...] , item type is int
def getTradeDaysByHot():
    q = THS_Hot.select(THS_Hot.day).distinct().order_by(THS_Hot.day.asc()).tuples()
    days = [d[0] for d in q]
    return days

def getLastTradeDay():
    maxDay = THS_Hot.select(pw.fn.max(THS_Hot.day)).scalar()
    return maxDay

def calcHotZHOnLastDay():
    day = getLastTradeDay()
    return calcHotZHOnDay(day)

def loadFromFile():
    import json
    f = open('D:/download/a.json', 'r', encoding='utf-8')
    js = json.loads(f.read())
    for one in js:
        rs = []
        day = int(one['hotDay'].replace('-', ''))
        hotTime = int(one['hotTime'].replace(':', ''))
        for d in one['hotInfo']:
            d['day'] = day
            d['time'] = hotTime
            d['code'] = int(d['code'])
            del d['name']
            rs.append(THS_Hot(**d))
        THS_Hot.bulk_create(rs, 100)


if __name__ == '__main__':
    #getLastTradeDay()
    #calcAllHotZHAndSave()
    #loadFromFile()
    calcHotZHAndSave(20240611)
    
    print(os.getcwd())
    # 计算最热的30个股的综合排名
    #hots = calcHotZHOnDay(20240124)
    #zhDatas = [THS_HotZH(**d) for d in hots]
    #THS_HotZH.bulk_create(zhDatas, 50)

        

