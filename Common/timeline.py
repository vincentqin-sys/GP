import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, traceback
import os, sys, requests
import win32gui, win32con

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr, cls
from THS import ths_win
from Common import base_win
from db import ths_orm

class TimelineModel:
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
        #if self.code != code:
        self.code = code
        self.dataFile = datafile.DataFile(code, datafile.DataFile.DT_MINLINE, datafile.DataFile.FLAG_ALL)
        self.ddlrFile = ths_ddlr.ThsDdlrDetailData(code)
        try:
            url = cls.ClsUrl()
            his5datas = url.loadHistory5FenShi(code)
            lastDay = 0
            if self.dataFile.data == None:
                self.dataFile.data = []
            else:
                lastDay = self.dataFile.data[-1].day
            for d in his5datas['line']:
                if d['date'] <= lastDay:
                    continue
                ts = datafile.ItemData()
                ts.day = url.getVal(d, 'date', int, 0)
                ts.time = url.getVal(d, 'minute', int, 0)
                ts.open = int(url.getVal(d, 'open_px', float, 0) * 100)
                ts.close = int(url.getVal(d, 'last_px', float, 0) * 100)
                ts.low = min(ts.open, ts.close)
                ts.high = max(ts.open, ts.close)
                ts.vol = url.getVal(d, 'business_amount', int, 0)
                ts.amount = url.getVal(d, 'business_balance', int, 0)
                self.dataFile.data.append(ts)
        except Exception as e:
            traceback.print_exc()
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
            if self.fsData[0].time == 931:
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


class SimpleTimelineModel:
    def __init__(self) -> None:
        self.code = None
        self.name = None
        self.day = None # int value
        self.pre = None # int value
        self.priceRange = None
        self.volRange = None
        self.amountRange = None
        self.data = []
        self.localData = None

    def _calcCodePre(self, idx, lines):
        if idx == 0:
            c = lines[idx]['last_px']
        else:
            c = lines[idx - 1]['last_px']
        self.pre = int(c * 100 + 0.5)

    def _loadCode_Cls_Newest(self, code):
        self.code = code
        self.data.clear()
        try:
            url = cls.ClsUrl()
            ds = url.loadFenShi(code)
            for d in ds['line']:
                ts = datafile.ItemData()
                ts.time = url.getVal(d, 'minute', int, 0)
                ts.price = int(url.getVal(d, 'last_px', float, 0) * 100 + 0.5)
                ts.vol = url.getVal(d, 'business_amount', int, 0)
                ts.amount = url.getVal(d, 'business_balance', int, 0)
                ts.avgPrice = int(url.getVal(d, 'av_px', float, 0) * 100 + 0.5)
                self.data.append(ts)
        except Exception as e:
            traceback.print_exc()
            print('[SimpleTimelineModel.loadCode] fail', code)

    # code : str
    # day : int | None(is last day)
    def _loadCode_Cls(self, code, day = None):
        self.code = code
        self.data.clear()
        try:
            if type(day) == 'str':
                day = day.replace('-', '')
                day = int(day)
            url = cls.ClsUrl()
            his5datas = url.loadHistory5FenShi(code)
            days = his5datas['date']
            if not day:
                day = days[-1]
            self.day = day
            if day not in days:
                return False
            isLast = days[-1] == day
            lines = his5datas['line']
            ONE_DAY_LINES = 241
            idx = days.index(day) * ONE_DAY_LINES
            self._calcCodePre(idx, lines)
            for i in range(idx, min(idx + ONE_DAY_LINES, len(lines))):
                d = lines[i]
                ts = datafile.ItemData()
                ts.time = url.getVal(d, 'minute', int, 0)
                ts.price = int(url.getVal(d, 'last_px', float, 0) * 100 + 0.5)
                ts.vol = url.getVal(d, 'business_amount', int, 0)
                ts.amount = url.getVal(d, 'business_balance', int, 0)
                ts.avgPrice = int(url.getVal(d, 'av_px', float, 0) * 100 + 0.5)
                self.data.append(ts)
        except Exception as e:
            traceback.print_exc()
            print('[SimpleTimelineModel.loadCode] fail', code)
            return False
        return True

    # 最新一天的指数分时
    def _loadCode_Ths_Newest(self, code):
        self.code = code
        try:
            hx = henxin.HexinUrl()
            data = hx.loadUrlData( hx.getFenShiUrl(code))
            lastDay = int(data['date'])
            self.day = lastDay
            self.pre = int(data['pre'] * 100 + 0.5)
            for d in data['dataArr']:
                ts = datafile.ItemData()
                ts.time = d['time']
                ts.price = int(d['price'] * 100 + 0.5)
                ts.vol = int(d['vol'])
                ts.amount = int(d['money'])
                self.data.append(ts)
        except Exception as e:
            traceback.print_exc()
            print('[SimpleTimelineModel.loadCode_ZS] fail', code)

    def loadLocal(self, code, day):
        if len(code) == 8:
            code = code[2 : ]
        if code[0] not in ('0', '3', '6'):
            return
        if not self.localData or self.localData.code != code:
            self.localData = datafile.DataFile(code, datafile.DataFile.DT_MINLINE, datafile.DataFile.FLAG_ALL)
        if not self.localData:
            return
        if type(day) == str:
            day = int(day.replace('-', ''))
        idx = self.localData.getItemIdx(day)
        if idx < 0:
            return
        if idx > 0:
            self.pre = self.localData.data[idx - 1].close
        else:
            self.pre = self.localData.data[idx].open
        while idx < len(self.localData.data):
            dt = self.localData.data[idx]
            if dt.day == day:
                self.data.append(dt)
                dt.price = dt.close
                idx += 1
            else:
                break

    def load(self, code, day = None):
        if type(code) == int:
            code = f'{code :06d}'
        if not code:
            return
        if code[0] == '8':
            self._loadCode_Ths_Newest(code)
            obj = ths_orm.THS_ZS_ZD.select(ths_orm.THS_ZS_ZD.name.distinct()).where(ths_orm.THS_ZS_ZD.code == code).scalar()
            self.name = obj
        else:
            if not self._loadCode_Cls(code, day):
                self.loadLocal(code, day)
            obj = ths_orm.THS_GNTC.select(ths_orm.THS_GNTC.name.distinct()).where(ths_orm.THS_GNTC.code == code).scalar()
            self.name = obj

    def getPriceRange(self):
        if not self.data:
            return None
        if self.priceRange:
            return self.priceRange
        minPrice = maxPrice = 0
        for dt in self.data:
            if minPrice == 0:
                minPrice = dt.price
                maxPrice = dt.price
            else:
                minPrice = min(minPrice, dt.price)
                maxPrice = max(maxPrice, dt.price)
        maxPrice = max(self.pre, maxPrice)
        minPrice = min(self.pre, minPrice)
        ds = max(abs(maxPrice - self.pre), abs(minPrice - self.pre))
        maxPrice = self.pre + ds
        minPrice = self.pre - ds
        self.priceRange = (minPrice, maxPrice)
        return self.priceRange
    
    def getVolRange(self):
        if not self.data:
            return None
        if self.volRange:
            return self.volRange
        minVol = maxVol = 0
        for dt in self.data:
            if dt.vol <= 0:
                continue
            if minVol == 0:
                minVol = dt.vol
                maxVol = dt.vol
            else:
                minVol = min(minVol, dt.vol)
                maxVol = max(maxVol, dt.vol)
        self.volRange = (0, maxVol)
        return self.volRange
    
    def getAmountRange(self):
        if not self.data:
            return None
        if self.amountRange:
            return self.amountRange
        minVol = maxVol = 0
        for dt in self.data:
            if dt.amount <= 0:
                continue
            if minVol == 0:
                minVol = dt.amount
                maxVol = dt.amount
            else:
                minVol = min(minVol, dt.amount)
                maxVol = max(maxVol, dt.amount)
        self.amountRange = (0, maxVol)
        return self.amountRange

class SimpleTimelineWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.model = None
        self.mouseXY = None
        self.paddings = (45, 10, 60, 30)
        self.volHeight = 160
        self.volSpace = 20

    def load(self, code, day = None):
        self.priceRange = None
        self.model = SimpleTimelineModel()
        self.model.load(code, day)
        self.invalidWindow()
        title = f'{self.model.code}   {self.model.name}'
        win32gui.SetWindowText(self.hwnd, title)

    def getYAtPrice(self, price, h):
        priceRange = self.model.getPriceRange()
        if not priceRange:
            return 0
        h -= self.paddings[1] + self.paddings[3] + self.volHeight + self.volSpace
        p = (price - priceRange[0]) / (priceRange[1] - priceRange[0])
        y = h - int(p * h) + self.paddings[1]
        return y
    
    def getYAtVol(self, vol, h):
        h -= self.paddings[3]
        volRange = self.model.getVolRange()
        if not volRange or volRange[0] == volRange[1]:
            return h
        p = (vol - volRange[0]) / (volRange[1] - volRange[0])
        y = h - int(p * self.volHeight)
        return y

    def getXAtMinuteIdx(self, minuteIdx, w):
        ow = w
        w -= self.paddings[0] + self.paddings[2]
        ONE_DAY_LINES = 240
        p = w / ONE_DAY_LINES
        if minuteIdx == ONE_DAY_LINES:
            return ow - self.paddings[2]
        return int(minuteIdx * p) + self.paddings[0]

    def getPriceAtY(self, y, h):
        sy = self.paddings[1]
        ey = h - self.paddings[3] - self.volHeight - self.volSpace
        if y <= sy or y >= ey:
            return None
        H = ey - sy
        y -= sy
        pr = self.model.getPriceRange()
        if not pr or pr[0] == pr[1]:
            return None
        p = pr[1] - (y / H) * (pr[1] - pr[0])
        return p

    def getMinuteIdxAtX(self, x, w):
        if x < self.paddings[0]:
            x = self.paddings[0]
        elif x > w - self.paddings[2]:
            x = w - self.paddings[2]
        x -= self.paddings[0]
        cw = w - self.paddings[0] - self.paddings[2]
        ONE_DAY_LINES = 240
        p = cw / ONE_DAY_LINES
        x += p / 2
        idx = int(x / p)
        if idx >= len(self.model.data):
            idx = len(self.model.data) - 1
        return idx

    def formatAmount(self, amount):
        if amount >= 100000000:
            amount /= 100000000
            return f'{amount :.2f}亿'
        amount //= 10000
        return f'{amount}万'

    def drawBackground(self, hdc):
        if not self.model:
            return
        # draw horizontal line
        pr = self.model.getPriceRange()
        if not pr:
            return
        ph = (pr[1] - pr[0]) / 4
        ps = (pr[1], pr[1] - ph, self.model.pre, self.model.pre - ph, pr[0])
        W, H = self.getClientSize()
        for i, price in enumerate(ps):
            y = self.getYAtPrice(price, H)
            style = win32con.PS_SOLID if i % 2 == 0 else win32con.PS_DOT
            psWidth = 2 if i == 2 else 1
            lc = 0x36332E
            self.drawer.drawLine(hdc, self.paddings[0], y, W - self.paddings[2], y, lc, style = style, width = psWidth)
            #p1 = f'{price / 100 :.02f}'
            color = 0x0000ff if price >= self.model.pre else 0x00ff00
            #rc = (self.leftPriceRect[0], y - 8, self.leftPriceRect[2]- 5, y + 8)
            #self.drawer.drawText(hdc, p1, rc, color, align=win32con.DT_RIGHT)
            zf = (price - self.model.pre) / self.model.pre * 100
            p2 = f'{zf :.02f}%'
            rc = (W - self.paddings[2] + 5, y - 8, W, y + 8)
            self.drawer.drawText(hdc, p2, rc, color, align = win32con.DT_LEFT)
        y = H - self.paddings[3] + 1
        self.drawer.drawLine(hdc, self.paddings[0], y, W - self.paddings[2], y, 0x36332E, style = style, width = 1)

        # draw vol lines
        am = self.model.getAmountRange()
        y = H - self.paddings[3] - self.volHeight
        self.drawer.drawLine(hdc, self.paddings[0], y, W - self.paddings[2], y, 0x36332E, style = style, width = 2)
        rc = (W - self.paddings[2] + 5, y - 8, W, y + 8)
        self.drawer.drawText(hdc, self.formatAmount(am[1]), rc, 0x993322, align = win32con.DT_LEFT)
        y = H - self.paddings[3] - self.volHeight // 2
        self.drawer.drawLine(hdc, self.paddings[0], y, W - self.paddings[2], y, 0x36332E, style = win32con.PS_DOT)
        rc = (W - self.paddings[2] + 5, y - 8, W, y + 8)
        self.drawer.drawText(hdc, self.formatAmount(am[1] / 2), rc, 0x993322, align = win32con.DT_LEFT)
        # draw vertical line
        for i in range(9):
            idx = i * 30
            x = self.getXAtMinuteIdx(idx, W)
            style = win32con.PS_SOLID if i % 4 == 0 else win32con.PS_DOT
            ds = 0 if i == 0 or i == 8 else self.volHeight
            self.drawer.drawLine(hdc, x, self.paddings[1], x, H - self.paddings[3], 0x36332E, style)
            rc = (x - 20, H - self.paddings[3], x + 20, H - self.paddings[3] + 20)
        # draw space
        ey = H - self.paddings[3] - self.volHeight
        rc = (self.paddings[0], ey - self.volSpace + 1, W - self.paddings[2], ey - 1)
        self.drawer.fillRect(hdc, rc, self.drawer.darkness(self.css['bgColor']))

    def drawMouse(self, hdc):
        if not self.mouseXY or not self.model:
            return
        W, H = self.getClientSize()
        x, y = self.mouseXY
        idx = self.getMinuteIdxAtX(x, W)
        if idx < 0:
            return
        # vertical line
        x = self.getXAtMinuteIdx(idx, W)
        self.drawer.drawLine(hdc, x, self.paddings[1], x, H - self.paddings[3], 0x905090, style = win32con.PS_DOT)
        md = self.model.data[idx]
        tips = f'{self.formatAmount(md.amount)}元'
        ty = H - self.paddings[3] + 5
        rc = (x - 50, ty, x + 50, H)
        self.drawer.drawText(hdc, tips, rc, 0xf06050)
        # horizontal line
        price = self.getPriceAtY(y, H)
        if not price:
            return
        zf = (price - self.model.pre) / self.model.pre * 100
        self.drawer.drawLine(hdc, self.paddings[0], y, W - self.paddings[2], y, 0x905090, style = win32con.PS_DOT)
        rc = (W - self.paddings[2] + 2, y - 10, W, y + 10)
        self.drawer.fillRect(hdc, rc, self.css['bgColor'])
        self.drawer.drawText(hdc, f'{zf :.2f}%', rc, 0xf06050, win32con.DT_VCENTER | win32con.DT_SINGLELINE | win32con.DT_LEFT)


    def drawMinites(self, hdc):
        if not self.model.data:
            return
        W, H = self.getClientSize()
        self.drawer.use(hdc, self.drawer.getPen(0xffffff))
        for i, md in enumerate(self.model.data):
            x = self.getXAtMinuteIdx(i, W)
            y = self.getYAtPrice(md.price, H)
            if i == 0:
                win32gui.MoveToEx(hdc, x, y)
            else:
                win32gui.LineTo(hdc, x, y)
        first = self.model.data[0]
        if not hasattr(first, 'avgPrice'):
            return
        self.drawer.use(hdc, self.drawer.getPen(0x00ffff))
        for i, md in enumerate(self.model.data):
            x = self.getXAtMinuteIdx(i, W)
            y = self.getYAtPrice(md.avgPrice, H)
            if i == 0:
                win32gui.MoveToEx(hdc, x, y)
            else:
                win32gui.LineTo(hdc, x, y)

    def _getVolLineColor(self, idx):
        now = self.model.data[idx].price
        if idx == 0:
            pre = self.model.pre
        else:
            pre = self.model.data[idx - 1].price
        if now > pre:
            return 0x0000dd
        if now == pre:
            return 0xdddddd
        return 0x00dd00

    def drawVol(self, hdc):
        W, H = self.getClientSize()
        for i, md in enumerate(self.model.data):
            x = self.getXAtMinuteIdx(i, W)
            y = self.getYAtVol(md.vol, H)
            self.drawer.use(hdc, self.drawer.getPen(self._getVolLineColor(i)))
            win32gui.MoveToEx(hdc, x, H - self.paddings[3])
            win32gui.LineTo(hdc, x, y)

    def onDraw(self, hdc):
        if not self.model:
            return
        self.drawBackground(hdc)
        self.drawMouse(hdc)
        self.drawMinites(hdc)
        self.drawVol(hdc)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_MOUSEMOVE:
            y, x = (lParam >> 16) & 0xffff,(lParam & 0xffff)
            self.mouseXY = (x, y)
            if self.model:
                win32gui.InvalidateRect(hwnd, None, True)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)
    
if __name__ == '__main__':
    win = SimpleTimelineWindow()
    win.createWindow(None, (100, 100, 1200, 600), win32con.WS_OVERLAPPEDWINDOW)
    win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)
    #win.load('002085', None)
    win.load('sh000001') # cls82437 sh000001
    win32gui.PumpMessages()