from win32.lib.win32con import WS_CHILD, WS_VISIBLE
import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

from Tdx import datafile, orm as tdx_orm
from THS.download import henxin, load_ths_ddlr
from THS import orm as ths_orm
from FuPan import ddlr, multi_kline
from Common import base_win, kline

class KPL_Window(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.day = None
        self.data = None
        self.paddings = (10, 5, 10, 0) # left, top, right, bottom
        self.itemWidth = 16 # 每项宽度
        self.itemFontSize = 12

    def onDraw(self, hdc):
        #self.drawer.drawRect2(hdc, (0, 0, *self.getClientSize()), 0xff0000)
        if not self.data:
            return
        w, h = self.getClientSize()
        # draw scqx
        SCQX_CYCLE_H, SCQX_H = 20, 8
        scqdRect = [self.paddings[1] + 15, self.paddings[1] + (SCQX_CYCLE_H - SCQX_H) // 2, w - self.paddings[2] - 60, self.paddings[1] + (SCQX_CYCLE_H - SCQX_H) // 2 + SCQX_H]
        scqdCycle = [self.paddings[1] + 10, self.paddings[1], self.paddings[1] + 10 + SCQX_CYCLE_H, self.paddings[1] + SCQX_CYCLE_H]
        self.drawer.fillRect(hdc, scqdRect, 0xaaaaaa)
        self.drawer.fillCycle(hdc, scqdCycle, 0x00cc00)
        zhqd = self.data.get('zhqd', 0)
        sgx = int((scqdRect[2] - scqdRect[0]) / 100 * min(zhqd, 40))
        rc = [scqdRect[0], scqdRect[1], scqdRect[0] + sgx, scqdRect[3]]
        self.drawer.fillRect(hdc, rc, 0x00cc00)
        if zhqd > 40:
            szx = int((scqdRect[2] - scqdRect[0]) / 100 * (min(zhqd, 60) - 40))
            rc2 = [rc[2], scqdRect[1], rc[2] + szx, scqdRect[3]]
            self.drawer.fillRect(hdc, rc2, 0x00ccff)
        if zhqd > 60:
            smx = int((scqdRect[2] - scqdRect[0]) / 100 * (zhqd - 60))
            rc3 = [rc2[2], scqdRect[1], rc2[2] + smx, scqdRect[3]]
            self.drawer.fillRect(hdc, rc3, 0x0000ff)
        fnt = self.drawer.getFont(fontSize=18, weight=1000)
        self.drawer.use(hdc, fnt)
        color = 0x00cc00
        if zhqd > 40: color = 0x00ccff
        if zhqd > 60: color = 0x0000ff
        self.drawer.drawText(hdc, f'{zhqd}', (scqdRect[2] + 10, scqdRect[1] - 5, scqdRect[2] + 60, scqdRect[3] + 5), color, align=win32con.DT_LEFT)
        # draw items
        NUM = 11
        endY = h - 54 - self.paddings[3]
        startY = 50
        space = (w - self.itemWidth * NUM - self.paddings[0] - self.paddings[2]) / (NUM - 1)
        keys = ('ztNum', 'z7', 'z5_7', 'z2_5', 'z0_2', 'zeroNum', 'd0_2', 'd2_5', 'd5_7', 'd7', 'dtNum')
        titles = ('涨停', '>7', '5-7', '2-5', '0-2', '平', '0-2', '2-5', '5-7', '<7', '跌停')
        maxNum = 1
        for v in keys:
            n = self.data.get(v, 0)
            maxNum = max(n, maxNum)
        for i, k in enumerate(keys):
            sx = int(space * (i + 1)) + self.itemWidth * i
            color = 0xaaaaaa
            if i < 5:
                color = 0x0000ff
            elif i > 5:
                color = 0x00ff00
            ih = self.data.get(k, 0) / maxNum * (endY - startY)
            ih = max(ih, 1)
            sy = endY - int(ih)
            rc = (sx, sy, sx + self.itemWidth, endY)
            self.drawer.fillRect(hdc, rc, color)
            rc = [sx - 3, sy - 15, sx + self.itemWidth + 3, sy]
            fnt = self.drawer.getFont(fontSize = self.itemFontSize)
            self.drawer.use(hdc, fnt)
            self.drawer.drawText(hdc, f'{self.data.get(k, 0)}', rc, color)
            rc[1] = endY + 4
            rc[3] = endY + 20
            self.drawer.drawText(hdc, titles[i], rc, color)
        # draw upNum
        UD_HEIGHT = 10
        zY = endY + 25
        ARROW = 10
        space2 = 5
        WW = w - self.paddings[0] - self.paddings[2] - space * 2
        mmn = max(self.data['upNum'] + self.data['downNum'] + self.data['zeroNum'], 1)
        upW = int(WW * self.data['upNum'] / mmn)
        ps = win32gui.GetStockObject(win32con.NULL_PEN)
        win32gui.SelectObject(hdc, ps)
        sx = self.paddings[0]
        ex = sx + upW
        self.drawer.use(hdc, self.drawer.getBrush(0x0000ff))
        win32gui.Polygon(hdc, [(sx, zY), (ex + ARROW, zY), (ex, zY + UD_HEIGHT), (sx, zY + UD_HEIGHT), (sx, zY)])
        zTY = zY + UD_HEIGHT + 5
        self.drawer.use(hdc, self.drawer.getFont(fontSize=14))
        self.drawer.drawText(hdc, f"{self.data['upNum']}家", (sx, zTY, sx + 50, zTY + 20), color=0x0000ff, align = win32con.DT_LEFT)
        # draw zeroNum
        zeroW = max(int(WW * self.data['zeroNum'] / mmn), 2)
        sx = ex + space2
        ex = sx + zeroW
        self.drawer.use(hdc, self.drawer.getBrush(0xaaaaaa))
        win32gui.Polygon(hdc, [(sx + ARROW, zY), (ex + ARROW, zY), (ex, zY + UD_HEIGHT), (sx, zY + UD_HEIGHT), (sx + ARROW, zY)])
        # draw downNum
        sx = ex + space2
        ex = int(w - self.paddings[2])
        self.drawer.use(hdc, self.drawer.getBrush(0x00ff00))
        win32gui.Polygon(hdc, [(sx + ARROW, zY), (ex, zY), (ex, zY + UD_HEIGHT), (sx, zY + UD_HEIGHT), (sx + ARROW, zY)])
        self.drawer.drawText(hdc, f"{self.data['downNum']}家", (ex - 50, zTY, ex, zTY + 20), color=0x00ff00, align = win32con.DT_RIGHT)
        # draw amount
        sx = w // 2
        amount = int(self.data['amount'])
        self.drawer.drawText(hdc, f"{amount}亿", (sx - 50, zTY, sx + 50, zTY + 20), color=0xaaaaaa, align = win32con.DT_CENTER)

    def getTradeDays(self):
        qr = tdx_orm.TdxLSModel.select(tdx_orm.TdxLSModel.day).distinct().order_by(tdx_orm.TdxLSModel.day.asc()).tuples()
        d = [dx[0] for dx in qr]
        return d

    def getLastTradeDay(self):
        ds = self.getTradeDays()
        return ds[-1]

    def updateDay(self, day):
        if self.day == day or not day:
            return
        if type(day) == str:
            day = int(day.replace('-', ''))
        self.day = day
        obj = tdx_orm.TdxLSModel.get_or_none(day = self.day)
        if not obj:
            self.data = {}
        else:
            self.data = obj.__data__
        day = f'{self.day // 10000}-{self.day // 100 % 100 :02d}-{self.day % 100 :02d}'
        obj = ths_orm.KPL_SCQX.get_or_none(day = day)
        if obj:
            self.data['zhqd'] = obj.zhqd
        self.invalidWindow()

    def nextDay(self):
        days = self.getTradeDays()
        if self.day not in days:
            self.updateDay(days[-1])
            return True
        idx = days.index(self.day)
        if idx != len(days) - 1:
            self.updateDay(days[idx + 1])
            return True
        return False
    
    def preDay(self):
        days = self.getTradeDays()
        if self.day not in days:
            self.updateDay(days[-1])
            return True
        idx = days.index(self.day)
        if idx != 0:
            self.updateDay(days[idx - 1])
            return True
        return False

class KPL_ZT_TableWindow(base_win.TableWindow):
    def __init__(self) -> None:
        super().__init__()
        self.headers = [{'name':'#idx', 'title':'', 'width': 30}, 
                        {'name':'name', 'title':'股票名称', 'width': 70}, 
                        {'name':'ztTime', 'title':'涨停时间', 'width': 60}, 
                        {'name':'status', 'title':'状态', 'width': 60}, 
                        {'name':'ztReason', 'title':'涨停原因', 'width': 60.5}] # {'name':'#idx', 'title':''}, 

    def updateDay(self, day):
        if not day:
            self.setData(None)
            return
        if type(day) == int:
            day = f'{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}'
        elif type(day) == str and len(day) == 8:
            day = day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
        qr = ths_orm.KPL_ZT.select().where(ths_orm.KPL_ZT.day == day)
        if self.data:
            self.data.clear()
        self.setData([d.__data__ for d in qr])
        self.invalidWindow()

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDBLCLK:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            if y > self.headHeight and y < self.getClientSize()[1] - self.tailHeight:
                y -= self.headHeight
                row = y // self.rowHeight + self.startIdx
                self.notifyListener('DbClick', {'row': row, 'data': self.data[row]})
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class KPL_MgrWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.layout = base_win.GridLayout((170, 30, '1fr'), (400, '1fr'), (10, 10))
        self.kplWin = KPL_Window()
        self.kplTableWin = KPL_ZT_TableWindow()
        self.multiKLineWin = multi_kline.MultiKLineWindow()
        self.datePickerWin = base_win.DatePicker()

    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.layout.setContent(0, 0, self.kplWin)
        self.layout.setContent(2, 0, self.kplTableWin)
        self.layout.setContent(0, 1, self.multiKLineWin, {'verExpand' : -1})
        gl = base_win.GridLayout(('100%', ), (40, '1fr', 150, '1fr', 40), (0, 5))
        preDayBtn = base_win.Button({'name': 'pre-day-btn', 'title': '<<'})
        nextDayBtn = base_win.Button({'name': 'next-day-btn', 'title': '>>'})
        preDayBtn.addListener('pre', self.onLisetenSelectDay)
        nextDayBtn.addListener('next', self.onLisetenSelectDay)
        preDayBtn.createWindow(self.hwnd, (0, 0, 40, 30))
        nextDayBtn.createWindow(self.hwnd, (0, 0, 40, 30))
        gl.setContent(0, 0, preDayBtn)
        gl.setContent(0, 2, self.datePickerWin)
        gl.setContent(0, 4, nextDayBtn)
        self.layout.setContent(1, 0, gl)
        self.kplWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.kplTableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.multiKLineWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.datePickerWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.datePickerWin.addListener('DatePicker', self.onLisetenDatePickerChanged)
        self.kplTableWin.addListener('TableWindow', self.onListenTable)
        self.layout.resize(0, 0, *self.getClientSize())

    def onLisetenSelectDay(self, target, evtName, evtInfo):
        #print('onLisetenSelectDay: ', target, evtName, evtInfo)
        if target == 'next':
            self.kplWin.nextDay()
            self.datePickerWin.setSelDay(self.kplWin.day)
            self.kplTableWin.updateDay(self.kplWin.day)
        elif target == 'pre': 
            self.kplWin.preDay()
            self.datePickerWin.setSelDay(self.kplWin.day)
            self.kplTableWin.updateDay(self.kplWin.day)

    def onLisetenDatePickerChanged(self, target, evtName, evtInfo):
        day = evtInfo['curSelDay']
        #day = f'{day.year}-{day.month :02d}-{day.day :02d}'
        self.kplWin.updateDay(day)
        self.kplTableWin.updateDay(day)

    def onLisetenEvent(self, target, evtName, evtInfo):
        print('onLisetenEvent: ', target, evtName, evtInfo)
        pass

    def onListenTable(self, target, evtName, evtInfo):
        if evtName == 'DbClick' or evtName == 'RowEnter':
            data = evtInfo['data']
            self.multiKLineWin.updateCode(data['code'])
            self.multiKLineWin.setMarkDay(data['day'])
            self.multiKLineWin.makeVisible(data['day'])

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            w, h = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.layout.resize(0, 0, w, h)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

    def init(self):
        #self.multiKLineWin.updateCode('603259')
        day = self.kplWin.getLastTradeDay()
        self.kplWin.updateDay(day)
        self.datePickerWin.setSelDay(day)
        self.kplTableWin.updateDay(day)

if __name__ == '__main__':
    kpl = KPL_MgrWindow()
    kpl.createWindow(None, (0, 0, 1000, 400), win32con.WS_OVERLAPPEDWINDOW)
    win32gui.ShowWindow(kpl.hwnd, win32con.SW_MAXIMIZE)
    kpl.init()
    win32gui.PumpMessages()