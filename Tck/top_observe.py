import win32gui, win32con , win32api, win32ui, pyautogui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from db import ths_orm, tck_orm
from Tdx import datafile
from Download import henxin, ths_ddlr, ths_iwencai
from THS import ths_win
from Common import base_win
from Tck import kline, kline_utils, mark_utils, timeline, top_diary, cache, utils

class MyWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, 20, '1fr')
        self.cols = ('1fr', '1fr')
        self.layout = base_win.GridLayout(rows, self.cols, (5, 10))
        self.listWins = []
        self.labels = []
        self.checkBox_THS = None

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.checkBox_THS = base_win.CheckBox({'title': '在同花顺中打开'})
        self.checkBox_THS.createWindow(self.hwnd, (0, 0, 150, 30))
        absLayout = base_win.AbsLayout()
        absLayout.setContent(230, 0, self.checkBox_THS)
        self.layout.setContent(0, 0, absLayout)

        def formateDde(colName, val, rowData):
            return f'{val :.2f}'
        
        headers = [
                   {'title': '', 'width': 30, 'name': '#idx' },
                   {'title': 'M', 'width': 30, 'name': 'markColor', 'sortable':True , 'render': mark_utils.markColorBoxRender, 'sorter': mark_utils.sortMarkColor },
                   {'title': '代码', 'width': 80, 'name': 'code', 'sortable':True},
                   {'title': '名称', 'width': 80, 'name': 'name', 'sortable':True, 'render': mark_utils.markColorTextRender },
                   {'title': '板块', 'width': 0, 'stretch': 1, 'name': 'bk', 'sortable':True},
                   {'title': '分时', 'width': 300, 'name': 'code', 'render': cache.renderTimeline},
                   {'title': '加入日期', 'width': 100, 'name': 'day', 'sortable':False , 'textAlign': win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE}
                   ]
        kinds = ['def', 'zt']
        tips = ['自选股', '涨停观察股']
        for i in range(len(self.layout.templateColumns)):
            win = base_win.TableWindow()
            win.rowHeight = 50
            win.createWindow(self.hwnd, (0, 0, 1, 1))
            win.headers = headers
            self.layout.setContent(2, i, win)
            self.listWins.append(win)
            lw = base_win.Label()
            lw.createWindow(self.hwnd, (0, 0, 1, 1))
            self.labels.append(lw)
            self.layout.setContent(1, i, lw)
            win.addListener(self.onDbClick, i)
            win.addNamedListener('ContextMenu', self.onContextMenu, kinds[i])
            self.initMySelect(win, kinds[i])
            lw.setText(tips[i])

    def onShow(self):
        self.initMySelect(self.listWins[0], 'def')
        self.initMySelect(self.listWins[1], 'zt')

    def initMySelect(self, tab, kind):
        rs = []
        q = tck_orm.MyObserve.select().where(tck_orm.MyObserve.kind == kind).dicts()
        for it in q:
            rs.append(it)
            bk = utils.get_THS_GNTC(it['code'])
            it['bk'] = bk['hy_2_name'] + '-' + bk['hy_3_name'] if bk else ''
        mark_utils.mergeMarks(rs, 'observe-' + kind, False)
        tab.setData(rs)
        tab.invalidWindow()

    def onContextMenu(self, evt, kind):
        tableWin = evt.src
        row = tableWin.selRow
        rowData = tableWin.getData()[row] if row >= 0 else None
        model = mark_utils.getMarkModel(row >= 0)
        menu = base_win.PopupMenu.create(self.hwnd, model)
        def onMenuItem(evt, rd):
            mark_utils.saveOneMarkColor({'kind': 'observe-' + kind, 'code': rowData['code']}, evt.item['markColor'], endDay = rowData['day'])
            rd['markColor'] = evt.item['markColor']
            tableWin.invalidWindow()
        menu.addNamedListener('Select', onMenuItem, rowData)
        x, y = win32gui.GetCursorPos()
        menu.show(x, y)
    
    def onDbClick(self, evt, idx):
        if evt.name != 'DbClick' and evt.name != 'RowEnter':
            return
        data = evt.data
        if not data:
            return
        if self.checkBox_THS.isChecked():
            kline_utils.openInThsWindow(data)
        else:
            win = kline_utils.openInCurWindow_Code(self, data)
            win.setCodeList(evt.src.getData())