import os, json, sys
import time, re

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

from Download import fiddler
from Tdx.datafile import *

class FenXi:
    DAY_MINUTES_NUM = 240
    CHECK_MAX_NUM_DAY = 30  # only check last 30 trade days
    SUM_MINUTES_LEN = 10 # sum minuts 5 / 10 /15

    def __init__(self, code) -> None:
        self.code = code
        self.ddf : DataFile = None # day DataFile
        self.mdf : DataFile = None # minute DataFile

    def load(self):
        self.ddf = DataFile(self.code, DataFile.DT_DAY)
        df = DataFile(self.code, DataFile.DT_MINLINE)
        self.mdf = df
        if not df.data:
            return
        dayNum = len(df.data) // self.DAY_MINUTES_NUM
        dayNumNew = min(dayNum, self.CHECK_MAX_NUM_DAY)
        fromIdx = (dayNum - dayNumNew) * self.DAY_MINUTES_NUM
        self.parseMinutes(fromIdx, len(df.data))

    def parseMinutes(self, fromIdx, endIdx):
        avgAmounts = {}
        for i in range(fromIdx, endIdx):
            m = self.mdf.data[i]
            if m.day not in avgAmounts:
                dd = self.ddf.getItemData(m.day)
                avgAmounts[m.day] = dd.amount / self.DAY_MINUTES_NUM # 日内分时平均成交额

def loadAllCodes():
    p = os.path.join(VIPDOC_BASE_PATH, '__minline')
    cs = os.listdir(p)
    rs = []
    for name in cs:
        if name[0 : 2] == 'sh' and name[2] == '6':
            rs.append(name[2 : 8])
        elif name[0 : 2] == 'sz' and name[2 : 4] in ('00', '30'):
            rs.append(name[2 : 8])
    return rs

def fxAll():
    cs = loadAllCodes()
    for code in cs:
        fx = FenXi(code)
        fx.load()

if __name__ == '__main__':
    fx = FenXi('300925')
    fx.load()