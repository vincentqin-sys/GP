import win32gui, win32con , win32api, win32ui, pyautogui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr
from THS import orm, ths_win
from Common import base_win, timeline, kline
from Tck import zs_fupan, kline_utils

class ZSWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, 20, '1fr')
        self.cols = ('1fr', '1fr', '1fr', '1fr')
        self.layout = base_win.GridLayout(rows, self.cols, (5, 10))
        self.listWins = []
        self.daysLabels =[]
        self.checkBox = None

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        datePicker = base_win.DatePicker()
        datePicker.createWindow(self.hwnd, (10, 10, 150, 30))
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.checkBox.createWindow(self.hwnd, (0, 0, 150, 30))
        rjBtn = base_win.Button({'title': '复盘日记'})
        rjBtn.createWindow(self.hwnd, (0, 0, 80, 30))
        absLayout = base_win.AbsLayout()
        absLayout.setContent(0, 0, datePicker)
        absLayout.setContent(230, 0, self.checkBox)
        absLayout.setContent(400, 0, rjBtn)
        self.layout.setContent(0, 0, absLayout)
        def onRjClick(evt, args):
            fpWin = zs_fupan.DailyFuPanWindow()
            p = self.hwnd
            while True:
                pp = win32gui.GetParent(p)
                if pp: p = pp
                else:break
            rc = win32gui.GetWindowRect(p)
            pw, ph = rc[2] - rc[0], rc[3] - rc[1]
            wcw = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            CW = int(wcw * 0.9)
            fpWin.createWindow(self.hwnd, (rc[0] + (pw - CW) // 2, rc[1], CW, ph), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_CAPTION, title='复盘日记') # WS_OVERLAPPEDWINDOW
            win32gui.ShowWindow(fpWin.hwnd, win32con.SW_SHOW)
            
        rjBtn.addNamedListener('Click', onRjClick)
        
        def formateRate(colName, val, rowData):
            return f'{val :.02f}%'
        def formateMoney(colName, val, rowData):
            return f'{int(val)}'
        def sortPM(colName, val, rowData, allDatas, asc):
            if val > 0:
                return val
            elif val < 0:
                return len(allDatas) + val + 100
            # == 0
            if asc:
                return 10000
            return -10000
        def render(win, hdc, row, col, colName, value, rowData, rect):
            datas = win.getData()
            color = win.css['textColor']
            if datas[row]['mark_1'] == 1:
                color = 0x0000dd
            elif datas[row]['mark_1'] == 2:
                color = 0xdd0000
            elif datas[row]['mark_1'] == 3:
                color = 0x00AA00
            align = win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE
            win.drawer.drawText(hdc, value, rect, color, align = align)

        headers = [ #{'title': '', 'width': 60, 'name': '#idx' },
                   {'title': '代码', 'width': 60, 'name': 'code'},
                   {'title': '指数名称', 'width': 0, 'stretch': 1, 'name': 'name', 'sortable':True, 'render': render },
                   {'title': '成交额', 'width': 60, 'name': 'money', 'formater': formateMoney , 'sortable':True },
                   {'title': '涨幅', 'width': 60, 'name': 'zdf', 'formater': formateRate, 'sortable':True },
                   {'title': '50亿排名', 'width': 70, 'name': 'zdf_50PM', 'sorter': sortPM, 'sortable':True },
                   {'title': '全市排名', 'width': 70, 'name': 'zdf_PM', 'sorter': sortPM, 'sortable':True }]
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
            win.enableListeners['ContextMenu'] = True
            win.addListener(self.onContextMenu, i)
        datePicker.addListener(self.onSelDayChanged, None)
        # init view
        today = datetime.date.today()
        day = today.strftime('%Y%m%d')
        self.updateDay(day)
    
    def onContextMenu(self, evt, tabIdx):
        if evt.name != 'ContextMenu':
            return
        win : base_win.TableWindow = self.listWins[tabIdx]
        wdata = win.getData()
        rowData = wdata[win.selRow] if win.selRow >= 0 else None
        code = rowData['code'] if rowData else None
        model = [{'title': '关联选中', 'name': 'GL', 'enable': win.selRow >= 0}, 
                 {'title': '标记红色重点', 'name': 'MARK', 'enable': win.selRow >= 0}, 
                 {'title': '标记蓝色观察', 'name': 'MARK_BLUE', 'enable': win.selRow >= 0}, 
                 {'title': '标记绿色负面', 'name': 'MARK_GREEN', 'enable': win.selRow >= 0}, 
                 {'title': 'LINE'},
                 {'title': '筛选标记', 'name': 'MARK_FILTER'}]
        menu = base_win.PopupMenuHelper.create(self.hwnd, model)
        menu.addListener(self.onMenuItemSelect, (tabIdx, code, rowData))
        x, y = win32gui.GetCursorPos()
        menu.show(x, y)

    def findIdx(self, win, code):
        datas = win.getData() or []
        for i, d in enumerate(datas):
            if d['code'] == code:
                return i
        return -1
    
    def onMenuItemSelect(self, evt, args):
        if evt.name != 'Select':
            return
        tabIdx, code, rowData = args
        if evt.item['name'] == "GL":
            for i, win in enumerate(self.listWins):
                if i == tabIdx:
                    continue
                idx = self.findIdx(win, code)
                win.selRow = idx
                win.showRow(idx)
                win.invalidWindow()
        elif evt.item['name'] == 'MARK':
            MARK_VAL = 1
            qr = orm.THS_ZS_ZD.update({orm.THS_ZS_ZD.mark_1 : MARK_VAL}).where(orm.THS_ZS_ZD.id == rowData['id'])
            qr.execute()
            rowData['mark_1'] = MARK_VAL
            self.listWins[tabIdx].invalidWindow()
        elif evt.item['name'] == 'MARK_BLUE':
            MARK_VAL = 2
            qr = orm.THS_ZS_ZD.update({orm.THS_ZS_ZD.mark_1 : MARK_VAL}).where(orm.THS_ZS_ZD.id == rowData['id'])
            qr.execute()
            rowData['mark_1'] = MARK_VAL
            self.listWins[tabIdx].invalidWindow()
        elif evt.item['name'] == 'MARK_GREEN':
            MARK_VAL = 3
            qr = orm.THS_ZS_ZD.update({orm.THS_ZS_ZD.mark_1 : MARK_VAL}).where(orm.THS_ZS_ZD.id == rowData['id'])
            qr.execute()
            rowData['mark_1'] = MARK_VAL
            self.listWins[tabIdx].invalidWindow()
        elif evt.item['name'] == 'MARK_FILTER':
            tabWin : base_win.TableWindow = self.listWins[tabIdx]
            day = tabWin._day
            fm = getattr(tabWin, '_filter_mark_', False)
            if not fm:
                qr = orm.THS_ZS_ZD.select().where(orm.THS_ZS_ZD.mark_1 > 0, orm.THS_ZS_ZD.day == day).dicts()
                rs = [d for d in qr]
            else:
                qr = orm.THS_ZS_ZD.select().where(orm.THS_ZS_ZD.day == day).dicts()
                rs = [d for d in qr]
            setattr(tabWin, '_filter_mark_', not fm)
            tabWin.setData(rs)
            tabWin.invalidWindow()

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
        if self.checkBox.isChecked():
            self.openInThsWindow(data)
        else:
            self.openInCurWindow(data)

    def openInThsWindow(self, data):
        kline_utils.openInThsWindow(data)
        
    def openInCurWindow(self, data):
        kline_utils.openInCurWindow_ZS(self, data)

    def updateDay(self, day):
        if type(day) == int:
            day = str(day)
        day = day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
        q = orm.THS_ZS_ZD.select(orm.THS_ZS_ZD.day).distinct().where(orm.THS_ZS_ZD.day <= day).order_by(orm.THS_ZS_ZD.day.desc()).limit(len(self.cols)).tuples()
        for i, d in enumerate(q):
            cday = d[0]
            ds = orm.THS_ZS_ZD.select().where(orm.THS_ZS_ZD.day == cday)
            datas = [d.__data__ for d in ds]
            self.listWins[i]._filter_mark_ = False
            self.listWins[i].setData(datas)
            self.listWins[i]._day = cday
            self.listWins[i].invalidWindow()
            sday = cday[0 : 4] + '-' + cday[4 : 6] + '-' + cday[6 : ]
            self.daysLabels[i].setText(cday)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            size = self.getClientSize()
            self.layout.resize(0, 0, size[0], size[1])
            self.invalidWindow()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)