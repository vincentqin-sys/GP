from win32.lib.win32con import WS_CHILD, WS_VISIBLE
import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr
from THS import orm, ths_win
from Common import base_win, timeline

class DddlrStructWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, 20, '1fr')
        cols = ('1fr', '1fr', '1fr', '1fr', '1fr')
        self.layout = base_win.GridLayout(rows, cols, (5, 10))
        self.listWins = []
        self.daysLabels =[]

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        datePicker = base_win.DatePicker()
        datePicker.createWindow(self.hwnd, (10, 10, 200, 30))
        absLayout = base_win.AbsLayout()
        absLayout.setContent(0, 0, datePicker)
        self.layout.setContent(0, 0, absLayout)
        def formateFloat(colName, val, rowData):
            return f'{val :.02f}'
        headers = [{'title': '', 'width': 60, 'name': '#idx' },
                   {'title': '股票名称', 'width': 0.1, 'name': 'name' },
                   {'title': '净流入', 'width': 70, 'name': 'total', 'formater': formateFloat },
                   {'title': '流入', 'width': 70, 'name': 'in', 'formater': formateFloat},
                   {'title': '流出', 'width': 70, 'name': 'out', 'formater': formateFloat }]
        for i in range(len(self.layout.templateColumns)):
            win = base_win.TableWindow()
            win.createWindow(self.hwnd, (0, 0, 1, 1))
            win.headers = headers
            self.layout.setContent(2, i, win)
            self.listWins.append(win)
            lw = win32gui.CreateWindow('STATIC', '', win32con.WS_VISIBLE|win32con.WS_CHILD, 0, 0, 1, 1, self.hwnd, None, None, None)
            self.daysLabels.append(lw)
            self.layout.setContent(1, i, lw)
        datePicker.addListener(self.onSelDayChanged, None)

    def onSelDayChanged(self, evtName, evtInfo, args):
        if evtName != 'Select':
            return
        self.updateDay(evtInfo['day'])

    def updateDay(self, day):
        if type(day) == int:
            day = str(day)
        day = day.replace('-', '')
        q = orm.THS_DDLR.select(orm.THS_DDLR.day).distinct().where(orm.THS_DDLR.day <= day).order_by(orm.THS_DDLR.day.desc()).limit(5).tuples()
        for i, d in enumerate(q):
            cday = d[0]
            ds = orm.THS_DDLR.select().where(orm.THS_DDLR.day == cday)
            datas = [d.__data__ for d in ds]
            for xd in datas:
                xd['in'] = xd['activeIn'] + xd['positiveIn']
                xd['out'] = xd['activeOut'] + xd['positiveOut']
            self.listWins[i].data = datas
            self.listWins[i].invalidWindow()
            sday = cday[0 : 4] + '-' + cday[4 : 6] + '-' + cday[6 : ]
            win32gui.SetWindowText(self.daysLabels[i], sday)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            size = self.getClientSize()
            self.layout.resize(0, 0, size[0], size[1])
            self.invalidWindow()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)