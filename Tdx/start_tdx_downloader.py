import sys, os, pyautogui, win32gui, win32con, time, datetime
import io, psutil, subprocess, win32process
from pywinauto.controls.common_controls import DateTimePickerWrapper # pip install pywinauto
import start_ls_info

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

    def startDownload(self):
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
        fromDayCtrl.set_time(year=2023, month=12, day = 1)
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
        self.startProcess()
        self.login()
        self.openDownloadDialog()
        self.startDownload()
        self.killProcess()

def work():
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
        if ts < '18:30':
            time.sleep(10 * 60)
            continue
        lastDay = today.day
        work()
        