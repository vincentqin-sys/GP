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
        self.cols = (200, 150, 60, 200, 100, 60, 60, 60, '1fr')
        self.layout = base_win.GridLayout(rows, self.cols, (5, 10))
        self.tableWin = base_win.TableWindow()
        self.tableCntWin = table.EditTableWindow()
        self.editorWin = base_win.Editor()
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.autoSyncCheckBox = base_win.CheckBox({'title': '自动同步显示'})
        self.tcgnDatas = []
        self.allDatas = []
        #base_win.ThreadPool.addTask()
        self.curTcgn = None
        self.sm = base_win

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
            {'title': '', 'width': 30, 'name': '#idx' , 'fontSize' : 14},
            {'title': '一级题材概念', 'width': 120, 'name': 'tcgn', 'editable': False, 'fontSize' : 14, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
            {'title': '二级题材概念', 'width': 150, 'name': 'tcgn_sub', 'editable': True, 'fontSize' : 14, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
            {'title': '股票名称', 'width': 70, 'name': 'name', 'editable': True, 'fontSize' : 14},
            {'title': '股票代码', 'width': 70, 'name': 'code', 'editable': True, 'fontSize' : 14},
            {'title': '详情', 'stretch': 1, 'name': 'info', 'editable': True, 'fontSize' : 14, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
        ]
        self.checkBox.createWindow(self.hwnd, (0, 0, 1, 1))
        self.autoSyncCheckBox.createWindow(self.hwnd, (0, 0, 1, 1))
        self.editorWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableCntWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableCntWin.enableListeners['ContextMenu'] = True
        self.tableWin.enableListeners['ContextMenu'] = True
        self.tableWin.rowHeight = 32
        self.tableWin.headers = headers
        self.tableCntWin.rowHeight = 40
        self.tableCntWin.headers = headers2
        addBtn = base_win.Button({'title': 'Add'})
        addBtn.createWindow(self.hwnd, (0, 0, 1, 1))
        insertBtn = base_win.Button({'title': 'Insert'})
        insertBtn.createWindow(self.hwnd, (0, 0, 1, 1))
        newBtn = base_win.Button({'title': '新建一级概念'})
        newBtn.createWindow(self.hwnd, (0, 0, 1, 1))
        delBtn = base_win.Button({'title': 'Del'})
        delBtn.createWindow(self.hwnd, (0, 0, 1, 1))
        openBtn = base_win.Button({'title': 'Open'})
        openBtn.createWindow(self.hwnd, (0, 0, 1, 1))

        
        self.layout.setContent(0, 1, self.checkBox)
        #self.layout.setContent(0, 2, newBtn)
        #self.layout.setContent(0, 4, addBtn)
        #self.layout.setContent(0, 5, insertBtn)
        #self.layout.setContent(0, 6, delBtn)
        self.layout.setContent(0, 2, openBtn)

        self.layout.setContent(0, 3, self.editorWin)
        self.layout.setContent(0, 4, self.autoSyncCheckBox)

        self.layout.setContent(1, 0, self.tableWin)
        self.layout.setContent(1, 1, self.tableCntWin, {'horExpand': -1})
        self.editorWin.addListener(self.onQuery)
        self.tableWin.addListener(self.onSelect)
        self.tableWin.addListener(self.onContextMenu_1)
        self.tableCntWin.addListener(self.onCellChanged)
        self.tableCntWin.addListener(self.onContextMenu)
        addBtn.addListener(self.onAddInsert, 'Add')
        insertBtn.addListener(self.onAddInsert, 'Insert')
        newBtn.addListener(self.onNewOrUpdate, 'New')
        delBtn.addListener(self.onDel, 'Del')
        openBtn.addListener(self.onOpen, 'Open')

        self.loadAllTcgnDatas()
        self.tableWin.setData(self.tcgnDatas)
        sm = ths_win.ThsShareMemory.instance()
        sm.open()
        sm.addListener('ListenSync_TCGN', self.onAutoSync)

    def onContextMenu_1(self, evt, args):
        if evt.name != 'ContextMenu':
            return
        selRow = self.tableWin.selRow
        rd = None
        if selRow >= 0:
            rd = self.tableWin.getData()[selRow]
        model = [{'title': '新建', 'name': 'Insert'}, 
                 {'title': '更新', 'name': 'Update', 'enable': selRow >= 0},
                 ]
        menu = base_win.PopupMenuHelper.create(self.hwnd, model)
        menu.addListener(self.onContextMenuItemSelect_1, rd)
        pos = win32gui.GetCursorPos()
        menu.show(*pos)

    def onContextMenuItemSelect_1(self, evt, args):
        if evt.name != 'Select':
            return
        item = evt.item
        if item['name'] == 'Insert':
            self.onNewOrUpdate('Click', None, None)
        elif item['name'] == 'Update':
            self.onNewOrUpdate('Click', None, args)

    def onContextMenu(self, evt, args):
        if evt.name != 'ContextMenu':
            return
        data = self.tableCntWin.getData() or []
        selRow = self.tableCntWin.selRow
        model = [{'title': '在选中行前插入', 'name': 'Insert', 'enable': selRow >= 0 or len(data) == 0}, 
                 {'title': '在选中行后添加', 'name': 'Add', 'enable': selRow >= 0 or len(data) == 0}, 
                 {'title': 'LINE'},
                 {'title': '删除选中行', 'name': 'Del', 'enable': selRow >= 0}, 
                 {'title': 'LINE'},
                 #{'title' : '打开股票', 'name': 'Open', 'enable': selRow >= 0},
                 {'title': '置顶', 'name': 'MoveTop', 'enable': selRow > 0},
                 {'title': '上移', 'name': 'MoveUp', 'enable': selRow > 0},
                 {'title': '下移', 'name': 'MoveDown', 'enable': selRow >= 0 and selRow < len(data) - 1},
                 {'title': '置底', 'name': 'MoveBottom', 'enable': selRow >= 0 and selRow < len(data) - 1},
                 ]
        menu = base_win.PopupMenuHelper.create(self.hwnd, model)
        menu.addListener(self.onContextMenuItemSelect)
        pos = win32gui.GetCursorPos()
        menu.show(*pos)
    
    def onContextMenuItemSelect(self, evt, args):
        if evt.name != 'Select':
            return
        item = evt.item
        if item['name'] == 'Insert' or item['name'] == 'Add':
            self.onAddInsert(self.Event('Click', None), item['name'])
            return
        if item['name'] == 'Del':
            dlg = dialog.ConfirmDialog('确定要删除吗?')
            def _ds(evt, args):
                if evt.name == 'OK':
                    self.onDel(self.Event('Click', None), 'Del')
            dlg.createWindow(self.hwnd, title='Confirm')
            dlg.showCenter()
            dlg.addListener(_ds)
            return
        if item['name'] == 'Open':
            self.onOpen(self.Event('Click', None), 'Open')
            return
        if item['name'].startswith('Move'):
            self.onMove(item['name'])
    
    def reload(self, tcgn, newSelRow):
        tab = self.tableCntWin
        if not tcgn:
            tab.setData([])
        else:
            si = tab.startRow
            qr = orm.TCK_TCGN.select().where(orm.TCK_TCGN.tcgn == tcgn).order_by(orm.TCK_TCGN.order_.asc()).dicts()
            dx = [d for d in qr]
            tab.setData(dx)
            tab.setSelRow(newSelRow)
            tab.startRow = si
        tab.invalidWindow()

    def onMove(self, name):
        datas = self.tableCntWin.getData()
        if len(datas) <= 1:
            return
        selRow = self.tableCntWin.selRow
        selData = datas[selRow]
        tcgn = selData['tcgn']
        if name == 'MoveUp' or name == 'MoveDown':
            delta = 1 if name == 'MoveUp' else -1
            preData = datas[selRow - delta]
            qr = orm.TCK_TCGN.update({orm.TCK_TCGN.order_ : preData['order_']}).where(orm.TCK_TCGN.id == selData['id'])
            qr.execute()
            qr = orm.TCK_TCGN.update({orm.TCK_TCGN.order_ : selData['order_']}).where(orm.TCK_TCGN.id == preData['id'])
            qr.execute()
            self.reload(tcgn, selRow - delta)
        elif name == 'MoveBottom':
            newOrder = datas[-1]['order_'] + 1
            qr = orm.TCK_TCGN.update({orm.TCK_TCGN.order_ : newOrder}).where(orm.TCK_TCGN.id == selData['id'], orm.TCK_TCGN.tcgn == tcgn)
            qr.execute()
            self.reload(tcgn, len(datas) - 1)
        elif name == 'MoveTop':
            newOrder = datas[0]['order_']
            qr = orm.TCK_TCGN.update({orm.TCK_TCGN.order_ : orm.TCK_TCGN.order_ + 1}).where(orm.TCK_TCGN.order_ < selData['order_'], orm.TCK_TCGN.tcgn == tcgn)
            qr.execute()
            qr = orm.TCK_TCGN.update({orm.TCK_TCGN.order_ : newOrder}).where(orm.TCK_TCGN.id == selData['id'])
            qr.execute()
            self.reload(tcgn, 0)

    def onCellChanged(self, evt, args):
        if evt.name != 'CellChanged':
            return
        name = evt.header['name']
        cellVal = evt.data[name].strip()
        qr = orm.TCK_TCGN.update({name : cellVal}).where(orm.TCK_TCGN.id == evt.data['id'])
        qr.execute()
        if name != 'name':
            return
        code = self.getCodeByName(cellVal)
        if not code or evt.data['code'] == code:
            return
        qr = orm.TCK_TCGN.update({'code' : code}).where(orm.TCK_TCGN.id == evt.data['id'])
        qr.execute()
        evt.data['code'] = code

    def onDel(self, evt, args):
        if evt.name != 'Click':
            return
        row = self.tableCntWin.selRow
        if row < 0:
            return
        model = self.tableCntWin.getData()
        data = model[row]
        orm.TCK_TCGN.delete_by_id(data['id'])
        model.pop(row)
        self.tableCntWin.invalidWindow()

    def onOpen(self, evt, args):
        if evt.name != 'Click':
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

    def onNewOrUpdate(self, evt, args):
        if evt.name != 'Click':
            return
        dlg = dialog.InputDialog()
        dlg.createWindow(self.hwnd, (0, 0, 300, 70), title='一级题材概念')
        if args: # is update
            dlg.setText(args['tcgn'])
        dlg.showCenter()
        dlg.addListener(self.onDialogInputEnd, args)

    def onDialogInputEnd(self, evt, args):
        if evt.name != 'InputEnd':
            return
        txt = evt.text or ''
        if not txt:
            return
        if txt and txt.strip():
            self.curTcgn = txt.strip()
        if not args: # insert
            self.tableCntWin.setData([])
            dt = self.tableWin.getData()
            if dt == None:
                dt = []
                self.tableWin.setData(dt)
            dt.append({'tcgn': self.curTcgn})
            self.tableWin.setSelRow(len(dt) - 1)
            self.tableWin.showRow(len(dt) - 1)
        else: # update
            qr = orm.TCK_TCGN.update({orm.TCK_TCGN.tcgn : self.curTcgn}).where(orm.TCK_TCGN.tcgn == args['tcgn'])
            qr.execute()
            args['tcgn'] = self.curTcgn
        self.tableCntWin.invalidWindow()
        self.tableWin.invalidWindow()
        
    def onAddInsert(self, evt, args):
        if evt.name != 'Click':
            return
        if not self.curTcgn:
            return
        cur = {'tcgn' : self.curTcgn, 'tcgn_sub': '', 'code': '', 'name':'', 'info':'', 'order_': 0}

        def getMaxOrder(model):
            if not model:
                return 0
            order = 0
            for m in model:
                order = max(order, m['order_'])
            return order

        model = self.tableCntWin.getData()
        curSelRow = self.tableCntWin.selRow
        rl = -1
        if not model:
            cur['order_'] = 0
            rl = 0
        elif curSelRow < 0:
            cur['order_'] = getMaxOrder(model)
            rl = len(model)
        elif args == 'Add':
            rl = curSelRow + 1
            selData = model[curSelRow]
            cur['order_'] = selData['order_'] + 1
            cur['tcgn_sub'] = selData['tcgn_sub']
            qr = orm.TCK_TCGN.update({orm.TCK_TCGN.order_ : orm.TCK_TCGN.order_ + 1}).where(orm.TCK_TCGN.tcgn == self.curTcgn, orm.TCK_TCGN.order_ > selData['order_'])
            qr.execute()
        elif args == 'Insert':
            rl = curSelRow
            selData = model[curSelRow]
            cur['order_'] = selData['order_']
            cur['tcgn_sub'] = selData['tcgn_sub']
            qr = orm.TCK_TCGN.update({orm.TCK_TCGN.order_ : orm.TCK_TCGN.order_ + 1}).where(orm.TCK_TCGN.tcgn == self.curTcgn, orm.TCK_TCGN.order_ >= selData['order_'])
            qr.execute()
        if model == None:
            model = []
            self.tableCntWin.setData(model)
        obj = orm.TCK_TCGN.create(**cur)
        self.reload(cur['tcgn'], rl)

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
        self.onQuery(self.Event('PressEnter', self, text = self.editorWin.text), None)

    def onQuery(self, evt, args):
        if evt.name != 'PressEnter':
            return
        queryText = evt.text
        if not queryText:
            self.reload(self.curTcgn, 0)
            return
        queryText = queryText.upper()
        llt = getattr(self, 'last_load_time', 0)
        if time.time() - llt > 10 * 60: # 10 minutes
            qr = orm.TCK_TCGN.select().dicts()
            self.allDatas = [d for d in qr]
            setattr(self, 'last_load_time', time.time())

        if '|' in queryText:
            qs = queryText.split('|')
            cond = 'OR'
        else:
            qs = queryText.split(' ')
            cond = 'AND'
        qrs = []
        for q in qs:
            q = q.strip()
            if q and q not in qrs:
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
        
        searchDatas = []
        for d in self.allDatas:
            if match(d, qrs, cond):
                searchDatas.append(d)
        self.tableCntWin.setData(searchDatas)
        self.tableCntWin.invalidWindow()
    
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
        
    def onSelect(self, evt, args):
        if evt.name != 'SelectRow':
            return
        data = evt.data
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

    def openKlineMinutes(self, evt, parent):
        if evt.name != 'DbClick':
            return
        win = ddlr_detail.DDLR_MinuteMgrWindow()
        rc = win32gui.GetWindowRect(parent.hwnd)
        win.createWindow(parent.hwnd, rc, win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION)
        day = evt.data.day
        win.updateCodeDay(evt.code, day)

    def loadAllTcgnDatas(self):
        qr = orm.TCK_TCGN.select(orm.TCK_TCGN.tcgn).distinct().dicts()
        rs = []
        for d in qr:
            rs.append(d)
        self.tcgnDatas = rs

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