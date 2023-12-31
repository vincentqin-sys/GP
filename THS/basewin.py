import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os

class BaseWindow:
    bindHwnds = {}

    def __init__(self) -> None:
        self.hwnd = None
        self.listeners = []

    def addListener(self, obj):
        self.listeners.append(obj)

    def notifyListener(self, evtName, info):
        for s in self.listeners:
            s.onListen(evtName, info)

    def onListen(self, evtName, info):
        pass

    # @param rect = (x, y, width, height)
    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className = 'STATIC', title = ''): #  0x00800000 | 
        self.hwnd = win32gui.CreateWindow(className, title, style, *rect, parentWnd, None, None, None)
        BaseWindow.bindHwnds[self.hwnd] = self
        self.oldProc = win32gui.SetWindowLong(self.hwnd, win32con.GWL_WNDPROC, BaseWindow._WinProc)
        #print('oldProc=', self.oldProc)
    
    # @return [x, y, width, height]
    def getRect(self):
        l, t, r, b = win32gui.GetClientRect(self.hwnd)
        return l, t, r - l, b - t
    
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
        bk = win32gui.CreateSolidBrush(0x000000)
        win32gui.FillRect(hdc, win32gui.GetClientRect(self.hwnd), bk)
        #pen = win32gui.CreatePen(win32con.PS_SOLID, 2, 0xff00ff)
        #win32gui.SelectObject(hdc, pen)
        win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
        win32gui.SetTextColor(hdc, 0x0)

        a = win32gui.LOGFONT()
        a.lfHeight = fontSize
        a.lfFaceName = '新宋体'
        font = win32gui.CreateFontIndirect(a)
        win32gui.SelectObject(hdc, font)
        self.draw(hdc)
        win32gui.EndPaint(self.hwnd, ps)
        win32gui.DeleteObject(font)
        win32gui.DeleteObject(bk)
        #win32gui.DeleteObject(pen)
        return True
        
    def draw(self, hdc):
        pass

    @staticmethod
    def _WinProc(hwnd, msg, wParam, lParam):
        self = BaseWindow.bindHwnds[hwnd]
        if self.winProc(hwnd, msg, wParam, lParam):
            return 0
        #return win32gui.DefWindowProc(hwnd, msg, wParam, lParam)
        return win32gui.CallWindowProc(self.oldProc, hwnd, msg, wParam, lParam)