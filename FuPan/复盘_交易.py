import os, sys, requests, json, time
import win32gui, win32con
import base_win, orm, hot_utils, ths_win


cwd = os.getcwd()
w = cwd.index('GP')
cwd = cwd[0 : w + 2]
sys.path.append(cwd)

from Tdx.datafile import DataFile, DataFileUtils
from THS import orm as ths_orm

tsm = ths_win.ThsShareMemory()

# 计算最大跌幅
# return {code, 最大跌幅, 起始日期，结束日期, 下跌天数, 跌停数}
def getMaxDieFu(code, fromDay : int, endDay : int):
    df = DataFile(code, DataFile.DT_DAY, DataFile.FLAG_ALL)
    df.calcZDT()
    bi = df.getItemIdx(fromDay)
    ei = df.getItemIdx(endDay)
    if bi < 0 or ei < 0:
        # error
        return 0
    maxPrice = minPrice = 0
    maxPriceDay = minPriceDay = 0
    maxPriceIdx = minPriceIdx = 0
    for i in range(bi, ei + 1):
        mx = max(df.data[i].open, df.data[i].close)
        mn = min(df.data[i].open, df.data[i].close)
        if maxPrice == 0 or maxPrice < mx:
            maxPrice = mx
            maxPriceDay = df.data[i].day
            maxPriceIdx = i
        if minPrice == 0 or minPrice > mn:
            minPrice = mn
            minPriceDay = df.data[i].day
            minPriceIdx = i

    if maxPriceDay > minPriceDay:
        return None
    c = df.data[maxPriceIdx - 1].close
    c = max(c, maxPrice)
    dfVal = (minPrice - c) / c * 100
    dtNum = 0
    for i in range(maxPriceIdx, minPriceIdx + 1):
        zdt = getattr(df.data[i], 'zdt', '')
        if 'DT' in zdt: dtNum += 1
    return [code, dfVal, maxPriceDay, minPriceDay, minPriceIdx - maxPriceIdx + 1, dtNum]

# 查找下跌幅度最大的个股
def findMaxDieFu(fromDay : int, endDay : int):
    codes = DataFileUtils.listAllCodes()
    dfList = []
    for c in codes:
        info = getMaxDieFu(c, fromDay, endDay)
        if info:
            dfList.append(info)
    dfList = sorted(dfList, key=lambda x : x[1])
    #print(dfList[0 : 50])
    for i in range(0, 50):
        name = ths_orm.THS_Newest.select(ths_orm.THS_Newest.name).where(ths_orm.THS_Newest.code == dfList[i][0]).scalar()
        dfList[i].insert(1, name)
        dfList[i][2] = f'{dfList[i][2] :.1f}'
        print(i + 1, dfList[i])
    return dfList
#--------------------------------------------------
def findZT_1_2_one(df, fromDay : int, endDay : int):
    beginIdx, endIdx = 0, 0
    for d in df.data:
        if d.day >= fromDay:
            break
        beginIdx += 1
    for d in df.data:
        if d.day > endDay:
            break
        endIdx += 1
    maxLbs = 0
    for i in range(beginIdx, min(endIdx + 2, len(df.data))):
        d = df.data[i]
        maxLbs = max(maxLbs, getattr(d, 'lbs', 0))
    
    

# 涨停1 - 1.5 - 2.5之间的个股
def findZT_1_2(fromDay : int, endDay : int):
    codes = DataFileUtils.listAllCodes()
    for c in codes:
        df = DataFile(c, DataFile.DT_DAY, DataFile.FLAG_ALL)
        df.calcMA(5)
        df.calcMA(10)
        df.calcZDT()

    pass


if __name__ == '__main__':
    #findMaxDieFu(20231227, 20231229)
    #while True:
    #    win32gui.ShowWindow(0xd08f2, win32con.SW_SHOW)
    #    time.sleep(0.3)
    #tsm.open()
    time.sleep(20)





    
