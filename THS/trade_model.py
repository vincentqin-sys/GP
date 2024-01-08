import os, sys, requests, json, time
import base_win, orm, hot_utils, ths_win

cwd = os.getcwd()
w = cwd.index('GP')
cwd = cwd[0 : w + 2]
sys.path.append(cwd)

from Tdx.datafile import DataFile

def getHotCodesTop200(day : int):
    hots = hot_utils.calcHotZHOnDay(day)
    hots = hots[0 : 200]
    return hots

def loadTodayData(code):
    return
    url = hexi.getTodayKLineUrl(code)
    print(url)
    resp = httpSession.get(url)
    if resp.status_code != 200:
        print('[loadTodayData] fail: ', resp)
        return None
    txt = resp.content.decode()
    fi = txt.index(':{') + 1
    ei = txt.index('}})') + 1
    txt = txt[fi : ei]
    js = json.loads(txt)
    keysMap = {'day': '1', 'open': '7', 'high': '8', 'low': '9', 'close': '11', 'vol': '13', 
                'amount': '19', 'hsl': '1968584', 'name': 'name'}
    obj = {}
    KS = ('1', '7', '8', '9', '11')
    for k in keysMap:
        if keysMap[k] in KS:
            obj[k] = int(js[keysMap[k]].replace('.', ''))
        elif k == 'amount':
            obj[k] = float(keysMap[k])
        else:
            obj[k] = keysMap[k]
    print(obj)
    return obj

def loadDataFile(code):
    df = DataFile(code, DataFile.DT_DAY, DataFile.FLAG_ALL)
    return df

def isAccept(code):
    if type(code) == int:
        code = f'{code:06d}'
    df = loadDataFile(code)


if __name__ == '__main__':
    #loadTodayData('300093')
    tsm = ths_win.ThsShareMemory()
    tsm.open()
    while True:
        time.sleep(0.5)
        code = tsm.readCode()
        day = tsm.readSelDay()
        print(f'read code={code :06d}  day={day}')

        
    
