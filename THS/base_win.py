import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os

class BaseWindow:
    bindHwnds = {}

    def __init__(self) -> None:
        self.hwnd = None
        self.oldProc = None
        self.listeners = []
    
    # func = function(target, evtName, evtInfo)
    def addListener(self, target, func):
        self.listeners.append((target, func))

    def notifyListener(self, evtName, evtInfo):
        for ls in self.listeners:
            obj, func = ls
            func(obj, evtName, evtInfo)

    # @param rect = (x, y, width, height)
    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className = 'STATIC', title = ''): #  0x00800000 | 
        self.hwnd = win32gui.CreateWindow(className, title, style, *rect, parentWnd, None, None, None)
        BaseWindow.bindHwnds[self.hwnd] = self
        self.oldProc = win32gui.SetWindowLong(self.hwnd, win32con.GWL_WNDPROC, BaseWindow._WinProc)
        print(f'[BaseWindow.createWindow] self.oldProc=0x{self.oldProc :x}, title=', title)
    
    # @return [x, y, width, height]
    def getRect(self):
        if not self.hwnd:
            return None
        l, t, r, b = win32gui.GetClientRect(self.hwnd)
        return [l, t, r - l, b - t]
    
    # @return True: 已处理事件,  False:未处理事件
    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_PAINT:
            self._draw()
            return True
        if msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return True
        return False

    def _draw(self, fontSize = 14):
        hdc, ps = win32gui.BeginPaint(self.hwnd)
        l, t, r, b = win32gui.GetClientRect(self.hwnd)
        w, h = r - l, b - t
        mdc = win32gui.CreateCompatibleDC(hdc)
        bmp = win32gui.CreateCompatibleBitmap(hdc, w, h)
        win32gui.SelectObject(mdc, bmp)
        bk = win32gui.CreateSolidBrush(0x000000)
        win32gui.FillRect(mdc, win32gui.GetClientRect(self.hwnd), bk)
        win32gui.SetBkMode(mdc, win32con.TRANSPARENT)
        win32gui.SetTextColor(mdc, 0x0)
        a = win32gui.LOGFONT()
        a.lfHeight = fontSize
        a.lfFaceName = '新宋体'
        font = win32gui.CreateFontIndirect(a)
        win32gui.SelectObject(mdc, font)
        self.draw(mdc)
        win32gui.BitBlt(hdc, 0, 0, w, h, mdc, 0, 0, win32con.SRCCOPY)
        win32gui.EndPaint(self.hwnd, ps)
        win32gui.DeleteObject(font)
        win32gui.DeleteObject(bk)
        win32gui.DeleteObject(bmp)
        win32gui.DeleteObject(mdc)
        return True
        
    def draw(self, hdc):
        pass

    @staticmethod
    def _WinProc(hwnd, msg, wParam, lParam):
        self = BaseWindow.bindHwnds[hwnd]
        rs = self.winProc(hwnd, msg, wParam, lParam)
        if rs == True:
            return 0
        if rs != False:
            return rs
        #if self.oldProc:
        #    return win32gui.CallWindowProc(self.oldProc, hwnd, msg, wParam, lParam)
        return win32gui.DefWindowProc(hwnd, msg, wParam, lParam)