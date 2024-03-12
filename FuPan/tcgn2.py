import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, re

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr
from THS import orm, ths_win
from Common import base_win, timeline, kline, sheet, dialog, table
import ddlr_detail

thsWin = ths_win.ThsWindow()
thsWin.init()

class TCGN_Window(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, '1fr')
        self.cols = (250, 150, 60, 60, 60, 60, 60, 60, '1fr')
        self.layout = base_win.GridLayout(rows, self.cols, (5, 10))
        self.tableWin = base_win.TableWindow()
        self.tableCntWin = table.ExTableWindow()
        self.editorWin = base_win.Editor()
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.tckData = []
        self.tckSearchData = None
        #base_win.ThreadPool.addTask()
        self.curTcgn = None

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        def formateMoney(colName, val, rowData):
            return f'{int(val)}'
        def sortPM(colName, val, rowData, allDatas, asc):
            return val
        headers = [ {'title': '', 'width': 30, 'name': '#idx' },
                   {'title': '一级题材概念', 'width': 0, 'stretch': 1, 'name': 'tcgn', 'sortable':True },
                   #{'title': '财联社详细', 'width': 0, 'name': 'cls_detail', 'stretch': 1 , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   ]
        headers2 = [
            {'title': '', 'width': 30, 'name': '#idx' },
            {'title': '二级题材概念', 'width': 200, 'name': 'tcgn_sub', 'editable': True},
            {'title': '股票代码', 'width': 100, 'name': 'code', 'editable': True},
            {'title': '股票名称', 'width': 150, 'name': 'name', 'editable': True},
            {'title': '详情', 'stretch': 1, 'name': 'info', 'editable': True},
        ]
        self.checkBox.createWindow(self.hwnd, (0, 0, 1, 1))
        self.editorWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableCntWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.rowHeight = 30
        self.tableWin.headers = headers
        self.tableCntWin.rowHeight = 30
        self.tableCntWin.headers = headers2
        addBtn = base_win.Button({'title': 'Add'})
        addBtn.createWindow(self.hwnd, (0, 0, 1, 1))
        insertBtn = base_win.Button({'title': 'Insert'})
        insertBtn.createWindow(self.hwnd, (0, 0, 1, 1))
        newBtn = base_win.Button({'title': 'New'})
        newBtn.createWindow(self.hwnd, (0, 0, 1, 1))
        delBtn = base_win.Button({'title': 'Del'})
        delBtn.createWindow(self.hwnd, (0, 0, 1, 1))
        openBtn = base_win.Button({'title': 'Open'})
        openBtn.createWindow(self.hwnd, (0, 0, 1, 1))

        self.layout.setContent(0, 0, self.editorWin)
        self.layout.setContent(0, 1, self.checkBox)
        self.layout.setContent(0, 2, addBtn)
        self.layout.setContent(0, 3, insertBtn)
        self.layout.setContent(0, 4, delBtn)
        self.layout.setContent(0, 6, newBtn)
        self.layout.setContent(0, 7, openBtn)

        self.layout.setContent(1, 0, self.tableWin)
        self.layout.setContent(1, 1, self.tableCntWin, {'horExpand': -1})
        self.editorWin.addListener(self.onQuery)
        self.tableWin.addListener(self.onSelect)
        self.tableCntWin.addListener(self.onCellChanged)
        addBtn.addListener(self.onAddInsert, 'Add')
        insertBtn.addListener(self.onAddInsert, 'Insert')
        newBtn.addListener(self.onNew, 'New')
        delBtn.addListener(self.onDel, 'Del')
        openBtn.addListener(self.onOpen, 'Open')

        self.loadAllData()
        self.tableWin.setData(self.tckData)

    def onCellChanged(self, evtName, evt, args):
        if evtName != 'CellChanged':
            return
        name = evt['header']['name']
        cellVal = evt['data'][name].strip()
        qr = orm.TCK_TCGN.update({name : cellVal}).where(orm.TCK_TCGN.id == evt['data']['id'])
        qr.execute()
        if name != 'name':
            return
        code = self.getCodeByName(cellVal)
        if not code or evt['data']['code'] == code:
            return
        qr = orm.TCK_TCGN.update({'code' : code}).where(orm.TCK_TCGN.id == evt['data']['id'])
        qr.execute()
        evt['data']['code'] = code

    def onDel(self, evtName, evt, args):
        if evtName != 'Click':
            return
        row = self.tableCntWin.selRow
        if row < 0:
            return
        model = self.tableCntWin.getData()
        data = model[row]
        orm.TCK_TCGN.delete_by_id(data['id'])
        model.pop(row)
        self.tableCntWin.invalidWindow()

    def onOpen(self, evtName, evt, args):
        if evtName != 'Click':
            return
        row = self.tableCntWin.selRow
        if row < 0:
            return
        model = self.tableCntWin.getData()
        data = model[row]
        code = data['code']
        if not self.isCode(code):
            return
        if self.checkBox.isChecked():
            self.openInThsWindow(data)
        else:
            self.openInCurWindow(data)

    def onNew(self, evtName, evt, args):
        if evtName != 'Click':
            return
        dlg = dialog.InputDialog()
        dlg.createWindow(self.hwnd, (0, 0, 300, 70), title='一级题材概念')
        dlg.showCenter()
        dlg.addListener(self.onDialogInputEnd)

    def onDialogInputEnd(self, evtName, evt, args):
        if evtName != 'InputEnd':
            return
        self.curTcgn = evt['text'] or ''
        self.curTcgn = self.curTcgn.strip()
        if not self.curTcgn:
            return
        self.tableCntWin.setData([])
        self.tableCntWin.invalidWindow()
        dt = self.tableWin.getData()
        if dt == None:
            dt = []
            self.tableWin.setData(dt)
        dt.append({'tcgn': self.curTcgn})
        self.tableWin.invalidWindow()
        self.tableWin.setSelRow(len(dt) - 1)
        self.tableWin.showRow(len(dt) - 1)

    def onAddInsert(self, evtName, evt, args):
        if evtName != 'Click':
            return
        if not self.curTcgn:
            return
        cur = {'tcgn' : self.curTcgn, 'tcgn_sub': '', 'code': '', 'name':'', 'info':'', 'order_': 0}
        model = self.tableCntWin.getData()
        curSelRow = self.tableCntWin.selRow
        if not model:
            cur['order_'] = 0
        elif curSelRow < 0:
            cur['order_'] = len(model)
        elif args == 'Add':
            cur['order_'] = curSelRow + 1
            cur['tcgn_sub'] = model[curSelRow]['tcgn_sub']
            qr = orm.TCK_TCGN.update({orm.TCK_TCGN.order_ : orm.TCK_TCGN.order_ + 1}).where(orm.TCK_TCGN.tcgn == self.curTcgn, orm.TCK_TCGN.order_ > curSelRow)
            qr.execute()
        elif args == 'Insert':
            cur['order_'] = curSelRow
            cur['tcgn_sub'] = model[curSelRow]['tcgn_sub']
            qr = orm.TCK_TCGN.update({orm.TCK_TCGN.order_ : orm.TCK_TCGN.order_ + 1}).where(orm.TCK_TCGN.tcgn == self.curTcgn, orm.TCK_TCGN.order_ >= curSelRow)
            qr.execute()
        if model == None:
            model = []
            self.tableCntWin.setData(model)
        model.insert(cur['order_'], cur)
        obj = orm.TCK_TCGN.create(**cur)
        cur['id'] = obj.id
        self.tableCntWin.invalidWindow()
        self.tableWin.invalidWindow()

    def isCode(self, s):
        if not s:
            return False
        s = s.strip()
        if len(s) != 6:
            return False
        for k in s:
            if k < '0' or k > '9':
                return False
        return True
    
    def getCodeByName(self, name):
        obj = orm.THS_GNTC.get_or_none(name = name)
        if not obj:
            obj = orm.THS_Newest.get_or_none(name = name)
        if not obj:
            return ''
        return obj.code

    def onQuery(self, evtName, evtInfo, args):
        if evtName != 'PressEnter':
            return
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
        
    def onSelect(self, evtName, evtInfo, args):
        if evtName != 'SelectRow':
            return
        data = evtInfo['data']
        if not data:
            return
        self.curTcgn = data['tcgn']
        qr = orm.TCK_TCGN.select().where(orm.TCK_TCGN.tcgn == self.curTcgn).order_by(orm.TCK_TCGN.order_.asc()).dicts()
        datas = [d for d in qr]
        self.tableCntWin.setData(datas)
        self.tableCntWin.invalidWindow()
        
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
        qr = orm.TCK_TCGN.select(orm.TCK_TCGN.tcgn).distinct().dicts()
        rs = []
        for d in qr:
            rs.append(d)
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
        keys = ('tcgn', 'info')
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