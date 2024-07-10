import sys, os, pyautogui, win32gui, win32con, time, datetime, traceback
import io, psutil, subprocess, win32process, win32event, win32api, winerror
from pywinauto.controls.common_controls import DateTimePickerWrapper # pip install pywinauto
import peewee as pw
from multiprocessing import shared_memory # python 3.8+

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from db import tdx_orm

class TdxVolPMTools:
    def __init__(self):
        fromDay = 20230101
        v = tdx_orm.TdxVolPMModel.select(pw.fn.max(tdx_orm.TdxVolPMModel.day)).scalar()
        self.fromDay = v if v else fromDay
        self.codes = None
        self.codeNames = None
        self.days = None
        self.loadAllCodes()
        self.calcDays()
        self.initCodeName()
        self.datafiles = [datafile.DataFile(c, datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL) for c in self.codes]
        
    # 加载所有股标代码（上证、深证股），不含指数、北证股票
    def loadAllCodes(self):
        self.codes = datafile.DataFileUtils.listAllCodes()
    
    def calcDays(self):
        self.days = datafile.DataFileUtils.calcDays(self.fromDay)

    def initCodeName(self):
        ths_db = pw.SqliteDatabase(f'{tdx_orm.path}GP/db/THS_F10.db')
        sql = 'select code, name from 最新动态'
        csr = ths_db.cursor()
        csr.execute(sql)
        rs = csr.fetchall()
        codeNames = {}
        for r in rs:
            codeNames[r[0]] = r[1]
        self.codeNames = codeNames
        csr.close()
        ths_db.close()
    
    def save(self, datas):
        tdx_orm.TdxVolPMModel.bulk_create(datas, 50)
    
    def calcVolOrder_Top100(self):
        dfs = self.datafiles
        bpd = 0
        def sortKey(df):
            idx = df.getItemIdx(bpd)
            if idx < 0:
                return 0
            return df.data[idx].amount

        for day in self.days:
            bpd = day
            newdfs = sorted(dfs, key = sortKey, reverse=True)
            top100 = []
            for i in range(100):
                nf = newdfs[i]
                code = nf.code
                di = nf.getItemData(day)
                amount =  (di.amount if di else 0) / 100000000
                name = self.codeNames.get(code)
                if not name:
                    name = 'N'
                d = {'code': code, 'name': name, 'day': day, 'amount': amount, 'pm': i + 1}
                top100.append(tdx_orm.TdxVolPMModel(**d))
                #print(d)
            self.save(top100)

    # 计算两市成交总额
    def calcSHSZVol(self):
        sh = datafile.DataFile('999999', datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL)
        sz = datafile.DataFile('399001', datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL)
        zs = []
        for day in self.days:
            d1 = sh.getItemData(day)
            d2 = sz.getItemData(day)
            amount = (d1.amount + d2.amount) // 100000000
            zs.append(tdx_orm.TdxVolPMModel(**{'code': '999999', 'name': '上证指数', 'day': day, 'amount': d1.amount // 100000000, 'pm': 0}))
            zs.append(tdx_orm.TdxVolPMModel(**{'code': '399001', 'name': '深证指数', 'day': day, 'amount': d2.amount // 100000000, 'pm': 0}))
            zs.append(tdx_orm.TdxVolPMModel(**{'code': '000000', 'name': '两市成交', 'day': day, 'amount': amount, 'pm': 0}))
        self.save(zs)
   
class TdxLSTools:
    def __init__(self) -> None:
        fromDay = 20230101
        v = tdx_orm.TdxLSModel.select(pw.fn.max(tdx_orm.TdxLSModel.day)).scalar()
        if v: fromDay = v
        self.fromDay = fromDay
        self.codes = None
        self.days = None

    def calcOneDayInfo(self, day, sz, sh, dfs):
        item = tdx_orm.TdxLSModel()
        item.day = day
        item.amount = (sz.getItemData(day).amount + sh.getItemData(day).amount) // 100000000 # 亿元
        for df in dfs:
            idx = df.getItemIdx(day)
            if idx <= 0:
                continue
            dt = df.data[idx]
            if dt.close > df.data[idx - 1].close:
                item.upNum += 1
            elif dt.close < df.data[idx - 1].close:
                item.downNum += 1
            else:
                item.zeroNum += 1
            zdt = getattr(dt, 'zdt', '')
            if zdt == 'ZT':
                item.ztNum += 1
            elif zdt == 'DT':
                item.dtNum += 1
            else:
                zd = getattr(dt, 'zhangFu', -9999)
                if zd > 0 and zd <= 2:
                    item.z0_2 += 1
                elif zd > 2 and zd <= 5:
                    item.z2_5 += 1
                elif zd > 5 and zd <= 7:
                    item.z5_7 += 1
                elif zd > 7:
                    item.z7 += 1
                elif zd < 0 and zd >= -2:
                    item.d0_2 += 1
                elif zd < -2 and zd >= -5:
                    item.d2_5 += 1
                elif zd < -5 and zd >= -7:
                    item.d5_7 += 1
                elif zd < -7 and zd != -9999:
                    item.d7 += 1
            lbs = getattr(dt, 'lbs', 0)
            if lbs >= 2:
                item.lbNum += 1
            if item.zgb < lbs:
                item.zgb = lbs
            
        return item

    def calcInfo(self):
        self.codes = datafile.DataFileUtils.listAllCodes()
        self.days = datafile.DataFileUtils.calcDays(self.fromDay)
        sh = datafile.DataFile('999999', datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL)
        sz = datafile.DataFile('399001', datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL)
        dfs = [datafile.DataFile(c, datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL) for c in self.codes]
        rs = []
        for df in dfs:
            df.calcZDT()
            df.calcZhangFu()
        for day in self.days:
            item = self.calcOneDayInfo(day, sz, sh, dfs)
            rs.append(item)
            print('TdxLSTools.calcInfo item=', item.__data__)
        tdx_orm.TdxLSModel.bulk_create(rs, 50)

class TdxDownloader:
    def __init__(self) -> None:
        pass

    def checkProcessStarted(self):
        pids = psutil.pids()
        for pid in pids:
            p = psutil.Process(pid)
            if 'tdxw.exe' in p.name().lower():
                self.pid = pid
                #print('已检测到开启了通达信')
                return True
        return False

    def startProcess(self):
        subprocess.Popen('D:\\Program Files\\new_tdx2\\TdxW.exe', shell=True)
        time.sleep(10)

    def killProcess(self):
        os.system('taskkill /F /IM TdxW.exe')

    def getScreenPos(self, hwnd, x, y, recurcive = True):
        while hwnd:
            #print(f'hwnd={hwnd:X}', win32gui.GetWindowText(hwnd))
            nx, ny , *_ = win32gui.GetWindowRect(hwnd)
            x += nx
            y += ny
            hwnd = win32gui.GetParent(hwnd)
            if not recurcive:
                break
        return (x, y)

    def login(self):
        hwnd = win32gui.FindWindow('#32770', '通达信金融终端V7.642')
        print(f'login hwnd=0x{hwnd :X}')
        if not hwnd:
            raise Exception('Not find Tdx login window')
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(3)
        pwdPos = (250, 300)
        pwdPos = self.getScreenPos(hwnd, *pwdPos)
        pyautogui.click(*pwdPos, duration=0.5)
        for i in range(20):
            pyautogui.press('backspace')
        pyautogui.typewrite('gaoyan2012')

        loginBtnPos = (200, 370)
        loginBtnPos = self.getScreenPos(hwnd, *loginBtnPos)
        pyautogui.click(*loginBtnPos, duration=0.5)
        time.sleep(15)

    def getTdxMainWindow(self):
        mainWnd = win32gui.FindWindow('TdxW_MainFrame_Class', None)
        print(f'main tdx window={mainWnd:X}')
        if not mainWnd:
            raise Exception('Not find tdx main window')
        return mainWnd
    
    def openDownloadDialog(self):
        mainWnd = self.getTdxMainWindow()
        win32gui.SetForegroundWindow(mainWnd)
        btnPos = (433, 35)
        time.sleep(3)
        btnPos = self.getScreenPos(mainWnd, *btnPos)
        pyautogui.click(*btnPos, duration=0.5)
        time.sleep(10)

    def getStartDayForDay(self):
        maxday = 20240101
        df = datafile.DataFile('999999', datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL)
        if df.data:
            maxday = df.data[-1].day
        dt = datetime.datetime.strptime(str(maxday), '%Y%m%d')
        #dt = dt + datetime.timedelta(days = 1)
        return dt
    
    def getStartDayForTimemimute(self):
        maxday = 20240101
        df = datafile.DataFile('999999', datafile.DataFile.DT_MINLINE, datafile.DataFile.FLAG_ALL)
        if df.data:
            maxday = df.data[-1].day
        dt = datetime.datetime.strptime(str(maxday), '%Y%m%d')
        #dt = dt + datetime.timedelta(days = 1)
        return dt
    
    def startDownloadForDay(self):
        hwnd = win32gui.FindWindow('#32770', '盘后数据下载')
        print(f'download dialog hwnd={hwnd:X}')
        if not hwnd:
            raise Exception('Not find download dialog')
        selBtnPos = self.getScreenPos(hwnd, 80, 95, False) # 日线和实时行情Button pos
        win32gui.SetForegroundWindow(hwnd)
        pyautogui.click(*selBtnPos, duration = 0.3)
        fromDayCtrl = win32gui.GetDlgItem(hwnd, 0x4D5) # 开始时间控件
        print(f'fromDayCtrl={fromDayCtrl:X}')
        if not fromDayCtrl:
            raise Exception('Not find fromDayCtrl')
        fromDayCtrl = DateTimePickerWrapper(fromDayCtrl)
        startDay = self.getStartDayForDay()
        fromDayCtrl.set_time(year = startDay.year, month = startDay.month, day = startDay.day)

        startBtn = win32gui.FindWindowEx(hwnd, None, 'Button', '开始下载')
        startBtnPos = self.getScreenPos(hwnd, 440, 400, False)
        pyautogui.click(*startBtnPos, duration = 0.3) # 点击下载
        # wait for download end
        statusCtrl = win32gui.GetDlgItem(hwnd, 0x4C8) 
        time.sleep(2)
        if win32gui.GetWindowText(startBtn) != '取消下载':
            raise Exception('start download Fail')
        while True:
            time.sleep(5)
            if win32gui.GetWindowText(startBtn) == '开始下载':
                break
        pyautogui.click(*selBtnPos, duration = 0.3)

    def startDownloadForTimeMinute(self):
        hwnd = win32gui.FindWindow('#32770', '盘后数据下载')
        print(f'download dialog hwnd={hwnd:X}')
        if not hwnd:
            raise Exception('Not find download dialog')
        win32gui.SetForegroundWindow(hwnd)
        selTabPos = self.getScreenPos(hwnd, 130, 35, False) # 一分钟线 tab pos
        pyautogui.click(*selTabPos, duration = 0.3)
        time.sleep(1.5)
        selBtnPos = self.getScreenPos(hwnd, 70, 70, False) # 一分钟线 pos
        pyautogui.click(*selBtnPos, duration = 0.3)

        fromDayCtrl = win32gui.GetDlgItem(hwnd, 0x4D5) # 开始时间控件
        print(f'fromDayCtrl={fromDayCtrl:X}')
        if not fromDayCtrl:
            raise Exception('Not find fromDayCtrl')
        fromDayCtrl = DateTimePickerWrapper(fromDayCtrl)
        startDay = self.getStartDayForTimemimute()
        fromDayCtrl.set_time(year=startDay.year, month=startDay.month, day = startDay.day)
        startBtn = win32gui.FindWindowEx(hwnd, None, 'Button', '开始下载')
        startBtnPos = self.getScreenPos(hwnd, 440, 400, False)
        pyautogui.click(*startBtnPos, duration = 0.3) # 点击下载
        # wait for download end
        time.sleep(2)
        if win32gui.GetWindowText(startBtn) != '取消下载':
            raise Exception('start download Fail')
        while True:
            time.sleep(5)
            if win32gui.GetWindowText(startBtn) == '开始下载':
                break

    def run(self):
        if self.checkProcessStarted():
            self.killProcess()
        pyautogui.hotkey('win', 'd')
        self.startProcess()
        try:
            self.login()
            self.openDownloadDialog()
            self.startDownloadForDay()
            self.startDownloadForTimeMinute()
        except:
            traceback.print_exc()
            return False
        self.killProcess()
        return True

def unlockScreen():
    try:
        shm = shared_memory.SharedMemory('PY_Screen_Locker', False)
        buf = shm.buf.cast('q')
        ts = win32api.GetTickCount() + 60 * 1000 * 60
        buf[0] = ts
        buf[1] = 200
        buf.release()
        shm.close()
        time.sleep(10)
    except Exception as e:
        import traceback
        traceback.print_exc()
        pass

def tryWork():
    try:
        return work()
    except Exception as e:
        traceback.print_exc()
    return False


def work():
    unlockScreen()
    time.sleep(10)
    tm = datetime.datetime.now()
    ss = tm.strftime('%Y-%m-%d %H:%M')
    print('\033[32m' + ss + '\033[0m')
    # 下载
    tdx = TdxDownloader()
    flag = tdx.run()
    if flag:
        tm = datetime.datetime.now()
        ss = tm.strftime('%Y-%m-%d %H:%M')
        print('download end ', ss)
        # 计算成交量排名
        print('calc vol info')
        t = TdxVolPMTools()
        t.calcVolOrder_Top100()
        t.calcSHSZVol()
        #计算两市行情信息
        t = TdxLSTools()
        t.calcInfo()
        print('merge mimute time line data')
        ld = datafile.DataFileLoader()
        ld.mergeAll()
    print('-----------End----------\n\n')
    return flag

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

# seconds
def checkUserNoInputTime():
    a = win32api.GetLastInputInfo()
    cur = win32api.GetTickCount()
    diff = cur - a
    sec = diff / 1000
    return sec >= 5 * 60

def getMaxDay(paths):
    md = None
    for p in paths:
        bn = os.path.basename(p)
        if '-' not in bn:
            continue
        sp = bn.split('-')
        if not md:
            md = sp[-1]
        elif md < sp[-1]:
            md = sp[-1]
    return md


def autoMain():
    os.system('') # fix win10 下console 颜色不生效
    lastDay = 0
    tryDays = {}
    while True:
        today = datetime.datetime.now()
        if today.weekday() >= 5: #周六周日
            time.sleep(60 * 60)
            continue
        if lastDay == today.day:
            time.sleep(60 * 60)
            continue
        ts = f"{today.hour:02d}:{today.minute:02d}"
        if ts < '21:05' or ts > '22:30':
            time.sleep(3 * 60)
            continue
        lock = getDesktopGUILock()
        if not lock:
            time.sleep(3 * 60)
            continue
        sday = today.strftime('%Y-%m-%d')
        if sday in tryDays:
            tryDays[sday] += 1
        else:
            tryDays[sday] = 1
        if tryDays[sday] <= 3 and work(): #checkUserNoInputTime() and
            lastDay = today.day
        releaseDesktopGUILock(lock)
        time.sleep(10 * 60)
        

def mergeTimeline():
    pass

if __name__ == '__main__':
    #t = TdxLSTools()
    #t.calcInfo()
    if 'debug' in sys.argv:
        work() # run one time
    else:
        autoMain()