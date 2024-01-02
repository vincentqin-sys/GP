import os, sys, requests, json
import base_win, orm, hot_utils

cwd = os.getcwd()
w = cwd.index('GP')
cwd = cwd[0 : w + 2]
sys.path.append(cwd)

from Tdx.datafile import DataFile
from download.henxin import HexinUrl

httpSession = requests.session()
hexi = HexinUrl(httpSession)

def initCookie(cookie):
    #cookie = 'other_uid=Ths_iwencai_Xuangu_ubrr9jwfshzhczhpzic14fano2jf57hi; ta_random_userid=rb9hxv5p4r; cid=c0c6ae89b3ef8beacf7bb42884ff26f31680602883; v=A4_rwbwPNhJwdzLusZes_cEvHiictOPWfQjnyqGcK_4FcKXWqYRzJo3YdxWy'
    for c in cookie.split(';'):
        kv = c.strip().split('=')
        httpSession.cookies.set(kv[0], kv[1])

def getHotCodesTop200(day : int):
    hots = hot_utils.calcHotZHOnDay(day)
    hots = hots[0 : 200]
    return hots

def loadTodayData(code):
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
    hexi.init()
    hexi.read('hh.txt')
    loadTodayData('300093')
    hexi.write('hh.txt')
    
