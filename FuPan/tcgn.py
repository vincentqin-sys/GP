import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, re

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr
from THS import orm, ths_win
from Common import base_win, timeline, kline, sheet

thsWin = ths_win.ThsWindow()
thsWin.init()

class TCGN_Window(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, '1fr')
        self.cols = (250, 150, 80, 80, '1fr')
        self.layout = base_win.GridLayout(rows, self.cols, (5, 10))
        self.tableWin = base_win.TableWindow()
        self.sheetWin = sheet.SheetWindow()
        self.editorWin = base_win.Editor()
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.tckData = []
        self.tckSearchData = None
        #base_win.ThreadPool.addTask()
        self.curData = None

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        def formateMoney(colName, val, rowData):
            return f'{int(val)}'
        def sortPM(colName, val, rowData, allDatas, asc):
            return val
        headers = [ {'title': '', 'width': 30, 'name': '#idx' },
                   {'title': '题材概念', 'width': 0, 'stretch': 1, 'name': 'tcgn', 'sortable':True },
                   #{'title': '财联社详细', 'width': 0, 'name': 'cls_detail', 'stretch': 1 , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   ]
        self.checkBox.createWindow(self.hwnd, (0, 0, 1, 1))
        self.editorWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.sheetWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.rowHeight = 40
        self.tableWin.headers = headers
        newBtn = base_win.Button({'title': 'New'})
        newBtn.createWindow(self.hwnd, (0, 0, 1, 1))

        self.layout.setContent(0, 0, self.editorWin)
        self.layout.setContent(0, 1, self.checkBox)
        self.layout.setContent(0, 2, newBtn)

        self.layout.setContent(1, 0, self.tableWin)
        self.layout.setContent(1, 1, self.sheetWin, {'horExpand': -1})
        self.editorWin.addListener(self.onEditEnd, None)
        self.tableWin.addListener(self.onDbClick, None)
        self.sheetWin.addListener(self.onSheetSave, None)
        newBtn.addListener(self.onNew, None)

        self.loadAllData()
        self.tableWin.setData(self.tckData)

    def onNew(self, evtName, evt, args):
        if evtName != 'Click':
            return
        self.curData = None
        self.sheetWin.model.clearAll()
        self.sheetWin.model.setCellText(0, 0, '[input title]')
        self.sheetWin.invalidWindow()
        self.tableWin.invalidWindow()

    def onSheetSave(self, evtName, evt, args):
        if evtName != 'Save':
            return
        model : sheet.SheetModel = evt
        cell = model.getCell(0, 0)
        tcgn = ''
        if cell:
            tcgn = cell.getText()
        if not tcgn or not tcgn.strip():
            win32gui.MessageBox(self.hwnd, '需要在单元格A1输入题材概念标题', 'Error', win32con.MB_OK)
            return
        tcgn = tcgn.strip()
        info = model.serialize()
        if self.curData:
            self.curData['tcgn'] = tcgn
            self.curData['info'] = info
            qr = orm.TCK_TCGN.update({'tcgn': tcgn, 'info': info}).where(orm.TCK_TCGN.id == self.curData['id'])
            qr.execute()
        else:
            obj = orm.TCK_TCGN.create(tcgn = tcgn, info = info)
            self.curData = obj.__data__
            self.tckData.append(self.curData)
        self.tableWin.invalidWindow()

    def onEditEnd(self, evtName, evtInfo, args):
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
        
    def onDbClick(self, evtName, evtInfo, args):
        if evtName != 'RowEnter' and evtName != 'DbClick':
            return
        data = evtInfo['data']
        if not data:
            return
        self.curData = data
        self.sheetWin.model.unserialize(data['info'])
        self.sheetWin.invalidWindow()
        
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

    def loadAllData(self):
        qr = orm.TCK_TCGN.select().dicts()
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