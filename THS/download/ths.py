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

    def _enumChild(self, hwnd, rt):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if '逐笔成交--600000(' in title:
            rt['val'] = hwnd
        return True
    
    def getScreenPos(self, hwnd, x, y):
        while hwnd:
            rect = win32gui.GetWindowRect(hwnd)
            x += rect[0]
            y += rect[1]
            hwnd = win32gui.GetParent(hwnd)
        return x, y

    # 打开 大单棱镜
    def _openDDLJ(self):
        if not self.topWnd:
            return
        if win32gui.IsIconic(self.topWnd):
            win32gui.ShowWindow(self.topWnd, win32con.SW_MAXIMIZE)
        win32gui.SetForegroundWindow(self.topWnd)
        self.ddWnd = win32gui.FindWindow(None, '大单棱镜')
        if self.ddWnd:
            return
        pyautogui.typewrite('600000', 0.02)
        pyautogui.press('enter')
        time.sleep(3)
        rt = {'val': None}
        win32gui.EnumChildWindows(self.topWnd, self._enumChild, rt)
        hwnd = rt['val']
        if not hwnd:
            return
        print(f'hwnd=0x{hwnd: X}')
        _, y, x, _ = win32gui.GetWindowRect(hwnd)
        y += 5
        x -= 40
        #pyautogui.moveTo(x, y)
        pyautogui.click(x, y, interval = 0.5)
        time.sleep(3)
        self.ddWnd = win32gui.FindWindow(None, '大单棱镜')
    
    def openDDLJ(self):
        for i in range(0, 3):
            if not self.ddWnd:
                self._showTopWindow()
                self._openDDLJ()
                time.sleep(3)
        return self.ddWnd

    def initWindows(self):
        def callback(hwnd, selfx):
            title = win32gui.GetWindowText(hwnd)
            if '同花顺(v' in title:
                selfx.topWnd = hwnd
            return True
        win32gui.EnumWindows(callback, self)

    def _showTopWindow(self):
        if not self.topWnd:
            return
        if win32gui.IsIconic(self.topWnd):
            win32gui.ShowWindow(self.topWnd, win32con.SW_MAXIMIZE)

    def grubFocusInSearchBox(self):
        if not self.ddWnd:
            return
        rect = win32gui.GetWindowRect(self.ddWnd)
        x, y = rect[0] + 100, rect[1] + 60 # search input box center
        pyautogui.click(x, y)

if __name__ == '__main__':
    dd = THS_DDWindow()
    dd.initWindows()
    dd.openDDLJ()
    dd.grubFocusInSearchBox()