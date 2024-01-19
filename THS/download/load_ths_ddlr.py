import peewee as pw
from peewee import fn
import os, json, time, sys, pyautogui, io, datetime, win32api, win32event, winerror
import fiddler, ths

#sys.path.append('.')
#sys.path.append('..')
cwd = os.getcwd()
w = cwd.index('GP')
cwd = cwd[0 : w + 2]
sys.path.append(cwd)
from THS import orm
from Tdx import datafile

BASE_STRUCT_PATH = 'D:/ThsData/ddlr-struct/'
BASE_DETAIL_PATH = 'D:/ThsData/ddlr-detail-src/'
DEST_DETAIL_PATH = 'D:/ThsData/ddlr-detail/'

if not os.path.exists(BASE_STRUCT_PATH):
    os.makedirs(BASE_STRUCT_PATH)
if not os.path.exists(BASE_DETAIL_PATH):
    os.makedirs(BASE_DETAIL_PATH)
if not os.path.exists(DEST_DETAIL_PATH):
    os.makedirs(DEST_DETAIL_PATH)

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
        query = orm.THS_Hot.select(orm.THS_Hot.day).distinct().order_by(orm.THS_Hot.day.desc()).limit(100).tuples()
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
                destfp = DEST_DETAIL_PATH + f
                self.loadFileData(fp, destfp)
                os.remove(fp)
    
    # 写入 xxxxxx.dd 文件， 数据格式： 日期;开始时间,买卖方式(1:主动买 2:被动买 3:主动卖 4:被动卖),成交金额(万元); ...
    def loadFileData(self, fileName, destfp):
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

        f2 = open(destfp + '.dd', 'a', encoding='utf8')
        f2.write(sio.getvalue())
        f2.close()

class ThsDdlrDetailData:

    def __init__(self, code) -> None:
        self.code = code
        self.data = []  # [{day :'YYYY-MM-DD', data: [(minutes, bs, money), ...], ... ]   # minutes int value . eg: 930 ==> '09:30' ; bs -> 1:主动买 2:被动买 3:主动卖 4:被动卖;  money :万元
        self._loadFile()

    def getDataAtDay(self, day):
        for item in self.data:
            if item['day'] == day:
                return item['data']
        return None

    # return [fromIdx, endIdx)
    def getMiniteDataRange(self, dayData, fromIdx):
        if fromIdx < 0 or fromIdx >= len(dayData):
            return None
        minute = dayData[fromIdx][0]
        for i in range(fromIdx, len(dayData)):
            if minute != dayData[i][0]:
                break
            i += 1
        return (fromIdx, i)

    def _loadOneLine(self, line):
        rs = {}
        spec = line.split(';')
        rs['day'] = spec[0][0 : 4] + '-' + spec[0][4 : 6] + '-' + spec[0][6 : 8]
        rs['data'] = []
        md = None
        for i in range(1, len(spec)):
            items = spec[i].split(',')
            if len(items) != 3:
                break
            _time, bs, money = items
            rs['data'].append((int(_time), int(bs), int(money)))
        return rs

    def _loadFile(self):
        fp = DEST_DETAIL_PATH + self.code + '.dd'
        if not os.path.exists(fp):
            return
        f = open(fp, 'r')
        while True:
            line = f.readline().strip()
            if not line:
                break
            item = self._loadOneLine(line)
            if len(self.data) > 0 and self.data[-1]['day'] == item['day']:
                self.data[-1] = item # 重复数据 replace it
            else:
                self.data.append(item)
        f.close()

def autoLoadOne(code, ddWin):
    ddWin.grubFocusInSearchBox()
    # clear input text
    for i in range(20):
        pyautogui.press('backspace')
        pyautogui.press('delete')
    pyautogui.typewrite(code, 0.01)
    pyautogui.press('enter')
    time.sleep(3)
    ddWin.releaseFocus()
    return codeExists(code)

# 自动下载同花顺热点Top200个股的大单数据
def autoLoadTop200Data():
    d = datetime.datetime.today()
    print(d.strftime('%Y-%m-%d:%H:%M:%S'), '->')
    print('自动下载Top 200大单买卖数据(同花顺Level-2)')
    print('Fiddler拦截onBeforeResponse, 将数据下载下来')
    fd = fiddler.Fiddler()
    fd.open()
    time.sleep(10)

    ddWin = ths.THS_DDWindow()
    ddWin.initWindows()
    if not ddWin.openDDLJ():
        fd.close()
        raise Exception('[autoLoadTop200Data] 同花顺的大单页面打开失败')

    MAX_NUM = 200
    datas = orm.THS_Hot.select().order_by(orm.THS_Hot.id.desc()).limit(MAX_NUM)
    datas = [d for d in datas]
    datas.reverse()
    successTimes, failTimes = 0, 0
    for idx, d in enumerate(datas):
        code = f"{d.code :06d}"
        sc = autoLoadOne(code, ddWin)
        if sc: successTimes += 1
        else: failTimes += 1
        if failTimes >= 5 and failTimes >= successTimes:
            break
    fd.close()
    print(f'Load {MAX_NUM}, Success {successTimes}, Fail {failTimes}')
    if successTimes + failTimes != MAX_NUM:
        raise Exception('[autoLoadTop200Data] 下载失败')

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

def run():
    lock = getDesktopGUILock()
    if not lock:
        return False
    try:
        autoLoadTop200Data()
        lds = LoadThsDdlrStruct()
        lds.loadAllFileData()
        ldd = LoadThsDdlrDetail()
        # 写入 xxxxxx.dd 文件， 数据格式： 日期;开始时间,买卖方式(1:主动买 2:被动买 3:主动卖 4:被动卖),成交金额(万元); ...
        ldd.loadAllFilesData()
        rs = True
    except Exception as e:
        print('Occur Exception: ', e)
        rs = False
    releaseDesktopGUILock(lock)
    return rs

def checkDDLR_Amount():
    query = orm.THS_DDLR.select(orm.THS_DDLR.code).distinct().where(orm.THS_DDLR.amount.is_null(True) | (orm.THS_DDLR.amount == 0) ).tuples()
    for q in query:
        code = q[0]
        df = datafile.DataFile(code, datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL)
        cs = orm.THS_DDLR.select().where(orm.THS_DDLR.code == code)
        for ddlr in cs:
            if not ddlr.amount:
                ad = df.getItemData(ddlr.day)
                if ad:
                    ddlr.amount = ad.amount / 100000000
                    ddlr.save()
    
def getDesktopGUILock():
    LOCK_NAME = 'D:/__Desktop_GUI_Lock__'
    mux = win32event.CreateMutex(None, False, LOCK_NAME)
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        win32api.CloseHandle(mux)
        return None
    return mux

def releaseDesktopGUILock(lock):
    if lock:
        win32api.CloseHandle(lock)

if __name__ == '__main__':
    lastDay = None
    runNow = False
    while True:
        today = datetime.datetime.now()
        if today.weekday() >= 5: # 周六周日
            time.sleep(60 * 60)
            continue
        nowDay = today.strftime('%Y-%m-%d')
        if lastDay == nowDay:
            time.sleep(60 * 60)
            checkDDLR_Amount()
            continue
        st = today.strftime('%H:%M')
        if (st >= '18:15' and st < '19:00') or runNow:
            pyautogui.hotkey('win', 'd')
            if run():
                lastDay = nowDay
                runNow = False
            checkDDLR_Amount()
            time.sleep(5 * 60)

    