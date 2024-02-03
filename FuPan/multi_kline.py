import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys

cwd = os.getcwd()
w = cwd.index('GP')
cwd = cwd[0 : w + 2]
sys.path.append(cwd)
from Tdx import datafile
from THS.download import henxin, load_ths_ddlr
from THS import orm as ths_orm, base_win, kline


class MultiKLineWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.layout = None #  GridLayout
        self.klines = []
        self.codeInfo = None # {code, name, gn, hy}
        self.selDay = None

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)

    def adjustChildKLine(self, childKlineNum = 3):
        rowTmp = ('1fr', ) * childKlineNum
        if self.layout:
            del self.layout
        self.layout = base_win.GridLayout(rowTmp, ('100%', ), (5, 10))
        for kl in self.klines:
            win32gui.DestroyWindow(kl.hwnd)
        self.klines.clear()
        for i in range(childKlineNum):
            win = kline.KLineWindow()
            idt = kline.KLineIndicator(win, {'height': -1, 'margins': (10, 0)})
            win.addIndicator(idt)
            idt = kline.AmountIndicator(win, {'height': 50, 'margins': (10, 0)})
            win.addIndicator(idt)
            self.klines.append(win)
            win.createWindow(self.hwnd, (0, 0, 10, 10))
            self.layout.setContent(i, 0, win)
            win.addListener(i, self.onListen)
        self.layout.resize(0, 0, *self.getClientSize())

    def updateCode(self, code):
        if type(code) == int:
            code = f'{code :06d}'
        if not code:
            return
        if code[0] != '6' and code[0] != '3' and code[0] != '0':
            # not a GP
            return
        obj = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == code)
        if not obj:
            return
        self.codeInfo = obj.__data__
        hy = self.codeInfo['hy'].split('-')
        hy2, hy3 = hy[1], hy[2]
        hy2Obj = ths_orm.THS_ZS.get_or_none(name = hy2.strip(), hydj = '二级行业')
        hy3Obj = ths_orm.THS_ZS.get_or_none(name = hy3.strip(), hydj = '三级行业')
        md2, md3 = None, None
        if hy2Obj:
            md2 = kline.KLineModel_Ths(hy2Obj.code)
            md2.loadDataFile()
        if hy3Obj:
            md3 = kline.KLineModel_Ths(hy3Obj.code)
            md3.loadDataFile()
            
        if md2 and md3:
            if len(md2.data) > len(md3.data):
                md2.data = md2.data[len(md2.data) -len(md3.data) : ]
            elif len(md2.data) < len(md3.data):
                md3.data = md3.data[len(md3.data) -len(md2.data) : ]
        self.klines[0].setModel(md2)
        self.klines[0].makeVisible(-1)
        self.klines[1].setModel(md3)
        self.klines[1].makeVisible(-1)

    def onListen(self, target, evtName, evtInfo):
        curWinIdx = target
        for i, kl in enumerate(self.klines):
            if i == curWinIdx:
                continue
            if evtName == 'Event.onMouseMove':
                kl.onMouseMove(evtInfo['x'], evtInfo['y'])
            elif evtName == 'Event.onKeyDown':
                kl.onKeyDown(evtInfo['oem'])

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            if self.layout:
                w = lParam & 0xffff
                h = (lParam >> 16) & 0xffff
                self.layout.resize(0, 0, w, h)
            return False
        return super().winProc(hwnd, msg, wParam, lParam)
    

if __name__ == '__main__':
    win = MultiKLineWindow()
    win.createWindow(None, (0, 0, 100, 100), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    win32gui.ShowWindow(win.hwnd, win32con.SW_MAXIMIZE)
    win.adjustChildKLine(3)
    win.updateCode('600053')
    win32gui.PumpMessages()