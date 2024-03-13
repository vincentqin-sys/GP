import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, re

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr
from THS import orm, ths_win
from Common import base_win, timeline, kline
import ddlr_detail

thsWin = ths_win.ThsWindow()
thsWin.init()

class TCK_Window(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, '1fr')
        self.cols = (60, 300, 150, '1fr')
        self.layout = base_win.GridLayout(rows, self.cols, (5, 10))
        self.tableWin = base_win.TableWindow()
        self.editorWin = base_win.Editor()
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.tckData = None
        self.tckSearchData = None
        
        base_win.ThreadPool.addTask('TCK', self.runTask)

    def runTask(self):
        self.loadAllData()
        if not self.tableWin.hwnd:
            return
        self.onEditEnd('PressEnter', {'text': self.editorWin.text}, None)

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        def formateMoney(colName, val, rowData):
            return f'{int(val)}'
        def sortPM(colName, val, rowData, allDatas, asc):
            return val
        headers = [ {'title': '', 'width': 30, 'name': '#idx' },
                   {'title': '日期', 'width': 80, 'name': 'day', 'sortable':True },
                   {'title': '名称', 'width': 70, 'name': 'name', 'sortable':True },
                   {'title': '代码', 'width': 60, 'name': 'code', 'sortable':True },
                   {'title': '热度', 'width': 70, 'name': 'zhHotOrder', 'sortable':True },
                   {'title': '开盘啦', 'width': 120, 'name': 'kpl_ztReason', 'sortable':True },
                   {'title': '同花顺', 'width': 80, 'name': 'ths_status', 'sortable':True },
                   {'title': '同花顺', 'width': 200, 'name': 'ths_ztReason',  'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'sortable':True},
                   {'title': '财联社', 'width': 150, 'name': 'cls_ztReason', 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'sortable':True },
                   {'title': '财联社详细', 'width': 0, 'name': 'cls_detail', 'stretch': 1 , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   ]
        self.checkBox.createWindow(self.hwnd, (0, 0, 1, 1))
        self.editorWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.rowHeight = 40
        self.tableWin.headers = headers
        btn = base_win.Button({'title': '刷新'})
        btn.createWindow(self.hwnd, (0, 0, 1, 1))
        btn.addListener(self.onRefresh)
        self.layout.setContent(0, 0, btn)
        self.layout.setContent(0, 1, self.editorWin)
        self.layout.setContent(0, 2, self.checkBox)
        self.layout.setContent(1, 0, self.tableWin, {'horExpand': -1})
        self.editorWin.addListener(self.onEditEnd, None)
        self.tableWin.addListener(self.onDbClick, None)

    def onRefresh(self, evtName, evtInfo, args):
        if evtName == 'Click':
            self.tckData = None
            self.onEditEnd('PressEnter', {'text': self.editorWin.text}, None)

    def onEditEnd(self, evtName, evtInfo, args):
        if evtName != 'PressEnter':
            return
        self.tableWin.setData(None)
        self.tableWin.invalidWindow()
        self.loadAllData()
        self.doSearch(evtInfo['text'])
        self.tableWin.setData(self.tckSearchData)
        self.tableWin.invalidWindow()
    
    def openInThsWindow(self, data):
        if not thsWin.topHwnd or not win32gui.IsWindow(thsWin.topHwnd):
            thsWin.topHwnd = None
            thsWin.init()
        if not thsWin.topHwnd:
            return
        win32gui.SetForegroundWindow(thsWin.topHwnd)
        time.sleep(0.5)
        pyautogui.typewrite(data['code'], 0.1)
        time.sleep(0.2)
        pyautogui.press('enter')
        

    def onDbClick(self, evtName, evtInfo, args):
        if evtName != 'RowEnter' and evtName != 'DbClick':
            return
        data = evtInfo['data']
        if not data:
            return
        if self.checkBox.isChecked():
            self.openInThsWindow(data)
        else:
            self.openInCurWindow(data)
        
    def openInCurWindow(self, data):
        win = kline.KLineWindow()
        win.showSelTip = True
        win.addDefaultIndicator('rate | amount')
        win.addIndicator(kline.DayIndicator(win, {}))
        win.addIndicator(kline.DdlrIndicator(win, {'height': 100}))
        win.addIndicator(kline.DdlrIndicator(win, {'height': 30}, False))
        win.addIndicator(kline.HotIndicator(win, None))
        dw = win32api.GetSystemMetrics (win32con.SM_CXFULLSCREEN)
        dh = win32api.GetSystemMetrics (win32con.SM_CYFULLSCREEN)
        W, H = 1000, 650
        x = (dw - W) // 2
        y = (dh - H) // 2
        win.createWindow(self.hwnd, (0, y, W, H), win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION)
        model = kline.KLineModel_Ths(data['code'])
        model.loadDataFile()
        win.setModel(model)
        win.setMarkDay(data['day'])
        win.makeVisible(-1)
        win.addListener(self.openKlineMinutes, win)

    def openKlineMinutes(self, evtName, evt, parent):
        if evtName != 'DbClick':
            return
        win = ddlr_detail.DDLR_MinuteMgrWindow()
        rc = win32gui.GetWindowRect(parent.hwnd)
        win.createWindow(parent.hwnd, rc, win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION)
        day = evt['data'].day
        win.updateCodeDay(evt['code'], day)

    def loadAllData(self):
        if self.tckData != None:
            return
        kplQr = orm.KPL_ZT.select().order_by(orm.KPL_ZT.day.desc(), orm.KPL_ZT.id.asc()).dicts()
        thsQr = orm.THS_ZT.select().dicts()
        clsQr = orm.CLS_ZT.select().dicts()
        hotZH = orm.THS_HotZH.select().dicts()
        
        kpl = {}
        ths = []
        cls = []
        hots = {}
        rs = []
        for d in hotZH:
            day = d['day']
            day = f"{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}"
            k = f"{day}:{d['code'] :06d}"
            hots[k] = d['zhHotOrder']
        for d in kplQr:
            k = d['day'] + ':' + d['code']
            kpl[k] = d
            d['kpl_ztReason'] = d['ztReason']
            ztNum = d.get('ztNum', 0)
            if type(ztNum) == str:
                print(d)
                ztNum = 0
            d['kpl_ztReason'] += f"({d['ztNum']})"
            d['zhHotOrder'] = hots.get(k, None)
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

    def doSearch(self, search : str):
        if not self.tckData:
            self.tckSearchData = None
            return
        if not search or not search.strip():
            self.tckSearchData = self.tckData
            return
        search = search.strip()
        ls = search.split(' ')
        st = []
        for k in ls:
            if k: st.append(k)
        keys = ('day', 'code', 'name', 'kpl_ztReason', 'ths_ztReason', 'cls_ztReason', 'cls_detail')
        def contains(v):
            for m in st:
                if m in v: return True
                return False
        rs = []
        for d in self.tckData:
            for k in keys:
                x = d.get(k, None)
                if x and type(x) == str and contains(x):
                    rs.append(d)
                    break
        self.tckSearchData = rs


    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            size = self.getClientSize()
            self.layout.resize(0, 0, size[0], size[1])
            self.invalidWindow()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)
    
if __name__ == '__main__':
    ls = 'ddd    cc    mm'.strip()
    print(ls)
    ls = ls.split('+')
    print(ls)
    pass