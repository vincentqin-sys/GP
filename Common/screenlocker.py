import os, sys, re, time, json, io
import win32gui, win32con, win32api, win32event
import threading, time, datetime, sys, os
from multiprocessing import Process
from multiprocessing import shared_memory # python 3.8+
import system_hotkey

import base_win

class ScreenLocker(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0
        self.keys = ''

    def createWindow(self, parentWnd = None, rect = None, style = 0, className='STATIC', title=''):
        W = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        H = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        rect = (0, 0, W, H)
        style = win32con.WS_POPUP
        super().createWindow(parentWnd, rect, style, className, title)

    def onChar(self, keyCode):
        if keyCode == win32con.VK_RETURN:
            if self.keys == 'gaoyan2012':
                self.unlock()
            self.keys = ''
            self.invalidWindow()
        else:
            self.keys += chr(keyCode)
            self.invalidWindow()

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SYSKEYDOWN or msg == win32con.WM_SYSKEYUP:
            return True
        if msg == win32con.WM_SHOWWINDOW:
            if wParam == True:
                win32gui.SetForegroundWindow(self.hwnd)
                win32gui.SetFocus(self.hwnd)
            return True
        if msg == win32con.WM_CHAR:
            self.onChar(wParam)
            return True
        if msg == win32con.WM_DESTROY:
            # no quit
            pass
        return super().winProc(hwnd, msg, wParam, lParam)
    
    def isLocked(self):
        locked = win32gui.IsWindow(self.hwnd) and win32gui.IsWindowVisible(self.hwnd)
        return locked
    
    def unlock(self):
        if win32gui.IsWindow(self.hwnd):
            win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)

    def lock(self):
        if not win32gui.IsWindow(self.hwnd):
            self.createWindow()
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOMOVE)
        self.invalidWindow()

    def onDraw(self, hdc):
        W, H = self.getClientSize()
        CW, CH = 250, 40
        x = (W - CW) // 2
        y = (H - CH) // 2
        rc = (x, y, x + CW, y + CH)
        self.drawer.fillRect(hdc, rc, 0x202020)
        if win32gui.GetFocus() == self.hwnd:
            self.drawer.drawRect(hdc, rc, 0x66B2FF)
        txt = '*' * len(self.keys)
        self.drawer.use(hdc, self.drawer.getFont(fontSize = 20))
        self.drawer.drawText(hdc, txt, rc, 0x0C95CD, align = win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)


class Main:
    SKIP_TIME_IDX = 0
    LOCK_STATUS_IDX = 1
    LOCK_STATUS_LOCK = 100
    LOCK_STATUS_UNLOCK = 200
    MAX_IDLE_TIME = 5 * 60
    
    def __init__(self, locker : ScreenLocker) -> None:
        self.locker = locker
        self.thread = base_win.Thread()
        self.shm = None
        self._name = 'PY_Screen_Locker'
        self.lastInputTime = 0

    def start(self):
        SZ = 128
        self.shm = shared_memory.SharedMemory(self._name, True, size = SZ)
        buf = self.shm.buf.cast('i')
        for i in range(SZ // 4):
            buf[i] = 0

        self.thread.addTask(1, self.loop)
        self.thread.start()

        hk = system_hotkey.SystemHotkey()
        hk.register(('alt', 'l'), callback = self.doHotKey, overwrite = True)

    def doHotKey(self, args):
        if self.locker.isLocked():
            self.locker.unlock()
        else:
            self.locker.lock()
    
    def writeIntData(self, pos, data):
        if not self.shm:
            return
        buf = self.shm.buf.cast('i')
        buf[pos] = data

    def readIntData(self, pos):
        if not self.shm:
            return 0
        buf = self.shm.buf.cast('i')
        data = buf[pos]
        return data
    
    # seconds
    def getIdleTime(self):
        lit = win32api.GetLastInputInfo()
        lit = max(lit, self.lastInputTime)
        idleTime = (win32api.GetTickCount() - lit) // 1000 # seconds
        return idleTime

    def loop(self):
        while True:
            time.sleep(1)

            status = self.readIntData(self.LOCK_STATUS_IDX)
            if status != 0:
                self.writeIntData(self.LOCK_STATUS_IDX, 0)
            if status == self.LOCK_STATUS_LOCK:
                self.locker.lock()
                continue
            if status == self.LOCK_STATUS_UNLOCK:
                self.locker.unlock()
                self.lastInputTime = win32api.GetTickCount()
                continue

            skipTime = self.readIntData(self.SKIP_TIME_IDX)
            if win32api.GetTickCount() <= skipTime:
                continue

            idleTime = self.getIdleTime()
            #print('idleTime = ', idleTime)
            if idleTime >= self.MAX_IDLE_TIME:
                self.locker.lock()
                continue

if __name__ == '__main__':
    locker = ScreenLocker()
    locker.createWindow()

    main = Main(locker)
    main.start()

    #locker.lock()
    win32gui.PumpMessages()

    # pyinstaller.exe -F -w screenlocker.py base_win.py   生成无cmd窗口的exe程序