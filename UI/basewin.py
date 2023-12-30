import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os

class BaseWindow:
    bindHwnds = {} # {hwnd: KLineView}

    def __init__(self) -> None:
        self.hwnd = None
        self.rect = None # [x, y, width, height]

    # @param rect = [x, y, width, height]
    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD): #  0x00800000 | 
        self.hwnd = win32gui.CreateWindow('STATIC', 'KLineWindow', style, rect[0], rect[1], rect[2], rect[3], parentWnd, None, None, None)
        BaseWindow.bindHwnds[self.hwnd] = self
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_WNDPROC, BaseWindow._WinProc)
        self.rect = rect
    
    # @return True: 已处理事件,  False:未处理事件
    def winProc(hwnd, msg, wParam, lParam):
        return False

    @staticmethod
    def _WinProc(hwnd, msg, wParam, lParam):
        self = BaseWindow.bindHwnds[hwnd]
        if self.winProc(hwnd, msg, wParam, lParam):
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wParam, lParam)