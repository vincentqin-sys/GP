import win32gui, win32con , win32api, win32ui, pyautogui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from db import ths_orm, tck_orm
from Tdx import datafile
from Download import henxin, ths_ddlr, ths_iwencai
from THS import ths_win
from Common import base_win
from Tck import kline, kline_utils, mark_utils, timeline, top_diary, cache

class DdeWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, 20, '1fr')
        cw = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        n = 4 if cw > 1600 else 3
        self.cols = ['1fr']
        for i in range(n - 1):
            self.cols.append(350)
        self.layout = base_win.GridLayout(rows, self.cols, (5, 10))
        self.listWins = []
        self.daysLabels =[]
        self.checkBox_THS = None
        self.datePicker = None

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.datePicker = base_win.DatePicker()
        self.datePicker.createWindow(self.hwnd, (10, 10, 150, 30))
        self.checkBox_THS = base_win.CheckBox({'title': '在同花顺中打开'})
        self.checkBox_THS.createWindow(self.hwnd, (0, 0, 150, 30))
        absLayout = base_win.AbsLayout()
        absLayout.setContent(0, 0, self.datePicker)
        absLayout.setContent(230, 0, self.checkBox_THS)
        self.layout.setContent(0, 0, absLayout)

        def formateDde(colName, val, rowData):
            return f'{val :.2f}'
        
        headers = [{'title': '', 'width': 30, 'name': '#idx' },
                   {'title': '代码', 'width': 60, 'name': 'code'},
                   {'title': '名称', 'width': 0, 'stretch': 1, 'name': 'name', 'sortable':True},
                   {'title': 'DDE净额_亿', 'width': 90, 'name': 'dde', 'sortable':True, 'formater': formateDde},
                   {'title': '排名', 'width': 70, 'name': 'dde_pm', 'sortable':False , 'textAlign': win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE}
                   ]
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
        self.datePicker.addListener(self.onSelDayChanged, None)
        # init view
        today = datetime.date.today()
        day = today.strftime('%Y%m%d')
        self.datePicker.setSelDay(day)
        self.updateDay(day)

    def onShow(self):
        self.initMySelect()

    def initMySelect(self):
        tab = self.listWins[0]
        tab.rowHeight = 50
        tab.headers = [
                   {'title': '', 'width': 30, 'name': '#idx' },
                   {'title': '代码', 'width': 80, 'name': 'code', 'sortable':True},
                   {'title': '名称', 'width': 80, 'name': 'name', 'sortable':True, 'render': mark_utils.markColorTextRender },
                   {'title': '板块', 'width': 0, 'stretch': 1, 'name': 'bk', 'sortable':True},
                   {'title': '分时', 'width': 300, 'name': 'code', 'render': cache.renderTimeline},
                   {'title': '加入日期', 'width': 100, 'name': 'day', 'sortable':False , 'textAlign': win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE}
                   ]
        rs = []
        for it in tck_orm.MySelCode.select().dicts():
            rs.append(it)
            bk = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == it['code'])
            it['bk'] = bk.hy_2_name if bk else ''
        tab.setData(rs)

    def onSelDayChanged(self, evt, args):
        if evt.name != 'Select':
            return
        # TODO: change models
        self.updateDay(evt.day)
    
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

    def updateDay(self, day):
        if type(day) == int:
            day = str(day)
        if len(day) == 8:
            day = day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
        
        rs = ths_iwencai.download_dde_money()
        skip = 0
        netDay = None
        if rs and rs[0].day <= day:
            skip = 1
            win = self.listWins[1]
            cday = rs[0].day
            self.daysLabels[1].setText(cday)
            data = [r.__data__ for r in rs]
            win.setData(data)
            win._day = cday
            win.invalidWindow()
            netDay = cday

        num = len(self.cols) - 1 - skip
        q = ths_orm.THS_DDE.select(ths_orm.THS_DDE.day).distinct().where(ths_orm.THS_DDE.day <= day).order_by(ths_orm.THS_DDE.day.desc()).limit(len(self.cols) - 1).tuples()
        deal = 0
        for i, d in enumerate(q):
            cday = d[0]
            if netDay == cday:
                continue
            if deal >= num:
                break
            self.updateDay_Table(cday, self.listWins[deal + 1 + skip])
            self.daysLabels[deal + 1 + skip].setText(cday)
            deal += 1

    def updateDay_Table(self, cday, tableWin):
        ds = ths_orm.THS_DDE.select().where(ths_orm.THS_DDE.day == cday).order_by(ths_orm.THS_DDE.dde.desc())
        datas = [d.__data__ for d in ds]
        tableWin.setData(datas)
        tableWin._day = cday
        tableWin.invalidWindow()