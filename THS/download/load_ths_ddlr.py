import peewee as pw
from peewee import fn
import os, json, time, sys, pyautogui, io
import fiddler, ths

sys.path.append('.')
import orm

BASE_STRUCT_PATH = 'D:/ths/ddlr-struct/'
BASE_DETAIL_PATH = 'D:/ths/ddlr-detail/'

if not os.path.exists(BASE_STRUCT_PATH):
    os.makedirs(BASE_STRUCT_PATH)
if not os.path.exists(BASE_DETAIL_PATH):
    os.makedirs(BASE_DETAIL_PATH)

def codeExists(code):
    e1 = os.path.exists(BASE_STRUCT_PATH + code)
    e2 = os.path.exists(BASE_DETAIL_PATH + code)
    return e1 and e2

def isCode(name):
    if not name:
        return False
    if len(name) != 6:
        return False
    for i in range(len(name)):
        if name[i] > '9' or name[i] < '0':
            return False
    return True

def getNameByCode(code):
    n = orm.THS_Newest.get_or_none(orm.THS_Newest.code == code)
    if not n:
        return ''
    return n.name

class LoadThsDdlrStruct:
    def listFiles(self):
        fs = os.listdir(BASE_STRUCT_PATH)
        rs = [BASE_STRUCT_PATH + f for f in fs if isCode(f) ]
        return rs

    def _loadFileData(self, fileName):
        data = {}
        f = open(fileName, 'r', encoding= 'utf8')
        lines = f.readlines()
        f.close()
        i = 0
        while i < len(lines) - 1:
            heads = lines[i].strip().split('\t')
            if len(heads) != 4 or len(lines[i + 1]) < 10:
                i += 1
                continue
            curTime, code, day, n = heads
            curDay, curTime = curTime.split(' ')
            curDay = curDay.replace('-', '')
            curTime = curTime[0 : 5] # hh:mm
            if curDay == day:
                if curTime < '15:00':
                    i += 2
                    continue
                
            js = json.loads(lines[i + 1])
            if js['code'] != 0:
                continue
            row = {'code' : code, 'day' : day}
            keys = ['activeIn', 'activeOut', 'positiveIn', 'positiveOut']
            for k in keys:
                row[k] = js['data'][k] / 100000000 # 亿
            row['total'] = row['activeIn'] + row['positiveIn'] - row['activeOut'] - row['positiveOut']
            data[day] = row
            i += 2
        
        # merge data
        rt = []
        for k, v in data.items():
            rt.append(v)
        return rt

    def loadOneFile(self, filePath):
        data = self._loadFileData(filePath)
        if len(data) <= 0:
            return
        self.mergeSavedData(data)
        os.remove(filePath)

    def loadAllFileData(self):
        fs = self.listFiles()
        print('找到大单结构数据: ', len(fs), '个')
        for f in fs:
            self.loadOneFile(f)

    def mergeSavedData(self, datas):
        code = datas[0]['code']
        name = getNameByCode(code)
        maxDay = orm.THS_DDLR.select(pw.fn.Max(orm.THS_DDLR.day)).where(orm.THS_DDLR.code == code).scalar()
        if not maxDay:
            maxDay = ''
        for d in datas:
            if d['day'] > maxDay:
                d['name'] = name
                orm.THS_DDLR.create(**d)

class LoadThsDdlrDetail:
    def __init__(self) -> None:
        self.tradeDays = self.getMaxTradeDays()
        #print(self.tradeDays)
        pass

    def getMaxTradeDays(self):
        query = orm.THS_Hot.select(orm.THS_Hot.day).distinct().order_by(orm.THS_Hot.day.desc()).limit(10).tuples()
        #print(query)
        maxDays = [str(d[0]) for d in query]
        return maxDays

    def getTradeDay(self, writeDay):
        for d in self.tradeDays:
            if writeDay >= d:
                return d
        raise Exception('出错了')

    def loadAllFilesData(self):
        fs = os.listdir(BASE_DETAIL_PATH)
        print('找到大单详细数据: ', len(fs), '个')
        for f in fs:
            if isCode(f):
                fp = BASE_DETAIL_PATH + f
                self.loadFileData(fp)
                os.remove(fp)
    
    # 写入 xxxxxx.dd 文件， 数据格式： 日期;开始时间,买卖方式(1:主动买 2:被动买 3:主动卖 4:被动卖),成交金额(万元); ...
    def loadFileData(self, fileName):
        f = open(fileName, 'r', encoding= 'utf8')
        lines = f.readlines()
        f.close()
        i = 0
        sio = io.StringIO()
        while i < len(lines) - 1:
            heads = lines[i].strip().split('\t')
            if len(heads) != 2 or len(lines[i + 1]) < 10:
                i += 1
                continue
            curTime, code = heads
            curDay, curTime = curTime.split(' ')
            curDay = curDay.replace('-', '')
            curTime = curTime[0 : 5] # hh:mm
            tradeDay = self.getTradeDay(curDay)
            ld = json.loads(lines[i + 1])
            if ld['code'] != 0:
                i += 2
                continue
            sio.write(tradeDay + ';')
            for d in ld['data']:
                v = d['firstTime'][0 : 4] + ',' + str(d['stats']) + ',' + str(int(d['totalMoney'] / 10000 + 0.5)) + ';'
                sio.write(v)
            sio.write('\n')
            i += 2

        f2 = open(fileName + '.dd', 'a', encoding='utf8')
        f2.write(sio.getvalue())
        f2.close()

def autoLoadOne(code, ddWin):
    ddWin.showWindow()
    time.sleep(1.5)
    ddWin.grubFocusInSearchBox()
    # clear input text
    for i in range(20):
        pyautogui.press('backspace')
        pyautogui.press('delete')
        time.sleep(0.02)
    pyautogui.typewrite(code, 0.1)
    pyautogui.press('enter')
    time.sleep(5)
    return codeExists(code)

# 自动下载同花顺热点Top200个股的大单数据
def autoLoadTop200Data():
    print('自动下载Top 200大单买卖数据(同花顺Level-2)')
    print('必须打开Fiddler, Fiddler拦截onBeforeResponse, 将数据下载下来')
    print('再将同花顺的大单统计功能打开, 鼠标定位在输入框中')
    fd = fiddler.Fiddler()
    fd.open()
    time.sleep(10)

    ddWin = ths.THS_DDWindow()
    if not ddWin.initWindows():
        raise Exception('未打开同花顺的大单页面')

    datas = orm.THS_Hot.select().order_by(orm.THS_Hot.id.desc()).limit(200)
    datas = [d for d in datas]
    datas.reverse()
    failTimes = 0
    for idx, d in enumerate(datas):
        code = f"{d.code :06d}"
        sc = autoLoadOne(code, ddWin)
        if sc:
            failTimes += 1
        sc = 'Success' if sc else 'Fail'
        print(f"[{idx + 1}] Download by fiddler : ", code, sc)
    fd.close()
    print('Load 200, Fail number:', failTimes)

def test2():
    import win32gui, win32con
    MAIN_WIN = 0x40468
    idx = 0
    def enumCallback(hwnd, exta):
        nonlocal idx
        title = win32gui.GetWindowText(hwnd)
        if win32gui.IsWindowVisible(hwnd):
            idx += 1
            print(f"[{idx}] hwnd = {hwnd : X}, {exta}, {title}")

    win32gui.EnumChildWindows(MAIN_WIN, enumCallback, 'WWX')

if __name__ == '__main__':
    autoLoadTop200Data()

    lds = LoadThsDdlrStruct()
    lds.loadAllFileData()

    ldd = LoadThsDdlrDetail()
    # 写入 xxxxxx.dd 文件， 数据格式： 日期;开始时间,买卖方式(1:主动买 2:被动买 3:主动卖 4:被动卖),成交金额(万元); ...
    ldd.loadAllFilesData()
    