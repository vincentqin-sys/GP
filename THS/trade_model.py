import os, sys
import base_win, orm, hot_utils

cwd = os.getcwd()
w = cwd.index('GP')
cwd = cwd[0 : w + 2]
sys.path.append(cwd)

from Tdx.datafile import DataFile
from download.henxin import Henxin

henxin = Henxin()

def getHotCodesTop200(day : int):
    hots = hot_utils.calcHotZHOnDay(day)
    hots = hots[0 : 200]
    return hots

def loadTodayData(code):
    url = henxin.getTodayKLineUrl(code)
    pass

def loadDataFile(code):
    df = DataFile(code, DataFile.DT_DAY, DataFile.FLAG_ALL)
    return df

def isAccept(code):
    if type(code) == int:
        code = f'{code:06d}'
    df = loadDataFile(code)


if __name__ == '__main__':
    pass
