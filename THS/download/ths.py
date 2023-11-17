import os, json, time, sys, pyautogui
import io, psutil, subprocess
import win32gui, win32con , win32api, win32ui, win32process # pip install pywin32

class THS_Window:
    def __init__(self) -> None:
        self.hwnd = None

    def open(self):
        pids = psutil.pids()
        for pid in pids:
            p = psutil.Process(pid)
            if 'hexin.exe' in p.name().lower():
                self.pid = pid
                print('已检测到开启了同花顺')
                return
        print('未开启同花顺, 自动开启')
        subprocess.Popen('D:\\Program Files\\THS\\hexin.exe', shell=True)
        self.needClose = True
        time.sleep(8)

    def close(self):
        if not self.needClose:
            return
        os.system('taskkill /F /IM hexin.exe')

    @staticmethod
    def cb(hwnd, self):
        title = win32gui.GetWindowText(hwnd)
        if self.hwnd or ('同花顺' not in title):
            return True
        threadId, processId = win32process.GetWindowThreadProcessId(hwnd)
        if processId == self.pid:
            self.hwnd = hwnd
        return True
    
    def findWindow(self):
        if self.hwnd:
            return self.hwnd
        win32gui.EnumWindows(THS_Window.cb, self)
        return self.hwnd

# 同花顺大单的窗口
class THS_DDWindow:
    def __init__(self) -> None:
        self.ddWnd = None
        self.topWnd = None

    def initWindows(self):
        def callback(hwnd, selfx):
            title = win32gui.GetWindowText(hwnd)
            if '同花顺(v' in title:
                selfx.topWnd = hwnd
            return True
    
        win32gui.EnumWindows(callback, self)
        self.ddWnd = win32gui.FindWindow(None, '大单棱镜')
        if not self.ddWnd:
            print('未查找到同花顺的大单棱镜窗口, 请确保已打开')
        return self.ddWnd != None

    def showWindow(self):
        if not self.ddWnd:
            return
        if win32gui.IsIconic(self.topWnd):
            win32gui.ShowWindow(self.topWnd, win32con.SW_MAXIMIZE)
        win32gui.SetForegroundWindow(self.ddWnd)
        time.sleep(1.5)

    def grubFocusInSearchBox(self):
        if not self.ddWnd:
            return
        rect = win32gui.GetWindowRect(self.ddWnd)
        x, y = rect[0] + 100, rect[1] + 60 # search input box center
        pyautogui.click(x, y)

dd = THS_DDWindow()
dd.initWindows()
dd.showWindow()
dd.grubFocusInSearchBox()