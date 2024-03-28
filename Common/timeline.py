import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys, requests
import win32gui, win32con

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr
from THS import orm, ths_win
from Common import base_win

class TimelineModel:
    def __init__(self):
        self.henxi = henxin.HexinUrl()
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
        #if self.code != code:
        self.code = code
        self.dataFile = datafile.DataFile(code, datafile.DataFile.DT_MINLINE, datafile.DataFile.FLAG_ALL)
        self.ddlrFile = ths_ddlr.ThsDdlrDetailData(code)
        try:
            #url = self.henxi.getFenShiUrl(code)
            #todayData = self.henxi.loadUrlData(url)
            #if not self.dataFile.data or self.dataFile.data[-1].day != int(todayData['date']):
                # append data
            #    pass
            #print(todayData)
            pass
        except Exception as e:
            print('[FenShiModel.update] fail', code, day)
        #if day and self.day != day:
        self.day = day
        fromIdx = self.dataFile.getItemIdx(day)
        if fromIdx < 0:
            self.fsData = None
        else:
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
            # insert 9:30 data 通达信合并了9:30和9:31的数据
            c930 = copy.copy(self.fsData[0])
            c930.time = 930
            c930.amount = c930.vol = 0
            c930.avgPrice = c930.close = c930.open
            self.fsData.insert(0, c930)

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
        if not self.ddlrGroupData:
            return self.ddlrFilterData
        for ds in self.ddlrGroupData:
            rd = []
            for d in ds:
                if d['money'] >= money:
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

class TimelineWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.leftPriceRect = None
        self.rightPriceRect = None
        self.minutesRect = None
        self.model = TimelineModel()
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
        if idx >= len(self.model.fsData):
            return -1
        return idx

    def getMinuteData(self, idx):
        fds = self.model.fsData
        if idx < 0 or not fds:
            return None
        return fds[idx]
    
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
        # draw minutes
        for i, d in enumerate(fsd):
            x = self.getMinuteX(i)
            y = self.getMinuteY(d.close)
            if i == 0:
                win32gui.MoveToEx(hdc, x, y)
            else:
                win32gui.LineTo(hdc, x, y)
        # draw avg price
        self.drawer.use(hdc, self.drawer.getPen(0x4782AE, width=2))
        for i, d in enumerate(fsd):
            x = self.getMinuteX(i)
            y = self.getMinuteY(d.avgPrice)
            if i == 0:
                win32gui.MoveToEx(hdc, x, y)
            else:
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
        x = self.getMinuteX(idx)
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
        if money == 0:
            return 0
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
        _time = ds[0]['beginTime']
        idx = self.timeToIdx(_time)
        data = self.getMinuteData(idx)
        price = data.close
        x = self.getMinuteX(idx)
        y = self.getMinuteY(price)
        buy = sell = 0
        for d in ds:
            bs, money = d['bs'], d['money']
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
            self.drawer.fillCycle(hdc, buyRc,  0x2524A1) # 0x2524A1  0x2E2FFF
            vs = win32gui.SetROP2(hdc, win32con.R2_MERGEPEN)
            self.drawer.fillCycle(hdc, sellRc, 0x0F570E) # 0x0F570E 0x00D600
            win32gui.SetROP2(hdc, vs)
        else:
            self.drawer.fillCycle(hdc, sellRc, 0x0F570E) # 0x0F570E 0x00D600
            vs = win32gui.SetROP2(hdc, win32con.R2_MERGEPEN)
            self.drawer.fillCycle(hdc, buyRc,  0x2524A1) # 0x2524A1  0x2E2FFF
            win32gui.SetROP2(hdc, vs)

    def onClick(self, x, y):
        idx = self.getMinuteIdx(x)
        data = self.getMinuteData(idx)
        if not data:
            return
        _time = data.time
        self.notifyListener(self.Event('click.ddlr.time', self, time = _time))

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
