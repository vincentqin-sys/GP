from win32.lib.win32con import WS_CHILD, WS_VISIBLE
import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr
from THS import orm, ths_win
from Common import base_win, timeline, kline

class ZSWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, 20, '1fr')
        self.cols = ('1fr', '1fr', '1fr', '1fr')
        self.layout = base_win.GridLayout(rows, self.cols, (5, 10))
        self.listWins = []
        self.daysLabels =[]

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        datePicker = base_win.DatePicker()
        datePicker.createWindow(self.hwnd, (10, 10, 200, 30))
        absLayout = base_win.AbsLayout()
        absLayout.setContent(0, 0, datePicker)
        self.layout.setContent(0, 0, absLayout)
        def formateRate(colName, val, rowData):
            return f'{val :.02f}%'
        def formateMoney(colName, val, rowData):
            return f'{int(val)}'
        def sortPM(colName, val, rowData, allDatas, asc):
            if val > 0:
                return val
            elif val < 0:
                return len(allDatas) + val + 100
            # == 0
            if asc:
                return 10000
            return -10000
        headers = [ #{'title': '', 'width': 60, 'name': '#idx' },
                   {'title': '指数名称', 'width': 0.1, 'name': 'name' },
                   {'title': '成交额', 'width': 80, 'name': 'money', 'formater': formateMoney },
                   {'title': '涨幅', 'width': 70, 'name': 'zdf', 'formater': formateRate},
                   {'title': '50亿排名', 'width': 70, 'name': 'zdf_50PM', 'sorter': sortPM},
                   {'title': '全市排名', 'width': 70, 'name': 'zdf_PM', 'sorter': sortPM}]
        for i in range(len(self.layout.templateColumns)):
            win = base_win.TableWindow()
            win.createWindow(self.hwnd, (0, 0, 1, 1))
            win.headers = headers
            self.layout.setContent(2, i, win)
            self.listWins.append(win)
            lw = base_win.Label()
            lw.createWindow(self.hwnd, (0, 0, 1, 1))
            self.daysLabels.append(lw)
            self.layout.setContent(1, i, lw)
            win.addListener(self.onDbClick, i)
        datePicker.addListener(self.onSelDayChanged, None)

    def onSelDayChanged(self, evtName, evtInfo, args):
        if evtName != 'Select':
            return
        # TODO: change models
        self.updateDay(evtInfo['day'])
    
    def onDbClick(self, evtName, evtInfo, idx):
        if evtName != 'DbClick' and evtName != 'RowEnter':
            return
        data = evtInfo['data']
        if not data:
            return
        win = kline.KLineWindow()
        win.showSelTip = True
        win.addDefaultIndicator(kline.KLineWindow.INDICATOR_KLINE | kline.KLineWindow.INDICATOR_AMOUNT)
        dw = win32api.GetSystemMetrics (win32con.SM_CXFULLSCREEN)
        dh = win32api.GetSystemMetrics (win32con.SM_CYFULLSCREEN)
        W, H = 1000, 450
        x = (dw - W) // 2
        y = (dh - H) // 2
        win.createWindow(self.hwnd, (x, y, W, H), win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION)
        model = kline.KLineModel_Ths(data['code'])
        model.loadDataFile()
        win.setModel(model)
        win.setMarkDay(data['day'])
        win.makeVisible(-1)

    def updateDay(self, day):
        if type(day) == int:
            day = str(day)
        day = day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
        q = orm.THS_ZS_ZD.select(orm.THS_ZS_ZD.day).distinct().where(orm.THS_ZS_ZD.day <= day).order_by(orm.THS_ZS_ZD.day.desc()).limit(len(self.cols)).tuples()
        for i, d in enumerate(q):
            cday = d[0]
            ds = orm.THS_ZS_ZD.select().where(orm.THS_ZS_ZD.day == cday)
            datas = [d.__data__ for d in ds]
            self.listWins[i].setData(datas)
            self.listWins[i].invalidWindow()
            sday = cday[0 : 4] + '-' + cday[4 : 6] + '-' + cday[6 : ]
            self.daysLabels[i].setText(cday)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            size = self.getClientSize()
            self.layout.resize(0, 0, size[0], size[1])
            self.invalidWindow()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)