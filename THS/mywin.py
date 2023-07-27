import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os
import query

#-----------------------------------------------------------
class EyeWindow:
    def __init__(self) -> None:
        self.eyeChildWnd = None
        self.wrapWnd = None
        wc = win32gui.WNDCLASS()
        wc.hbrBackground = win32con.COLOR_WINDOW
        wc.hCursor = win32api.LoadCursor( 0, win32con.IDC_ARROW)
        wc.lpszClassName = 'MyEyeWndClass'
        wc.lpfnWndProc = eyeWndProc
        self.wndClazz = win32gui.RegisterClass(wc)

    def createWindow(self):
        if self.wrapWnd and win32gui.IsWindow(self.wrapWnd):
            return
        self.wrapWnd = win32gui.CreateWindow(self.wndClazz, 'Eye-Window', win32con.WS_OVERLAPPEDWINDOW, 0, 0, 1000, 500, None, None, None, None)
        win32gui.ShowWindow(self.wrapWnd, win32con.SW_SHOWMAXIMIZED)
    
    def show(self):
        if self.eyeChildWnd and win32gui.IsWindow(self.eyeChildWnd):
            return
        self.eyeChildWnd = win32gui.FindWindow('#32770', '短线精灵')
        if self.eyeChildWnd:
            win32gui.SetParent(self.eyeChildWnd, self.wrapWnd)
            win32gui.UpdateWindow(self.eyeChildWnd)

def eyeWndProc(hwnd, msg, wParam, lParam):
    return win32gui.DefWindowProc(hwnd, msg, wParam, lParam)

eyeWindow = EyeWindow()
#-----------------------------------------------------------

# 同行比较排名窗口信息
class SortInfoWindow:
    def __init__(self) -> None:
        self.wnd = None
        self.size = None  # 窗口大小 (w, h)
        self.maxMode = True #  是否是最大化的窗口
        self.curCode = None
        self.textInfo = ''

    def createWindow(self, parentWnd):
        style = (0x00800000 | 0x10000000 | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION) & ~win32con.WS_SYSMENU
        w = win32api.GetSystemMetrics(0) # desktop width
        self.size = (200, 135)
        self.wnd = win32gui.CreateWindowEx(win32con.WS_EX_TOOLWINDOW, 'STATIC', '', style, w - 260 - self.size[0], 150, *self.size, parentWnd, None, None, None)
        win32gui.SetWindowPos(self.wnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        win32gui.SetWindowLong(self.wnd, win32con.GWL_WNDPROC, sortInfoWinProc)
        win32gui.ShowWindow(self.wnd, win32con.SW_NORMAL)

    def changeCode(self, code):
        if (self.curCode == code) or (not code):
            return
        self.curCode = code
        self.textInfo = query.getCodeInfo(self.curCode)
        if self.wnd and self.size:
            #win32gui.InvalidateRect(self.wnd, (0, 0, *self.size), True)
            #win32gui.UpdateWindow(self.wnd)
            win32gui.InvalidateRect(self.wnd, None, True)
            #win32gui.PostMessage(self.wnd, win32con.WM_PAINT)

    def onDraw(self):
        hwnd = self.wnd
        hdc, ps = win32gui.BeginPaint(hwnd)
        bk = win32gui.CreateSolidBrush(0x000000)
        win32gui.FillRect(hdc, win32gui.GetClientRect(hwnd), bk)
        win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
        win32gui.SetTextColor(hdc, 0x0)

        a = win32gui.LOGFONT()
        a.lfHeight = 16
        a.lfFaceName = '新宋体'
        font = win32gui.CreateFontIndirect(a)
        win32gui.SelectObject(hdc, font)
        self.drawContent(hdc)
        win32gui.EndPaint(hwnd, ps)
        win32gui.DeleteObject(font)
        win32gui.DeleteObject(bk)
    
    def drawContent(self, hdc):
        win32gui.SetTextColor(hdc, 0xdddddd)
        rr = list(win32gui.GetClientRect(self.wnd))
        rr[0] = rr[1] = 5
        rr = tuple(rr)
        win32gui.DrawText(hdc, self.textInfo, len(self.textInfo), rr, 0)
        

def sortInfoWinProc(hwnd, msg, wParam, lParam):
    if msg == win32con.WM_PAINT:
        sortInfoWindow.onDraw()
    return win32gui.DefWindowProc(hwnd, msg, wParam, lParam)

sortInfoWindow = SortInfoWindow()
#sortInfoWindow.createWindow(0X100706)
#sortInfoWindow.changeCode('000977')
#win32gui.PumpMessages()
#------------------------------------------

