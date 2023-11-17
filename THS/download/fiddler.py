import os, json, time, sys, pyautogui
import io, psutil, subprocess
import win32gui, win32con , win32api, win32ui, win32process # pip install pywin32

class Fiddler:
    def __init__(self) -> None:
        self.pid = None
        self.needClose = False
        self.hwnd = None

    def open(self):
        pids = psutil.pids()
        for pid in pids:
            p = psutil.Process(pid)
            if 'fiddler' in p.name().lower():
                self.pid = pid
                print('已检测到开启了fiddler')
                return
        print('未开启fiddler, 自动开启')
        subprocess.Popen('C:\\Program Files (x86)\\Fiddler\\Fiddler.exe', shell=True)
        self.needClose = True
        time.sleep(5)
        self.open()

    def close(self):
        # os.system('taskkill /F /IM Fiddler.exe')
        if not self.needClose:
            return
        win32gui.EnumWindows(self.cb, self)
        if self.hwnd:
            win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
            print('已自动关闭Fiddler')

    @staticmethod
    def cb(hwnd, self):
        title = win32gui.GetWindowText(hwnd)
        if self.hwnd or ('Fiddler' not in title):
            return True
        threadId, processId = win32process.GetWindowThreadProcessId(hwnd)
        if processId == self.pid:
            self.hwnd = hwnd
        return True


if __name__ == '__main__'    :
    fd = Fiddler()
    fd.open()
    fd.close()
