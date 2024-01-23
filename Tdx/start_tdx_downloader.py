import sys, os, pyautogui, win32gui, win32con, time, datetime
import io, psutil, subprocess, win32process, win32event, win32api, winerror
from pywinauto.controls.common_controls import DateTimePickerWrapper # pip install pywinauto
import start_ls_info, datafile

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
        dirs = datafile.DataFileUtils.getLDayDirs()
        maxday = None
        for d in dirs:
            d = os.path.basename(d)
            if '-' not in d:
                continue
            lday = d.split('-')[-1]
            if not maxday or maxday < lday:
                maxday = lday
        dt = datetime.datetime.strptime(maxday, '%Y%m%d')
        dt = dt + datetime.timedelta(days = 1)
        return dt    
    
    def getStartDayForTimemimute(self):
        dirs = datafile.DataFileUtils.getMinlineDirs()
        maxday = None
        for d in dirs:
            d = os.path.basename(d)
            if '-' not in d:
                continue
            lday = d.split('-')[-1]
            if not maxday or maxday < lday:
                maxday = lday
        dt = datetime.datetime.strptime(maxday, '%Y%m%d')
        dt = dt + datetime.timedelta(days = 1)
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
        fromDayCtrl.set_time(year=startDay.year, month=startDay.month, day = startDay.day)
        startBtn = win32gui.FindWindowEx(hwnd, None, 'Button', '开始下载')
        startBtnPos = self.getScreenPos(hwnd, 440, 400, False)
        pyautogui.click(*startBtnPos, duration = 0.3) # 点击下载
        # wait for download end
        time.sleep(30)
        if win32gui.GetWindowText(startBtn) != '取消下载':
            raise Exception('start download Fail')
        while True:
            time.sleep(60)
            if win32gui.GetWindowText(startBtn) == '开始下载':
                break

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
        time.sleep(30)
        if win32gui.GetWindowText(startBtn) != '取消下载':
            raise Exception('start download Fail')
        while True:
            time.sleep(60)
            if win32gui.GetWindowText(startBtn) == '开始下载':
                break

    def run(self):
        if self.checkProcessStarted():
            self.killProcess()
        pyautogui.hotkey('win', 'd')
        self.startProcess()
        self.login()
        self.openDownloadDialog()
        self.startDownloadForDay()
        self.startDownloadForTimeMinute()
        self.killProcess()

def work():
    lock = getDesktopGUILock()
    if not lock:
        return False
    # 下载
    tdx = TdxDownloader()
    tdx.run()
    # 计算成交量排名
    t = start_ls_info.TdxVolPMTools()
    t.calcVolOrder_Top500()
    t.calcSHSZVol()
    #计算两市行情信息
    t = start_ls_info.TdxLSTools()
    t.calcInfo()
    releaseDesktopGUILock(lock)
    return True

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

if __name__ == '__main__':
    lastDay = 0
    while True:
        today = datetime.datetime.now()
        if today.weekday() >= 5: #周六周日
            time.sleep(60 * 60)
            continue
        if lastDay == today.day:
            time.sleep(60 * 60)
            continue
        ts = f"{today.hour:02d}:{today.minute:02d}"
        if ts < '18:00':
            time.sleep(3 * 60)
            continue
        if checkUserNoInputTime() and work():
            lastDay = today.day
        