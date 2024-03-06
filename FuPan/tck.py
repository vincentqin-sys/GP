from win32.lib.win32con import WS_CHILD, WS_VISIBLE
import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr
from THS import orm, ths_win
from Common import base_win, timeline, kline

class TCK_Window(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, '1fr')
        self.cols = (300, '1fr')
        self.layout = base_win.GridLayout(rows, self.cols, (5, 10))
        self.tableWin = base_win.TableWindow()
        self.editorWin = base_win.Editor()
        self.tckData = None

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        def formateMoney(colName, val, rowData):
            return f'{int(val)}'
        def sortPM(colName, val, rowData, allDatas, asc):
            return val
        headers = [ {'title': '', 'width': 60, 'name': '#idx' },
                   {'title': '日期', 'width': 100, 'name': 'day' },
                   {'title': '名称', 'width': 80, 'name': 'name' },
                   {'title': '代码', 'width': 80, 'name': 'code' },
                   {'title': '开盘啦', 'width': 200, 'name': 'kpl_ztReason' },
                   {'title': '同花顺', 'width': 80, 'name': 'ths_status' },
                   {'title': '同花顺', 'width': 250, 'name': 'ths_ztReason' },
                   {'title': '财联社', 'width': 120, 'name': 'cls_ztReason' },
                   {'title': '财联社详细', 'width': 0.1, 'name': 'cls_detail' },
                   ]
        self.editorWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.rowHeight = 40
        self.tableWin.headers = headers
        self.layout.setContent(0, 0, self.editorWin)
        self.layout.setContent(1, 0, self.tableWin, {'horExpand': -1})
        self.editorWin.addListener(self.onEditEnd, None)
        self.tableWin.addListener(self.onDbClick, None)

    def onEditEnd(self, evtName, evtInfo, args):
        if evtName != 'PressEnter':
            return
        self.doSearch(evtInfo)

    def onDbClick(self, evtName, evtInfo, args):
        if evtName != 'DbClick' and evtName != 'RowEnter':
            return
        data = evtInfo['data']
        if not data:
            return
        win = kline.KLineWindow()
        win.showSelTip = True
        win.addDefaultIndicator(kline.KLineWindow.INDICATOR_KLINE | kline.KLineWindow.INDICATOR_AMOUNT | kline.KLineWindow.INDICATOR_RATE)
        dw = win32api.GetSystemMetrics (win32con.SM_CXFULLSCREEN)
        dh = win32api.GetSystemMetrics (win32con.SM_CYFULLSCREEN)
        W, H = 1000, 550
        x = (dw - W) // 2
        y = (dh - H) // 2
        win.createWindow(self.hwnd, (x, y, W, H), win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION)
        model = kline.KLineModel_Ths(data['code'])
        model.loadDataFile()
        win.setModel(model)
        win.makeVisible(-1)

    def loadAllData(self):
        if self.tckData:
            return
        kplQr = orm.KPL_ZT.select().dicts()
        thsQr = orm.THS_ZT.select().dicts()
        clsQr = orm.CLS_ZT.select().dicts()
        
        kpl = {}
        ths = []
        cls = []
        rs = []
        for d in kplQr:
            k = d['day'] + ':' + d['code']
            kpl[k] = d
            d['kpl_ztReason'] = d['ztReason']
            rs.append(d)
        for d in thsQr:
            k = d['day'] + ':' + d['code']
            obj = kpl.get(k, None)
            if obj:
                obj['ths_status'] = d['status']
                obj['ths_ztReason'] = d['ztReason']
            else:
                ths.append(d)
        for d in clsQr:
            k = d['day'] + ':' + d['code']
            obj = kpl.get(k, None)
            if obj:
                obj['cls_detail'] = d['detail']
                obj['cls_ztReason'] = d['ztReason']
            else:
                cls.append(d)
        self.tckData = rs

    def doSearch(self, search):
        self.loadAllData()
        self.tableWin.setData(self.tckData)
        self.tableWin.invalidWindow()

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            size = self.getClientSize()
            self.layout.resize(0, 0, size[0], size[1])
            self.invalidWindow()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)