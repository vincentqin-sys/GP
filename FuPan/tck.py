import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, re

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr
from THS import orm, ths_win
from Common import base_win, timeline, kline, table
import ddlr_detail

thsWin = ths_win.ThsWindow()
thsWin.init()

class TCK_Window(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, '1fr')
        self.cols = (60, 300, 150, 120, '1fr')
        self.layout = base_win.GridLayout(rows, self.cols, (5, 10))
        self.tableWin = table.EditTableWindow()
        self.editorWin = base_win.Editor()
        self.editorWin.placeHolder = ' or条件: |分隔; and条件: 空格分隔'
        self.editorWin.enableListeners['DbClick'] = True
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.autoSyncCheckBox = base_win.CheckBox({'title': '自动同步显示'})
        self.tckData = None
        self.tckSearchData = None
        
        self.inputTips = []
        
        base_win.ThreadPool.addTask('TCK', self.runTask)

    def runTask(self):
        self.loadAllData()
        if not self.tableWin.hwnd:
            return
        self.onQuery(self.editorWin.text)

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        def formateMoney(colName, val, rowData):
            return f'{int(val)}'
        def sortHot(colName, val, rowData, allDatas, asc):
            if val == None:
                return 1000
            return val
        headers = [ {'title': '', 'width': 30, 'name': '#idx','textAlign': win32con.DT_SINGLELINE | win32con.DT_CENTER | win32con.DT_VCENTER },
                   {'title': '日期', 'width': 70, 'name': 'day', 'sortable':True , 'fontSize' : 12},
                   {'title': '名称', 'width': 55, 'name': 'name', 'sortable':True , 'fontSize' : 12},
                   #{'title': '代码', 'width': 50, 'name': 'code', 'sortable':True , 'fontSize' : 12},
                   {'title': '热度', 'width': 40, 'name': 'zhHotOrder', 'sortable':True , 'fontSize' : 12, 'sorter': sortHot},
                   {'title': '开盘啦', 'width': 100, 'name': 'kpl_ztReason', 'sortable':True , 'fontSize' : 12},
                   {'title': '同花顺', 'width': 60, 'name': 'ths_status', 'sortable':True , 'fontSize' : 12},
                   {'title': '同花顺', 'width': 150, 'name': 'ths_ztReason', 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'sortable':True},
                   {'title': '同花顺备注', 'width': 120, 'name': 'mark_1', 'fontSize' : 12 , 'editable':True, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'sortable':True },
                   {'title': '财联社', 'width': 120, 'name': 'cls_ztReason', 'fontSize' : 12 ,'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'sortable':True },
                   {'title': '财联社详细', 'width': 0, 'name': 'cls_detail', 'stretch': 1 , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   ]
        self.checkBox.createWindow(self.hwnd, (0, 0, 1, 1))
        self.autoSyncCheckBox.createWindow(self.hwnd, (0, 0, 1, 1))
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
        self.layout.setContent(0, 3, self.autoSyncCheckBox)
        self.layout.setContent(1, 0, self.tableWin, {'horExpand': -1})
        def onPressEnter(evt, args):
            q = evt.text.strip()
            self.onQuery(q)
            if q and (q not in self.inputTips):
                self.inputTips.append(q)
        self.editorWin.addNamedListener('PressEnter', onPressEnter, None)
        self.editorWin.addNamedListener('DbClick', self.onDbClickEditor, None)
        self.tableWin.addListener(self.onDbClick, None)
        self.tableWin.addListener(self.onEditCell, None)
        sm = ths_win.ThsShareMemory.instance()
        sm.open()
        sm.addListener('ListenSync_TCK', self.onAutoSync)

    def onDbClickEditor(self, evt, args):
        if not self.inputTips:
            return
        model = []
        for s in self.inputTips:
            model.append({'title': s})
        def onSelMenu(evt, args):
            self.editorWin.setText(evt.item['title'])
            self.editorWin.invalidWindow()
            self.onQuery(self.editorWin.getText())
        menu = base_win.PopupMenuHelper.create(self.editorWin.hwnd, model)
        menu.addNamedListener('Select', onSelMenu)
        menu.show()

    def onEditCell(self, evt, args):
        if evt.name != 'CellChanged':
            return
        colName = evt.header['name']
        val = evt.data.get(colName, '')
        _id = evt.data['id']
        qr = orm.THS_ZT.update({colName : val}).where(orm.THS_ZT.id == _id)
        qr.execute()

    def onAutoSync(self, code, day):
        checked = self.autoSyncCheckBox.isChecked()
        if not checked:
            return
        code = f'{code :06d}'
        txt = self.editorWin.text
        if txt == code:
            return
        self.editorWin.setText(code)
        self.editorWin.invalidWindow()
        self.onQuery(self.editorWin.text)


    def onRefresh(self, evt, args):
        if evt.name == 'Click':
            self.tckData = None
            self.onQuery(self.editorWin.text)

    def onQuery(self, queryText):
        self.tableWin.setData(None)
        self.tableWin.invalidWindow()
        self.loadAllData()
        self.doSearch(queryText)
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
        

    def onDbClick(self, evt, args):
        if evt.name != 'RowEnter' and evt.name != 'DbClick':
            return
        data = evt.data
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

    def openKlineMinutes(self, evt, parent):
        if evt.name != 'DbClick':
            return
        win = ddlr_detail.DDLR_MinuteMgrWindow()
        rc = win32gui.GetWindowRect(parent.hwnd)
        win.createWindow(parent.hwnd, rc, win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION)
        day = evt.data.day
        win.updateCodeDay(evt.code, day)

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
            d['kpl_ztReason'] = d['ztReason'].upper()
            ztNum = d.get('ztNum', 0)
            if type(ztNum) == str:
                print(d)
                ztNum = 0
            d['kpl_ztReason'] += f"({d['ztNum']})"
            d['zhHotOrder'] = hots.get(k, None)
            rs.append(d)

        kplLastDay = rs[0]['day']
        for d in thsQr:
            k = d['day'] + ':' + d['code']
            obj = kpl.get(k, None)
            if obj:
                obj['ths_status'] = d['status']
                obj['ths_ztReason'] = d['ztReason'].upper()
                obj['mark_1'] = d['mark_1']
                obj['mark_2'] = d['mark_2']
            else:
                #ths.append(d)
                if kplLastDay < d['day']:
                    d['ths_status'] = d['status']
                    d['ths_ztReason'] = d['ztReason'].upper()
                    d['zhHotOrder'] = hots.get(k, None)
                    del d['status']
                    del d['ztReason']
                    rs.insert(0, d)
                    kpl[k] = d

        for d in clsQr:
            k = d['day'] + ':' + d['code']
            obj = kpl.get(k, None)
            if obj:
                detail = d['detail'].upper()
                detail = detail.replace('\r\n', ' | ')
                detail = detail.replace('\n', ' | ')
                obj['cls_detail'] = detail
                obj['cls_ztReason'] = d['ztReason'].upper()
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
        search = search.strip().upper()
        if '|' in search:
            qs = search.split('|')
            cond = 'OR'
        else:
            qs = search.split(' ')
            cond = 'AND'
        qrs = []
        for q in qs:
            q = q.strip()
            if q and (q not in qrs):
                qrs.append(q)

        def match(data, qrs, cond):
            for q in qrs:
                fd = False
                for k in data:
                    if k != 'id' and isinstance(data[k], str) and (q in data[k]):
                        fd = True
                        break
                if cond == 'AND' and not fd:
                    return False
                if cond == 'OR' and fd:
                    return True
            if cond == 'AND':
                return True
            return False

        #keys = ('day', 'code', 'name', 'kpl_ztReason', 'ths_ztReason', 'cls_ztReason', 'cls_detail')
        rs = []
        for d in self.tckData:
            if match(d, qrs, cond):
                rs.append(d)
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