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
        self.checkBox_THS = None
        self.tableWin = None
        self.kindCombox = None
        self.klineWin = None
        self.fsWin = None

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.checkBox_THS = base_win.CheckBox({'title': '在同花顺中打开'})
        self.checkBox_THS.createWindow(self.hwnd, (0, 0, 150, 30))
        flowLayout = base_win.FlowLayout()
        flowLayout.addContent(self.checkBox_THS, {'margins': (10, 0, 10, 0)})
        self.kindCombox = base_win.ComboBox()
        self.kindCombox.setPopupTip([{'title': '默认', 'kind': 'def'}, {'title': '涨停观察股', 'kind': 'zt'}])
        self.kindCombox.createWindow(self.hwnd, (0, 0, 150, 30))
        flowLayout.addContent(self.kindCombox)

        def formateDde(colName, val, rowData):
            return f'{val :.2f}'

        headers = [
                   {'title': '', 'width': 30, 'name': '#idx' },
                   #{'title': 'M', 'width': 30, 'name': 'markColor', 'sortable':True , 'render': mark_utils.markColorBoxRender, 'sorter': mark_utils.sortMarkColor },
                   {'title': '代码', 'width': 80, 'name': 'code', 'sortable':True},
                   {'title': '名称', 'width': 80, 'name': 'name', 'sortable':True, 'render': mark_utils.markColorTextRender },
                   {'title': '市值', 'width': 60, 'name': 'zsz', 'sortable':True},
                   {'title': '板块', 'width': 0, 'stretch': 1, 'name': 'bk', 'sortable':True},
                   #{'title': '分时', 'width': 300, 'name': 'code', 'render': cache.renderTimeline},
                   {'title': '加入日期', 'width': 100, 'name': 'day', 'sortable':False , 'textAlign': win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE}
                   ]
        self.tableWin = win = base_win.TableWindow()
        win.rowHeight = 30
        win.createWindow(self.hwnd, (0, 0, 1, 1))
        win.headers = headers
        win.addListener(self.onDbClick)
        win.addNamedListener('ContextMenu', self.onContextMenu)
        win.addNamedListener('SelectRow', self.onSelectRow)
        self.kindCombox.addNamedListener('PressEnter', self.onSelectKind)

        self.klineWin = kline_utils.createKLineWindow(self.hwnd, (0, 0, 1, 1), win32con.WS_VISIBLE | win32con.WS_CHILD)
        # fs window
        self.fsWin = timeline.SimpleTimelineWindow()
        self.fsWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.fsWin.volHeight = 50

        rows = (30, 250, '1fr')
        cols = (600, '1fr')
        self.layout = base_win.GridLayout(rows, cols, (5, 10))
        self.layout.setContent(0, 0, flowLayout)
        self.layout.setContent(1, 0, win, {'verExpand': -1})
        self.layout.setContent(0, 1, self.fsWin, {'verExpand': 1})
        self.layout.setContent(2, 1, self.klineWin)

    def onShow(self):
        idx = self.kindCombox.selIdx
        if idx < 0:
            self.kindCombox.setSelectItem(0)
        else:
            item = self.kindCombox.popupTipModel[idx]
            self.initMySelect(item['kind'])

    def onSelectRow(self, evt, args):
        if not evt.data:
            return
        code = evt.data['code']
        self.fsWin.load(code)
        self.klineWin.changeCode(code)
        self.klineWin.klineWin.clearMarkDay()
        self.klineWin.klineWin.setMarkDay(evt.data['day'])

    def onSelectKind(self, evt, args):
        kind = evt.kind
        self.initMySelect(kind)

    def initMySelect(self, kind):
        rs = []
        q = tck_orm.MyObserve.select().where(tck_orm.MyObserve.kind == kind).dicts()
        for it in q:
            rs.append(it)
            bk = utils.get_THS_GNTC(it['code'])
            if bk:
                it['bk'] = bk['hy_2_name'] + '-' + bk['hy_3_name']
                it['ltsz'] = bk['ltsz']
                it['zsz'] = bk['zsz']
        mark_utils.mergeMarks(rs, 'observe-' + kind, False)
        self.tableWin.setData(rs)
        self.tableWin.setSortHeader(self.tableWin.getHeaderByName('bk'), 'ASC')
        self.tableWin.invalidWindow()

    def onContextMenu(self, evt, args):
        tableWin = evt.src
        row = tableWin.selRow
        kind = self.kindCombox.getSelectItem()['kind']
        rowData = tableWin.getData()[row] if row >= 0 else None
        model = mark_utils.getMarkModel(row >= 0)
        model.append({'title': 'LINE'})
        model.append({'title': '删除', 'name': 'del', 'enable': rowData is not None})
        menu = base_win.PopupMenu.create(self.hwnd, model)
        def onMenuItem(evt, rd):
            if evt.item['name'] == 'del':
                tck_orm.MyObserve.delete().where(tck_orm.MyObserve.code == rowData['code'], tck_orm.MyObserve.kind == kind).execute()
                dts : list = tableWin.getData()
                dts.pop(row)
            else:
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

if __name__ == '__main__':
    fp = MyWindow()
    fp.createWindow(None, (0, 0, 1500, 700), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    w, h = fp.getClientSize()
    #fp.layout.resize(0, 0, w, h)
    win32gui.ShowWindow(fp.hwnd, win32con.SW_MAXIMIZE)
    win32gui.PumpMessages()