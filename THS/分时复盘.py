import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys, requests
import win32gui, win32con

cwd = os.getcwd()
w = cwd.index('GP')
cwd = cwd[0 : w + 2]
sys.path.append(cwd)
from Tdx import datafile
from THS.download import henxin, load_ths_ddlr
from THS import orm, base_win, ths_win

class FenShiModel:
    def __init__(self):
        self.dataFile = None
        self.ddlrFile = None
        self.fsData = None # 当日分时线数据
        self.ddlrData = None #当日大单流入数据
        self.ddlrGroupData = None
        self.ddlrFilterData = None #按分钟分组(filter)
        self.code = None
        self.day = None

        self.pre = 0
        self.priceRange = None

    def isValid(self):
        return (self.fsData != None) and (len(self.fsData) > 0)

    def update(self, code, day):
        if not code:
            return
        if type(code) == int:
            code = f'{code :06d}'
        if self.code != code:
            self.code = code
            self.dataFile = datafile.DataFile(code, datafile.DataFile.DT_MINLINE, datafile.DataFile.FLAG_ALL)
            self.ddlrFile = load_ths_ddlr.ThsDdlrDetailData(code)
        if day and self.day != day:
            self.day = day
            fromIdx = self.dataFile.getItemIdx(day)
            endIdx = fromIdx + 240 - 1
            while True:
                if endIdx >= len(self.dataFile.data):
                    break
                m = self.dataFile.data[endIdx]
                if m.day == day:
                    endIdx += 1
                else:
                    break
            self.dataFile.calcAvgPriceOfDay(int(day))
            self.fsData = self.dataFile.data[fromIdx : endIdx]
            self.ddlrData = self.ddlrFile.getDataAtDay(day)
            self.groupDDLRByTime()
            if fromIdx > 0:
                self.pre = self.dataFile.data[fromIdx - 1].close
            else:
                self.pre = self.dataFile.data[fromIdx].open
            self.priceRange = None

    def getTimeData(self, time_):
        pass

    def groupDDLRByTime(self):
        if not self.ddlrData:
            return
        self.ddlrGroupData = []
        i = 0
        while i < len(self.ddlrData):
            b, e = self.ddlrFile.getMiniteDataRange(self.ddlrData, i)
            self.ddlrGroupData.append(self.ddlrData[b : e])
            i = e
    
    def filterDDLR(self, money):
        self.ddlrFilterData = []
        for ds in self.ddlrGroupData:
            rd = []
            for d in ds:
                if d[2] >= money:
                    rd.append(d)
            if len(rd) > 0:
                self.ddlrFilterData.append(rd)
        return self.ddlrFilterData

    def getPriceRange(self):
        if not self.fsData:
            return None
        if self.priceRange:
            return self.priceRange
        minPrice = maxPrice = 0
        for dt in self.fsData:
            if minPrice == 0:
                minPrice = dt.low
                maxPrice = dt.high
            else:
                minPrice = min(minPrice, dt.low)
                maxPrice = max(maxPrice, dt.high)
        ds = max(abs(maxPrice - self.pre), abs(minPrice - self.pre))
        maxPrice = self.pre + ds
        minPrice = self.pre - ds
        self.priceRange = (minPrice, maxPrice)
        return self.priceRange

class FenShiWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.leftPriceRect = None
        self.rightPriceRect = None
        self.minutesRect = None
        self.model = FenShiModel()
        self.mouseXY = None
        self.showDDLR = False

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.onSize()

    def onSize(self):
        rect = self.getClientSize()
        w, h = rect[0], rect[1]
        LPW, RPW = 50, 60
        self.leftPriceRect = (0, 0, LPW, h)
        self.rightPriceRect = (w - LPW, 0, w, h)
        self.minutesRect = (LPW, 10, w - RPW, h - 30)

    def onDraw(self, hdc):
        self.drawer.fillRect(hdc, self.minutesRect, 0x171515)
        if not self.model.isValid():
            return
        self.drawBackground(hdc)
        self.drawMinite(hdc)
        self.drawMouse(hdc)
        self.drawDDLRCycle(hdc)
    
    def timeToIdx(self, _time):
        if _time <= 930:
            return 0
        hour = _time // 100
        minute = _time % 100
        ds = 0
        if hour <= 11:
            ds = 60 * (hour - 9) + minute - 30
            return ds
        ds = 120
        ds += minute + (hour - 13) * 60
        return ds

    def getMinuteX(self, idx):
        w = self.minutesRect[2] - self.minutesRect[0]
        sw = w / 240
        return int(sw * idx) + self.minutesRect[0]

    def getMinuteY(self, price):
        priceRange = self.model.getPriceRange()
        if not priceRange:
            return 0
        h = self.minutesRect[3] - self.minutesRect[1]
        p = (price - priceRange[0]) / (priceRange[1] - priceRange[0])
        y = h - int(p * h) + self.minutesRect[1]
        return y

    def getMinuteIdx(self, x):
        if not self.model.fsData:
            return -1
        if x < self.minutesRect[0]:
            return -1
        x -= self.minutesRect[0]
        w = self.minutesRect[2] - self.minutesRect[0]
        sw = w / 240
        idx = int(x / sw)
        if idx > len(self.model.fsData):
            return -1
        return idx

    def getMinuteData(self, idx):
        if idx < 0:
            return None
        fds = self.model.fsData
        if not fds:
            return None
        if idx == 0:
            d = copy.copy(fds[0])
            d.close = d.open
            d.time = 930
            return d
        return fds[idx - 1]
    
    def drawBackground(self, hdc):
        if not self.model.fsData:
            return
        mr = self.minutesRect
        # draw horizontal line
        pr = self.model.getPriceRange()
        ph = (pr[1] - pr[0]) / 4
        ps = (pr[1], pr[1] - ph, self.model.pre, self.model.pre - ph, pr[0])
        for i, price in enumerate(ps):
            y = self.getMinuteY(price)
            style = win32con.PS_SOLID if i % 2 == 0 else win32con.PS_DOT
            self.drawer.drawLine(hdc, mr[0], y, mr[2], y, 0x36332E, style=style)
            p1 = f'{price / 100 :.02f}'
            color = 0x0000ff if price >= self.model.pre else 0x00ff00
            rc = (self.leftPriceRect[0], y - 8, self.leftPriceRect[2]- 5, y + 8)
            self.drawer.drawText(hdc, p1, rc, color, align=win32con.DT_RIGHT)
            zf = (price - self.model.pre) / self.model.pre * 100
            p2 = f'{zf :.02f}%'
            rc = (self.rightPriceRect[0] + 5, y - 8, self.rightPriceRect[2], y + 8)
            self.drawer.drawText(hdc, p2, rc, color, align=win32con.DT_LEFT)
        # draw vertical line
        times = ('09:30', '10:00', '10:30', '11:00', '11:30', '13:30', '14:00', '14:30', '15:00')
        for i in range(9):
            idx = i * 30
            x = self.getMinuteX(idx)
            style = win32con.PS_SOLID if i % 4 == 0 else win32con.PS_DOT
            self.drawer.drawLine(hdc, x, mr[1], x, mr[3], 0x36332E, style)
            rc = (x - 20, mr[3], x + 20, mr[3] + 20)
            self.drawer.drawText(hdc, times[i], rc, 0x36332E, align=win32con.DT_CENTER)

    def drawMinite(self, hdc):
        fsd = self.model.fsData
        if not fsd:
            return
        self.drawer.use(hdc, self.drawer.getPen(0x888888, width=2))
        # minute data is begin from 09:31
        # draw 09:30
        price = fsd[0].open
        win32gui.MoveToEx(hdc, self.getMinuteX(0), self.getMinuteY(price))
        for i, d in enumerate(fsd):
            x = self.getMinuteX(i + 1)
            y = self.getMinuteY(d.close)
            win32gui.LineTo(hdc, x, y)
        # draw avg price
        self.drawer.use(hdc, self.drawer.getPen(0x4782AE, width=2))
        win32gui.MoveToEx(hdc, self.getMinuteX(0), self.getMinuteY(price))
        for i, d in enumerate(fsd):
            x = self.getMinuteX(i + 1)
            y = self.getMinuteY(d.avgPrice * 100)
            win32gui.LineTo(hdc, x, y)

    def drawMouse(self, hdc):
        fsd = self.model.fsData
        if not self.mouseXY or not fsd:
            return
        x, y = self.mouseXY
        mr = self.minutesRect
        idx = self.getMinuteIdx(x)
        if idx < 0:
            return
        md = self.getMinuteData(idx)
        price = md.close
        my = self.getMinuteY(price)
        self.drawer.drawLine(hdc, x, mr[1], x, mr[3], 0xdddddd, win32con.PS_DOT)
        self.drawer.drawLine(hdc, mr[0], my, mr[2], my, 0xdddddd, win32con.PS_DOT)
        # left price tip
        py = self.getMinuteY(price)
        rc = (self.leftPriceRect[0], py - 8, self.leftPriceRect[2], py + 8)
        color = 0x2E2FFF if price >= self.model.pre else 0x00D600
        self.drawer.fillRect(hdc, rc, color)
        self.drawer.drawText(hdc, f'{price / 100 :.02f} ', rc, 0xE9E9FF, align=win32con.DT_RIGHT)
        #right zf rate tip
        zf = (price - self.model.pre) / self.model.pre * 100
        rc = (self.rightPriceRect[0], py - 8, self.rightPriceRect[2], py + 8)
        self.drawer.fillRect(hdc, rc, color)
        self.drawer.drawText(hdc, f' {zf :.02f}%', rc, 0xE9E9FF, align=win32con.DT_LEFT)
        # bottom time tip
        timeTip = md.time
        timeTip = f'{timeTip // 100 :02d}:{timeTip % 100 :02d}'
        rc = (x - 20, mr[3], x + 20, mr[3] + 20)
        self.drawer.fillRect(hdc, rc, 0x8C8C8C)
        self.drawer.drawText(hdc, timeTip, rc, 0xededed)

    def drawDDLRCycle(self, hdc):
        fsd = self.model.fsData
        gd = self.model.ddlrFilterData
        if (not fsd) or (not gd):
            return
        for i, d in enumerate(gd):
            self.drawDDLRItemCycle(hdc, d)

    def getCycleWidth(self, money):
        if money >= 1000:
            return 16
        if money >= 500:
            return 14
        if money >= 300:
            return 12
        if money >= 100:
            return 10
        return 8

    def drawDDLRItemCycle(self, hdc, ds):
        if not ds:
            return
        _time = ds[0][0]
        idx = self.timeToIdx(_time)
        data = self.getMinuteData(idx)
        price = data.close
        x = self.getMinuteX(idx)
        y = self.getMinuteY(price)
        buy = sell = 0
        for d in ds:
            t, bs, money, *_ = d
            if bs <= 2:
                buy += money
            else:
                sell += money
        buyWidth = self.getCycleWidth(buy)
        sellWidth = self.getCycleWidth(sell)
        sx, sy = x - buyWidth // 2, y - buyWidth // 2
        buyRc = (sx, sy, sx + buyWidth, sy + buyWidth)
        sx, sy = x - sellWidth // 2, y - sellWidth // 2
        sellRc = (sx, sy, sx + sellWidth, sy + sellWidth)
        if buy >= sell:
            self.drawer.fillCycle(hdc, buyRc, 0x2524A1)
        else:
            self.drawer.fillCycle(hdc, sellRc, 0x088809)
            #vs = win32gui.SetROP2(hdc, win32con.R2_MASKPEN)
            #self.drawer.fillCycle(hdc, buyRc, 0x3333ff)
        #win32gui.SetROP2(hdc, vs)

    def onClick(self, x, y):
        idx = self.getMinuteIdx(x)
        data = self.getMinuteData(idx)
        if not data:
            return
        _time = data.time
        self.notifyListener('click.ddlr.time', {'time': _time})

    def update(self, code, day):
        self.model.update(code, day)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            self.onSize()
            win32gui.InvalidateRect(hwnd, None, True)
            return False
        if msg == win32con.WM_MOUSEMOVE:
            y, x = (lParam >> 16) & 0xffff,(lParam & 0xffff)
            self.mouseXY = (x, y)
            win32gui.InvalidateRect(hwnd, None, True)
            return True
        if msg == win32con.WM_LBUTTONUP:
            y, x = (lParam >> 16) & 0xffff,(lParam & 0xffff)
            #win32gui.InvalidateRect(hwnd, None, True)
            self.onClick(x, y)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class TableWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.data = None
        self.totalData = None
        self.SCROLL_BAR_WIDTH = 10
        self.HEAD_HEIGHT = 35
        self.TAIL_HEIGHT = 100
        self.ROW_HEIGHT = 30
        self.startIdx = 0
        self.selIdx = -1
        self.filterName = None

    def drawHeadColumn(self, hdc):
        sz = self.getClientSize()[0] - self.SCROLL_BAR_WIDTH
        cw = sz // 3
        self.drawer.fillRect(hdc, (0, 0, sz, self.HEAD_HEIGHT), 0x191919)
        titles = ('开始时间', '成交量', '金额')
        for i, t in enumerate(titles):
            rc = (i * cw, 10, (i + 1) * cw, self.HEAD_HEIGHT)
            self.drawer.drawText(hdc, t, rc, 0xffffff)

    def drawTailColumn(self, hdc):
        def fmtMoney(m):
            if abs(m) < 10000:
                return f'{m}万'
            return f'{m / 10000 :.02f}亿'

        if not self.totalData:
            return
        sz = self.getClientSize()
        ch = self.TAIL_HEIGHT // (len(self.totalData) + 1)
        cw = sz[0] // 3
        sy = sz[1] - self.TAIL_HEIGHT
        self.drawer.fillRect(hdc, (0, sy, sz[0], sy + ch), 0x1A1A1A)
        self.drawer.drawRect(hdc, (0, sy, sz[0], sy + ch), 0xcacaca)
        titles = (str(self.filterName), '个数', '总金额') # , '主动', '被动'
        for i, t in enumerate(titles):
            rc = (i * cw, sy + 5, (i + 1) * cw, sy + ch)
            self.drawer.drawText(hdc, t, rc, 0xffffff)
        sy += ch
        for i, d in enumerate(self.totalData):
            if d['name'] == '买单':
                color = 0x2222ff
            elif d['name'] == '卖单':
                color = 0x22ff22
            else:
                color = 0x2222ff if d['money'] >= 0 else 0x22ff22
            vals = (d['name'], d['num'], fmtMoney(d['money']))
            for j in range(len(vals)):
                rc = (j * cw, sy + 5, (j + 1) * cw, sy + ch)
                self.drawer.drawText(hdc, str(vals[j]), rc, color)
            sy += ch


    def getVisibleRange(self):
        rowNum = self.getMaxRowNum()
        return (self.startIdx, min(self.startIdx + rowNum, len(self.data) - 1))
    
    def drawRowItem(self, hdc, sy, data, cw):
        _time, bs, money, vol = data
        if _time < 9999:
            _time *= 100
        sy += (self.ROW_HEIGHT - 14) // 2
        rc = [0, sy, cw, sy + self.ROW_HEIGHT]
        self.drawer.drawText(hdc, f'{_time // 10000 :02d}:{_time//100%100 :02d}:{_time%100 :02d}', rc, color=0xffffff)
        
        colors = (0x2E2FFF, 0x0F1CBA, 0x00D600, 0x279F3D)
        color = colors[bs - 1]
        rc[0], rc[2]= cw, cw * 2 - 20
        self.drawer.drawText(hdc, f'{vol // 100}手', rc, color=color, align=win32con.DT_RIGHT)
        rc[0], rc[2]= cw * 2, cw * 3 - 20
        self.drawer.drawText(hdc, f'{money}万', rc, color=color, align=win32con.DT_RIGHT)

    def drawRows(self, hdc):
        w = self.getClientSize()[0] - self.SCROLL_BAR_WIDTH
        cw = w // 3
        vr = self.getVisibleRange()
        y = self.HEAD_HEIGHT
        for i in range(*vr):
            if i == self.selIdx:
                self.drawer.fillRect(hdc, (0, y, w, y + self.ROW_HEIGHT), 0x393533)
            self.drawRowItem(hdc, y, self.data[i], cw)
            y += self.ROW_HEIGHT
    
    def findNearestTime(self, _time):
        if not self.data:
            return -1
        for i, d in enumerate(self.data):
            if d[0] >= _time:
                return i
        return -1

    def onListen(self, target, evtName, evtInfo):
        if evtName == 'click.ddlr.time':
            _time = evtInfo['time']
            idx = self.findNearestTime(_time)
            self.startIdx = idx
            self.selIdx = idx
            win32gui.InvalidateRect(self.hwnd, None, True)
    
    def onDraw(self, hdc):
        self.drawer.fillRect(hdc, (0, 0, *self.getClientSize()), 0x151313)
        self.drawHeadColumn(hdc)
        if not self.data:
            return
        self.drawRows(hdc)
        self.drawTailColumn(hdc)

    def setData(self, data, filterName):
        self.filterName = filterName
        self.startIdx = 0
        self.selIdx = -1
        self.totalData = None
        if not data:
            self.data = None
            return
        self.data = []
        for ds in data:
            for d in ds:
                self.data.append(d)
        buy = {'name': '买单', 'num' : 0, 'money': 0, 'zdMoney': 0, 'bdMoney': 0}
        sell = {'name': '卖单','num' : 0, 'money': 0, 'zdMoney': 0, 'bdMoney': 0}
        for d in self.data:
            _t, bs, money, *_ = d
            rr = buy if bs <= 2 else sell
            rr['num'] += 1
            rr['money'] += money
            if bs % 2 == 1:
                rr['zdMoney'] += money
            else:
                rr['bdMoney'] += money
        total = {'name':'差值', 'num': buy['num'] - sell['num'], 'money': buy['money'] - sell['money']}
        self.totalData = (buy, sell, total)
        win32gui.InvalidateRect(self.hwnd, None, True)

    def onClick(self, x, y):
        win32gui.SetFocus(self.hwnd)
        if y > self.HEAD_HEIGHT and y < self.getClientSize()[1] - self.TAIL_HEIGHT:
            y -= self.HEAD_HEIGHT
            self.selIdx = y // self.ROW_HEIGHT + self.startIdx
            win32gui.InvalidateRect(self.hwnd, None, True)

    def getMaxRowNum(self):
        h = self.getClientSize()[1]
        h -= self.HEAD_HEIGHT + self.TAIL_HEIGHT
        num = (h + self.ROW_HEIGHT - 1) // self.ROW_HEIGHT
        return num

    def onMouseWheel(self, delta):
        if not self.data:
            return
        if delta & 0x8000:
            delta = delta - 0xffff - 1
        delta = -delta // 120
        addIdx = delta * 5
        self.startIdx = max(addIdx + self.startIdx, 0)
        self.startIdx = min(self.startIdx, len(self.data) - self.getMaxRowNum())
        win32gui.InvalidateRect(self.hwnd, None, True)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDOWN:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.onClick(x, y)
            return True
        if msg == win32con.WM_MOUSEWHEEL:
            self.onMouseWheel((wParam >> 16) & 0xffff)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class GroupButton(base_win.BaseWindow):
    def __init__(self, groups, enableGroup = True) -> None:
        super().__init__()
        self.groups = groups
        self.selGroupIdx = -1
        self.enableGroup = enableGroup
    
    # group = int, is group idx
    def setSelGroup(self, group):
        if not self.enableGroup:
            return
        if type(group) == int:
            self.selGroupIdx = group
        win32gui.InvalidateRect(self.hwnd, None, True)

    def onDraw(self, hdc):
        w, h = self.getClientSize()
        cw = w / len(self.groups)
        for i in range(len(self.groups)):
            item = self.groups[i]
            color = 0x00008C if self.enableGroup and i == self.selGroupIdx else 0x333333
            rc = [int(cw * i), 0,  int((i + 1) * cw), h]
            self.drawer.fillRect(hdc, rc, color)
            self.drawer.drawRect(hdc, rc, self.drawer.getPen(0x202020))
            rc[1] = (h - 16) // 2
            self.drawer.drawText(hdc, item['title'], rc, 0x2fffff)

    def onClick(self, x, y):
        w, h = self.getClientSize()
        cw = w / len(self.groups)
        idx = int(x / cw)
        if self.enableGroup:
            self.selGroupIdx = idx
        self.notifyListener('click', {'group': self.groups[idx], 'groupIdx': idx})
        win32gui.InvalidateRect(self.hwnd, None, True)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.onClick(x, y)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)


class FuPanMgrWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.fsWin = None
        self.tableWin = None
        self.shareMem = ths_win.ThsShareMemory(False)
        self.henxi = henxin.HexinUrl()

    def create(self):
        self.shareMem.open()
        style = win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE
        rect = (0, 0, 1000, 500)
        super().createWindow(None, rect, style, title = '大单复盘')
        win32gui.ShowWindow(self.hwnd, win32con.SW_MAXIMIZE)
        
        size = self.getClientSize()
        self.tableWin = TableWindow()
        rc = (0, 50, 250, size[1] - 50)
        self.tableWin.createWindow(self.hwnd, rc)

        rc2 = (rc[2] + 5, 0, size[0] - rc[2] - 10, 400)
        self.fsWin = FenShiWindow()
        self.fsWin.createWindow(self.hwnd, rc2)
        self.fsWin.addListener(None, self.tableWin.onListen)
        
        grs = (  {'title': '50万', 'val': 50, 'desc': '50万以上'},
                 {'title': '100万', 'val': 100, 'desc': '100万以上'},
                 {'title': '300万', 'val': 300, 'desc': '300万以上'},
                 {'title': '500万', 'val': 500, 'desc': '500万以上'} )
        self.moneyBtns = GroupButton(grs)
        rc3 = (63, 10, 190, 30)
        self.moneyBtns.createWindow(self.hwnd, rc3)
        self.moneyBtns.addListener(None, self.onListenMoney)

        refreshBtn = GroupButton(({'title': '刷新', 'val': 'Refresh'}, ), False)
        rc4 = (5, 10, 50, 30)
        refreshBtn.createWindow(self.hwnd, rc4)
        refreshBtn.addListener(None, self.onListenRefresh)

    def onListenMoney(self, target, evtName, evtInfo):
        group = evtInfo['group']
        ds = self.fsWin.model.filterDDLR(group['val'])
        self.tableWin.setData(ds, group['desc'])

    def onListenRefresh(self, target, evtName, evtInfo):
        code = self.shareMem.readCode()
        day = self.shareMem.readSelDay()
        if not code or not day:
            return
        code = f'{code :06d}'
        #url = self.henxi.getTodayKLineUrl(code)
        #data = self.henxi.loadUrlData(url)
        win32gui.SetWindowText(self.hwnd, f'大单复盘 ({code} / {day})')
        self.fsWin.update(code, day)
        self.fsWin.model.filterDDLR(50)


if __name__ == '__main__':
    mgr = FuPanMgrWindow()
    mgr.create()
    win32gui.PumpMessages()