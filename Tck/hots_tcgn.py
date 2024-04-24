import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, re

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr
from THS import orm as ths_orm, ths_win, hot_utils
from Common import base_win, timeline, kline, table
import ddlr_detail, orm, kline_utils

class Hots_Window(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, '1fr')
        self.cols = (60, 300, 80, 40, 150, 120, 120, '1fr')
        self.layout = base_win.GridLayout(rows, self.cols, (5, 10))
        self.tableWin = table.EditTableWindow()
        self.tableWin.enableListeners['ContextMenu'] = True
        self.editorWin = base_win.Editor()
        self.editorWin.placeHolder = ' or条件: |分隔; and条件: 空格分隔'
        self.editorWin.enableListeners['DbClick'] = True
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.autoSyncCheckBox = base_win.CheckBox({'title': '自动同步显示'})
        self.datePicker = base_win.DatePicker()
        self.hotsData = None
        self.searchData = None
        self.searchText = ''
        
        self.inputTips = []
        
        base_win.ThreadPool.addTask('Hots', self.runTask)

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
        def render(win, hdc, row, col, colName, value, rowData, rect):
            model = self.tableWin.getData()
            rowData = model[row]
            color = self.tableWin.css['textColor']
            if rowData.get('ths_mark_3', 0) == 1:
                color = 0x0000dd
            self.drawer.drawText(hdc, value, rect, color, align = win32con.DT_VCENTER | win32con.DT_SINGLELINE | win32con.DT_LEFT)
        headers = [ {'title': '', 'width': 40, 'name': '#idx','textAlign': win32con.DT_SINGLELINE | win32con.DT_CENTER | win32con.DT_VCENTER },
                   {'title': '日期', 'width': 100, 'name': 'day', 'sortable':True , 'fontSize' : 14},
                   {'title': '名称', 'width': 80, 'name': 'name', 'sortable':True , 'fontSize' : 14, 'render__': render},
                   {'title': '代码', 'width': 80, 'name': 'code', 'sortable':True , 'fontSize' : 14},
                   {'title': '热度', 'width': 80, 'name': 'zhHotOrder', 'sortable':True , 'fontSize' : 14, 'sorter': sortHot},
                   {'title': '板块', 'width': 200, 'name': 'hy', 'sortable':True , 'fontSize' : 12,  'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   {'title': '', 'width': 20, 'name': '__mm'},
                   {'title': '题材概念', 'width': 0, 'name': 'gn', 'stretch': 1 , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   ]
        self.checkBox.createWindow(self.hwnd, (0, 0, 1, 1))
        self.autoSyncCheckBox.createWindow(self.hwnd, (0, 0, 1, 1))
        self.editorWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.rowHeight = 40
        self.tableWin.headers = headers
        btn = base_win.Button({'title': '刷新'})
        btn.createWindow(self.hwnd, (0, 0, 1, 1))
        self.datePicker.createWindow(self.hwnd, (0, 0, 1, 1))
        btn.addListener(self.onRefresh)
        self.layout.setContent(0, 0, btn)
        self.layout.setContent(0, 1, self.editorWin)
        self.layout.setContent(0, 4, self.checkBox)
        self.layout.setContent(0, 5, self.autoSyncCheckBox)
        self.layout.setContent(0, 6, self.datePicker)

        self.layout.setContent(1, 0, self.tableWin, {'horExpand': -1})
        def onPressEnter(evt, args):
            q = evt.text.strip()
            self.onQuery(q)
            if q and (q not in self.inputTips):
                self.inputTips.append(q)
        self.editorWin.addNamedListener('PressEnter', onPressEnter, None)
        self.editorWin.addNamedListener('DbClick', self.onDbClickEditor, None)
        self.tableWin.addListener(self.onDbClick, None)
        sm = ths_win.ThsShareMemory.instance()
        sm.open()
        sm.addListener('ListenSync_Hots', self.onAutoSync)

    def onDbClickEditor(self, evt, args):
        model = []
        for s in self.inputTips:
            model.append({'title': s})
        model.append({'title': 'LINE'})
        for s in orm.TCK_CiTiao.select():
            model.append({'title': s.name})
        if len(model) == 1:
            return

        def onSelMenu(evt, args):
            self.editorWin.setText(evt.item['title'])
            self.editorWin.invalidWindow()
            self.onQuery(self.editorWin.getText())
        menu = base_win.PopupMenuHelper.create(self.editorWin.hwnd, model)
        menu.addNamedListener('Select', onSelMenu)
        menu.show()

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
            self.hotsData = None
            self.onQuery(self.editorWin.text)

    def onQuery(self, queryText):
        self.tableWin.setData(None)
        self.tableWin.invalidWindow()
        self.loadAllData()
        self.doSearch(queryText)
        self.tableWin.setData(self.searchData)
        self.tableWin.invalidWindow()

    def onDbClick(self, evt, args):
        if evt.name != 'RowEnter' and evt.name != 'DbClick':
            return
        data = evt.data
        if not data:
            return
        if self.checkBox.isChecked():
            kline_utils.openInThsWindow(data)
        else:
            kline_utils.openInCurWindow(data)
        
    def loadAllData(self):
        if self.hotsData != None:
            return
        selDay = self.datePicker.getSelDay()
        if not selDay:
            selDay = hot_utils.getLastTradeDay()
        if type(selDay) == str:
            selDay = int(selDay.replace('-', ''))
        hotZH = ths_orm.THS_HotZH.select().where(ths_orm.THS_HotZH.day == selDay).dicts()
        rs = []
        rsMaps = {}
        for d in hotZH:
            day = d['day']
            day = f"{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}"
            code = f"{d['code'] :06d}"
            mm = {'code': code, 'day': day, 'zhHotOrder': d['zhHotOrder']}
            rs.append(mm)
            rsMaps[code] = mm
        self.hotsData = rs
        TRUNCK = 50
        for i in range((len(rs) + TRUNCK - 1) // TRUNCK):
            prs = rs[i * TRUNCK : (i + 1) * TRUNCK ]
            cs = [d['code'] for d in prs]
            qr = ths_orm.THS_GNTC.select().where(ths_orm.THS_GNTC.code.in_(cs)).dicts()
            for m in qr:
                item : dict = rsMaps[m['code']]
                item.update(m)
        self.hotsData = rs

    def doSearch(self, search : str):
        self.searchText = search
        if not self.hotsData:
            self.searchData = None
            return
        if not search or not search.strip():
            self.searchData = self.hotsData
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
                    if ('_id' not in k) and isinstance(data[k], str) and (q in data[k]):
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
        for d in self.hotsData:
            if match(d, qrs, cond):
                rs.append(d)
        self.searchData = rs

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