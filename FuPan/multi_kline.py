import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr
from THS import orm as ths_orm
from Common import base_win, kline

class MultiKLineWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.layout = None #  GridLayout
        self.klines = []
        self.codeInfo = None # {code, name, gn, hy}
        self.selDay = None

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.adjustChildKLine(3)

    def setMarkDay(self, markDay):
        for k in self.klines:
            k.indicators[0].setMarkDay(markDay)
            k.invalidWindow()
        
    def makeVisible(self, day):
        model = self.klines[0].model
        if not model or not day:
            return
        if type(day) == str:
            day = int(day.replace('-', ''))
        idx = model.getItemIdx(day)
        for kl in self.klines:
            kl.makeVisible(idx)

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
            idt = kline.KLineIndicator(win, {'height': -1, 'margins': (10, 10)})
            win.addIndicator(idt)
            idt = kline.AmountIndicator(win, {'height': 50, 'margins': (10, 3)})
            win.addIndicator(idt)
            self.klines.append(win)
            win.createWindow(self.hwnd, (0, 0, 10, 10))
            self.layout.setContent(i, 0, win)
            win.addListener(self.onListen, i)
        self.layout.resize(0, 0, *self.getClientSize())

    def findByDayInData(self, day, fromIdx, data):
        i = fromIdx
        while i < len(data):
            if data[i].day < day:
                i += 1
            elif day == data[i].day:
                return True, i
            else:
                return False, max(i - 1, 0)
        return False, i - 1

    def adjustDataLength_2(self, days, model):
        fromIdx = 0
        rsData = []
        for day in days:
            fd, idx = self.findByDayInData(day, fromIdx, model.data)
            if fd:
                rsData.append(model.data[idx])
            else:
                dd = copy.copy(model.data[idx])
                dd.low = dd.high = dd.open = dd.close
                dd.amount = dd.vol = dd.rate = 0
                dd.day = day
                rsData.append(dd)
            fromIdx = idx
        model.data.clear()
        del model.data
        model.data = rsData

    def adjustDataLength(self, *models):
        models = [m for m in models if m and m.data]
        if not models:
            return
        days = set()
        for m in models:
            for d in m.data:
                days.add(d.day)
        days = list(days)
        days.sort()
        if len(days) > 500:
            days = days[-500 : ]
        for m in models:
            self.adjustDataLength_2(days, m)

    def updateCode(self, code):
        self.dataLen = 0
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
        md1 = kline.KLineModel_Ths(code)
        md1.loadDataFile()
        self.codeInfo = obj.__data__
        hy = self.codeInfo['hy'].split('-')
        hy2, hy3 = hy[1], hy[2]
        hy2Obj = ths_orm.THS_ZS.get_or_none(name = hy2.strip(), hydj = '二级行业')
        hy3Obj = ths_orm.THS_ZS.get_or_none(name = hy3.strip(), hydj = '三级行业')
        gn = obj.gn.split(';')
        for i in range(len(gn)):
            gn[i] = gn[i].replace('【', '').replace('】', '').strip()
        gnObj = ths_orm.THS_ZS.select().where(ths_orm.THS_ZS.gnhy == '概念', ths_orm.THS_ZS.name.in_(gn))
        gnModel = [d.__data__ for d in gnObj ]
        gnModel.insert(0, {'title' : 'LINE'})
        if hy3Obj: gnModel.insert(0, hy3Obj.__data__)
        if hy2Obj: gnModel.insert(0, hy2Obj.__data__)
        gnModel.insert(0, {'code' : code, 'name' : obj.name})
        for d in gnModel:
            if 'code' in d and 'name' in d:
                d['title'] = d['name'] + ' ' + d['code']
        md2, md3 = None, None
        if hy3Obj:
            md3 = kline.KLineModel_Ths(hy3Obj.code)
            md3.loadDataFile()
        elif hy2Obj:
            md2 = kline.KLineModel_Ths(hy2Obj.code)
            md2.loadDataFile()
        self.adjustDataLength(md1, md2, md3)
        self.klines[0].setModel(md1)
        self.klines[1].setModel(md2 or md3)
        #self.klines[2].setModel(md3)
        self.klines[0].makeVisible(-1)
        self.klines[1].makeVisible(-1)
        #self.klines[2].makeVisible(-1)
        #self.klines[0].setPopupMenu(gnModel, self.onMenuItemClick, 0)
        #self.klines[1].setPopupMenu(gnModel, self.onMenuItemClick, 1)
        #self.klines[2].setPopupMenu(gnModel, self.onMenuItemClick, 2)

    def onMenuItemClick(self, klineIdx, idx, menuItem):
        md = kline.KLineModel_Ths(menuItem['code'])
        md.loadDataFile()
        days = [d.day for d in self.klines[0].model.data]
        self.adjustDataLength_2(days, md)
        target = self.klines[(klineIdx + 1) % len(self.klines)]
        self.klines[klineIdx].setModel(md)
        self.klines[klineIdx].makeVisible(target.selIdx)

    def onListen(self, evtName, evtInfo, args):
        curWinIdx = args
        for i, kl in enumerate(self.klines):
            if i == curWinIdx:
                continue
            if evtName == 'Event.MouseMove':
                kl.onMouseMove(evtInfo['x'], evtInfo['y'])
            elif evtName == 'Event.KeyDown':
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
    win.updateCode('600053')
    win32gui.PumpMessages()