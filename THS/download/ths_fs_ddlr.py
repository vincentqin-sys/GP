import os, json, time, sys, pyautogui
import io, psutil, subprocess
import win32gui, win32con , win32api, win32ui, win32process # pip install pywin32
from load_ths_ddlr import ThsDdlrDetailData

# 大单分时窗口(是分时图的子窗口)
class THS_DDFSWindow:
    bindData = {}
    touMingColor = 0xfafafa

    def __init__(self) -> None:
        self.hwnd = None
        self.fenShiWnd = None
        self.curDay = None
        self.curCode = None
        self.size = None
        self.detailData = None # 大单分时详细数据  ThsDdlrDetailData
        self.points = None # 大单分时点 [ {rect, bs, money} ]

    def findFenShiWindow(self):
        def callback(hwnd, lparam):
            title = win32gui.GetWindowText(hwnd)
            if '左右方向键切换分时' in title and win32gui.IsWindowVisible(hwnd):
                if ('(' in title) and (')' in title):
                    begin, end = title.index('('), title.index(')')
                    self.curCode = title[begin + 1 : end]
                    self.curDay = title[end + 2 : end + 12]
                    #p1 = win32gui.FindWindowEx(hwnd, None, 'msctls_statusbar32', None)
                    #self.parentHwnd = win32gui.FindWindowEx(p1, None, 'AfxFrameOrView140s', None)
                    self.fenShiWnd = hwnd
                    print(f'fenShiWnd = 0x{self.fenShiWnd :X} curCode = {self.curCode} curDay = {self.curDay}')
            return True
        win32gui.EnumWindows(callback, None)

    def createWindow(self):
        self.findFenShiWindow()
        if not self.fenShiWnd:
            return
        style = win32con.WS_POPUP| win32con.WS_VISIBLE | win32con.WS_CAPTION | win32con.WS_SYSMENU
        rect = win32gui.GetWindowRect(self.fenShiWnd)
        HEIGHT = int((rect[3] - rect[1]) * 0.6)
        x, y = rect[0] + 30, rect[1]
        w = rect[2] - rect[0] - 30 - 30
        self.size = (w, HEIGHT)
        print(f'x={x} y={y}, size={self.size}')
        self.hwnd = win32gui.CreateWindowEx(win32con.WS_EX_LAYERED, 'STATIC', '分时大单', style, x, y, w, HEIGHT, None, None, win32gui.GetModuleHandle(None), None)
        win32gui.SetLayeredWindowAttributes(self.hwnd, THS_DDFSWindow.touMingColor, 0, win32con.ULW_COLORKEY)
        #self.hwnd = win32gui.CreateWindow('STATIC', 'Hello', style, x, y, w, HEIGHT, None, None, win32gui.GetModuleHandle(None), None)
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOMOVE)
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_WNDPROC, THS_DDFSWindow._winProc)
        THS_DDFSWindow.bindData[self.hwnd] = self
        self.detailData = ThsDdlrDetailData(self.curCode)

    def draw(self):
        hdc, ps = win32gui.BeginPaint(self.hwnd)
        bk = win32gui.CreateSolidBrush(THS_DDFSWindow.touMingColor)
        win32gui.SelectObject(hdc, bk)
        win32gui.FillRect(hdc, win32gui.GetClientRect(self.hwnd), bk)
        win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
        win32gui.SetTextColor(hdc, 0x0)
        self._draw(hdc)
        win32gui.EndPaint(self.hwnd, ps)
        win32gui.DeleteObject(bk)

    def timeToIdx(self, _time):
        hour = _time // 100
        minutes = _time % 100
        idx = 0
        if hour == 9:
            return minutes - 30
        if hour == 10 or hour == 11:
            return (hour - 9) * 60 + minutes - 30
        return ((hour - 13) + 2) + minutes - 30

    def _drawOneMinute(self, hdc, x, data, zeroY, stepY, hbr):
        win32gui.SelectObject(hdc, hbr)
        ZJ = 10  # 直径
        for dt in data:
            points = (x - ZJ // 2, zeroY - ZJ // 2, x + ZJ // 2, zeroY + ZJ // 2)
            zeroY += stepY
            win32gui.Ellipse(hdc, *points)

    def _draw(self, hdc):
        pen1 = win32gui.CreatePen(win32con.PS_SOLID, 2, 0xff0000)
        redHbr = win32gui.CreateSolidBrush(0x0000ff)
        greenHbr = win32gui.CreateSolidBrush(0x00ff00)
        redPen = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x0000ff)
        greenPen = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ff00)
        win32gui.SelectObject(hdc, pen1)
        #win32gui.Rectangle(hdc, *win32gui.GetClientRect(self.hwnd))
        _, _, w, h = win32gui.GetClientRect(self.hwnd)
        zeroY = h // 2 - 1
        win32gui.MoveToEx(hdc, 0, zeroY)
        win32gui.LineTo(hdc, w, zeroY) # 0轴间分隔线
        internal = w / 240
        data = self.detailData.getDataAtDay(self.curDay)
        if not data:
            return
        fromIdx, endIdx = 0, 0
        while endIdx < len(data):
            idxs = self.detailData.getMiniteDataRange(data, endIdx)
            if not idxs:
                break
            fromIdx, endIdx = idxs
            if fromIdx >= len(data):
                break
            minute = data[fromIdx][0]
            i = self.timeToIdx(minute)
            if i < 0:
                x = 15
            else:
                x = int(i * internal) + 30
            buyData = [data[fe] for fe in range(fromIdx, endIdx) if data[fe][1] <= 2]
            sellData = [data[fe] for fe in range(fromIdx, endIdx) if data[fe][1] > 2]
            win32gui.SelectObject(hdc, redPen)
            self._drawOneMinute(hdc, x, buyData, zeroY - 15, -15, redHbr)
            win32gui.SelectObject(hdc, greenPen)
            self._drawOneMinute(hdc, x, sellData, zeroY + 15, 15, greenHbr)
        win32gui.DeleteObject(pen1)


    @staticmethod
    def _winProc(hwnd, msg, wparam, lparam):
        thiz = THS_DDFSWindow.bindData[hwnd]
        if msg == win32con.WM_PAINT:
            if not getattr(thiz, 'memDC', None):
                hdc = win32gui.GetDC(hwnd)
                thiz.memDC = win32gui.CreateCompatibleDC(hdc)
                thiz.memBitmap = win32gui.CreateCompatibleBitmap(hdc, *thiz.size)
                win32gui.SelectObject(thiz.memDC, thiz.memBitmap)
                win32gui.ReleaseDC(hwnd, hdc)
            thiz.draw()
            return 0
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            win32gui.DeleteObject(thiz.memDC)
            win32gui.DeleteObject(thiz.memBitmap)
            return 0
        elif msg == win32con.WM_LBUTTONDBLCLK:
            #hotWindow.changeMode()
            #showSortAndLiangDianWindow(not hotWindow.maxMode, True)
            return 0
        elif msg == win32con.WM_RBUTTONUP:
            #hotWindow.changeDataType()
            return 0
        #elif msg == win32con.WM_SIZE:
        #    return 0
        elif msg == win32con.WM_NCHITTEST:
            return win32con.HTCAPTION
        else:
            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
        

if __name__ == '__main__':
    fsWin = THS_DDFSWindow()
    fsWin.createWindow()
    win32gui.PumpMessages()