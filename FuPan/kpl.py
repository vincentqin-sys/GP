from win32.lib.win32con import WS_CHILD, WS_VISIBLE
import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys

cwd = os.getcwd()
w = cwd.index('GP')
cwd = cwd[0 : w + 2]
sys.path.append(cwd)
from Tdx import datafile, orm as tdx_orm
from THS.download import henxin, load_ths_ddlr
from THS import orm as ths_orm, base_win, kline
from FuPan import ddlr, multi_kline

class KPL_Window(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.day = None
        self.data = None

    def onDraw(self, hdc):
        self.drawSCQX(hdc)
        pass

    def drawSCQX(self, hdc):
        self.drawer.fillRect(hdc, (0, 0, *self.getClientSize()), 0xff0000)
        pass

    def updateDay(self, day):
        if self.day == day or not day:
            return
        if type(day) == str:
            day = int(day.replace('-', ''))
        self.day = day
        obj = tdx_orm.TdxLSModel.get_or_none(day = self.day)
        if not obj:
            self.data = {}
        else:
            self.data = obj.__data__
        day = f'{self.day // 10000}-{self.day // 100 % 100 :02d}-{self.day % 100 :02d}'
        obj = ths_orm.KPL_SCQX.get_or_none(day = day)
        if obj:
            self.data['zhqd'] = obj.zhqd

class KPL_ZT_TableWindow(base_win.TableWindow):
    def __init__(self) -> None:
        super().__init__()
        self.headers = [{'name':'code', 'title':'股票名称'}, {'name':'ztTime', 'title':'涨停时间'}, {'name':'status', 'title':'状态'}, {'name':'ztReason', 'title':'涨停原因'}] # {'name':'#idx', 'title':''}, 
        self.columnCount = len(self.headers)


class KPL_MgrWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.layout = base_win.GridLayout((170, 30, '1fr'), (300, '1fr'), (10, 10))
        self.kplWin = KPL_Window()
        self.kplTableWin = KPL_ZT_TableWindow()
        self.multiKLineWin = multi_kline.MultiKLineWindow()

    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.layout.setContent(0, 0, self.kplWin)
        self.layout.setContent(2, 0, self.kplTableWin)
        self.layout.setContent(0, 1, self.multiKLineWin, {'verExpand' : -1})
        gl = base_win.GridLayout(('100%', ), (40, '1fr', 40), (0, 5))
        preDayBtn = base_win.Button({'name': 'pre-day-btn', 'title': '<<'})
        nextDayBtn = base_win.Button({'name': 'next-day-btn', 'title': '>>'})
        preDayBtn.addListener('pre', self.onLisetenSelectDay)
        nextDayBtn.addListener('next', self.onLisetenSelectDay)
        preDayBtn.createWindow(self.hwnd, (0, 0, 40, 30))
        nextDayBtn.createWindow(self.hwnd, (0, 0, 40, 30))
        gl.setContent(0, 0, preDayBtn)
        gl.setContent(0, 2, nextDayBtn)
        self.layout.setContent(1, 0, gl)
        self.kplWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.kplTableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.multiKLineWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.layout.resize(0, 0, *self.getClientSize())

    def onLisetenSelectDay(self, target, evtName, evtInfo):
        print('onLisetenSelectDay: ', target, evtName, evtInfo)
        pass

    def onLisetenEvent(self, target, evtName, evtInfo):
        print('onLisetenEvent: ', target, evtName, evtInfo)
        pass

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            w, h = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.layout.resize(0, 0, w, h)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)


if __name__ == '__main__':
    kpl = KPL_MgrWindow()
    kpl.createWindow(None, (0, 0, 1000, 400), win32con.WS_OVERLAPPEDWINDOW)
    win32gui.ShowWindow(kpl.hwnd, win32con.SW_MAXIMIZE)
    win32gui.PumpMessages()