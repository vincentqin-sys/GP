import peewee as pw
import hot_utils
from orm import THS_Hot, THS_HotZH

# 前3个交易日热度日期，从小到大排列
# day = 20230101  is int
def _getParseDays(day : int):
    allDays = hot_utils.getTradeDaysByHot()
    rs = []
    for i in range(len(allDays) - 1, 0, -1):
        if len(rs) >= 3:
            break
        if day >= allDays[i]:
            rs.append(allDays[i])
    rs.reverse()
    if rs[-1] != day:
        raise Exception('[_getParseDays] Invalid trade day: ', day)
    return rs

# 取得所有热度股(仅HotZH表)
# return { code: [THS_HotZH.data, ....] }
def _getAllHotCodesInHotZH(fromDay, endDay):
    rs = {}
    q = THS_HotZH.select().where(THS_HotZH.day >= fromDay, THS_HotZH.day <= endDay).order_by(THS_HotZH.day.asc())
    #print(q.sql())
    for d in q:
        code = d.code
        vl = rs[code] if code in rs else []
        vl.append(d.__data__)
        rs[code] = vl
    return rs

# return { code: [THS_HotZH.data, ....] }
def getAllHotCodes(day : int):
    days = _getParseDays(day)
    startDay, endDay = days[0], days[-1]
    rs = _getAllHotCodesInHotZH(startDay, endDay)
    lastDay = THS_HotZH.select(pw.fn.max(THS_HotZH.day)).scalar()
    if endDay > lastDay:
        newest = hot_utils.calcHotZHOnDay(lastDay)
        for n in newest:
            code = n['code']
            if code in rs:
                rs[code].append(n)
            else:
                rs[code] = [n]
    rmCodes = []
    for code in rs:
        if len(rs[code]) != len(days):
            rmCodes.append(code)
    for rc in rmCodes:
        del rs[rc]
    return rs


def getGrowth(hotsZH):
    if len(hotsZH) >= 2:
        pre, last = hotsZH[-2], hotsZH[-1]
        orderGrowth = int(pre['zhHotOrder'] - last['zhHotOrder'])
        valGrowth = int((last['avgHotValue'] - pre['avgHotValue']) / pre['avgHotValue'] * 100)
    else:
        orderGrowth = valGrowth = 1000 # 首次
    last = hotsZH[-1]
    rt = {'orderGrowth' : orderGrowth, 'valGrowth' : valGrowth}
    rt.update(last)
    return rt

# 计算热度值增长率
# return [ {code, orderGrowth, valGrowth} ]
def calcHotGrowth(day : int):
    codes = getAllHotCodes(day)
    rs = []
    for code in codes:
        gr = getGrowth(codes[code])
        if gr['avgHotValue'] < 30: #去除30万热度以下的个股, 热度太低的也没意义
            continue
        gr['code'] = f'{code :06d}'
        gr['name'] = hot_utils.getNameByCode(code)
        rs.append(gr)
    return rs

if __name__ == '__main__':
    rs = calcHotGrowth(20231204)
    rs = sorted(rs, key = lambda it : it['valGrowth'], reverse=True)
    print('#\tCODE\t  Name\t热度增率\t进位\t平均热度值')
    for i in range(0, len(rs)):
        code, name, valGrowth, orderGrowth,avgHotValue = rs[i]['code'], str(rs[i]['name']), rs[i]['valGrowth'], rs[i]['orderGrowth'], rs[i]['avgHotValue']
        hotOrder = rs[i]['zhHotOrder']
        print(i, f'{code}\t{name}\t{valGrowth:+d}%\t{orderGrowth:+d}({hotOrder})\t{avgHotValue}万\t', sep='\t')