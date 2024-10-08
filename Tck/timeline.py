from win32.lib.win32con import WS_CHILD, WS_VISIBLE
import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, traceback
import os, sys, requests
import win32gui, win32con

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, cls
from Common import base_win, ext_win
from db import ths_orm
from Tck import fx

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
                ts.close = ts.price = int(url.getVal(d, 'last_px', float, 0) * 100 + 0.5)
                ts.vol = url.getVal(d, 'business_amount', int, 0)
                ts.amount = url.getVal(d, 'business_balance', int, 0)
                ts.avgPrice = int(url.getVal(d, 'av_px', float, 0) * 100 + 0.5)
                ts.day = url.getVal(d, 'date', int, 0)
                self.data.append(ts)
        except Exception as e:
            traceback.print_exc()
            print('[SimpleTimelineModel.loadCode] fail', code)
            return False
        return True

    # 最新一天的指数分时
    def loadCode_Ths_Newest(self, code, day):
        self.code = code
        self.data.clear()
        try:
            if type(day) == 'str':
                day = day.replace('-', '')
                day = int(day)
            hx = henxin.HexinUrl()
            data = hx.loadUrlData( hx.getFenShiUrl(code))
            lastDay = int(data['date'])
            self.name = data['name']
            if day and day != lastDay:
                return False
            self.day = lastDay
            self.pre = int(data['pre'] * 100 + 0.5)
            for d in data['dataArr']:
                ts = datafile.ItemData()
                ts.time = d['time']
                ts.close = ts.price = int(d['price'] * 100 + 0.5)
                ts.vol = int(d['vol'])
                ts.amount = int(d['money'])
                ts.day = lastDay
                self.data.append(ts)
            return True
        except Exception as e:
            traceback.print_exc()
            print('[SimpleTimelineModel.loadCode_ZS] fail', code)
        return False

    def loadLocal(self, code, day):
        if len(code) == 8:
            code = code[2 : ]
        if code[0] not in ('0', '3', '6'):
            return
        if not self.localData or self.localData.code != code:
            self.localData = datafile.DataFile(code, datafile.DataFile.DT_MINLINE)
            self.localData.loadData(datafile.DataFile.FLAG_ALL)
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
        if code[0] in ('0', '3', '6', '8'):
            if not self.loadCode_Ths_Newest(code, day):
                self.loadLocal(code, day)
        else:
            if not self._loadCode_Cls(code, day):
                self.loadLocal(code, day)
            #obj = ths_orm.THS_ZS_ZD.select(ths_orm.THS_ZS_ZD.name.distinct()).where(ths_orm.THS_ZS_ZD.code == code).scalar()
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
        self.hilights = []

    def load(self, code, day = None):
        self.priceRange = None
        self.model = SimpleTimelineModel()
        self.model.load(code, day)
        self.initHilights(code, day)
        self.invalidWindow()
        title = f'{self.model.code}   {self.model.name}'
        win32gui.SetWindowText(self.hwnd, title)

    def initHilights(self, code, day):
        self.hilights.clear()
        if not day:
            return
        fxc = fx.FenXiCode(code)
        fxc.loadFile()
        fxc.calcOneDay(day)
        for x in fxc.results:
            self.addHilight(x['fromMinute'], x['endMinute'], x)

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

    def minuteToIdx(self, minute):
        if minute <= 930:
            return 0
        hour = minute // 100
        minute = minute % 100
        ds = 0
        if hour <= 11:
            ds = 60 * (hour - 9) + minute - 30
            return ds
        ds = 120
        ds += minute + (hour - 13) * 60
        return ds

    def drawHilight(self, hdc):
        if not self.model:
            return
        sdc = win32gui.SaveDC(hdc)
        W, H = self.getClientSize()
        vsy = H - self.paddings[3] - self.volHeight
        for fe in self.hilights:
            f, e, info = fe
            sx = self.getXAtMinuteIdx(self.minuteToIdx(f), W)
            ex = self.getXAtMinuteIdx(self.minuteToIdx(e), W)
            psy = self.paddings[1]
            pey = vsy - self.volSpace
            self.drawer.fillRect(hdc, (sx, psy + 1, ex + 1, pey), 0x101010)
            vey = H - self.paddings[3]
            self.drawer.fillRect(hdc, (sx, vsy + 1, ex + 1, vey), 0x101010)
            txtRc = (sx, pey - 30, sx + 60, pey)
            text = f'{info["zf"] :.1f}% \n{info["max3MinutesAvgAmount"]}万'
            self.drawer.drawText(hdc, text, txtRc, color = 0xe0abce, align = win32con.DT_LEFT)
        win32gui.RestoreDC(hdc, sdc)
            
    def addHilight(self, fromMinute, endMinute, info):
        fe = (fromMinute, endMinute, info)
        self.hilights.append(fe)

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
            idx = self.minuteToIdx(md.time)
            x = self.getXAtMinuteIdx(idx, W)
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
            idx = self.minuteToIdx(md.time)
            x = self.getXAtMinuteIdx(idx, W)
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
            idx = self.minuteToIdx(md.time)
            x = self.getXAtMinuteIdx(idx, W)
            y = self.getYAtVol(md.vol, H)
            self.drawer.use(hdc, self.drawer.getPen(self._getVolLineColor(i)))
            win32gui.MoveToEx(hdc, x, H - self.paddings[3])
            win32gui.LineTo(hdc, x, y)

    def onDraw(self, hdc):
        if not self.model:
            return
        self.drawHilight(hdc)
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

class PanKouWindow(ext_win.CellRenderWindow):
    def __init__(self) -> None:
        super().__init__(('1fr', '2fr', '2fr'))
        self.data = None
        VCENTER = win32con.DT_VCENTER | win32con.DT_SINGLELINE
        CENTER = VCENTER | win32con.DT_CENTER
        for i in range(5):
            self.addRow({'height': 25, 'margin': 0, 'name': 'sell', 'val': 5 - i}, {'text': str(5 - i), 'color': 0xc0c0c0, 'textAlign': CENTER, 'fontSize': 16}, self.getCell, self.getCell)
        self.addRow({'height': 2, 'bgColor': 0x2020a0})
        for i in range(5):
            self.addRow({'height': 25, 'margin': 0, 'name': 'buy', 'val': i + 1}, {'text': str(i + 1), 'color': 0xc0c0c0, 'textAlign': CENTER, 'fontSize': 16}, self.getCell, self.getCell)

    def getCell(self, rowInfo, cellIdx):
        if not self.data:
            return None
        k = rowInfo['name'][0]
        i = rowInfo['val']
        px = self.data.get(f'{k}_px_{i}', 0)
        amount = self.data.get(f'{k}_amount_{i}', 0)
        amount *= px * 100
        cx = {'textAlign': win32con.DT_VCENTER | win32con.DT_SINGLELINE}

        if cellIdx == 1:
            ipx = int(px * 100 + 0.5)
            if ipx > 0:
                cx['text'] = f'{ipx // 100}.{ipx % 100}'
            
            pre = self.data.get('preclose_px', 0)
            cx['color'] = 0x0000ff if px >= pre else 0x00ff00
        elif cellIdx == 2:
            cx['color'] = 0xF4E202
            if amount >= 100000000:
                cx['text'] = f'{amount / 100000000 :.2f}亿'
            elif amount > 0:
                cx['text'] = f'{amount / 10000 :.1f}万'
            else:
                cx['text'] = ''
        return cx

    def getVolCell(self, rowInfo, cellIdx):
        if not self.data:
            return None
        k = rowInfo['name'][0]
        i = rowInfo['val']
        px = self.data.get(f'{k}_px_{i}', 0)
        
        cx = {}
        pre = self.data.get('preclose_px', 0)
        cx['color'] = 0x0000ff if px >= pre else 0x00ff00
        ipx = int(px * 100 + 0.5)
        cx['text'] = f'{ipx // 100}.{ipx % 100}'
        return cx

    def createWindow(self, parentWnd, rect, style= win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)

    def load(self, code):
        url = cls.ClsUrl()
        self.data = url.loadPanKou5(code)
        self.invalidWindow()

class TimelinePanKouWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.timelineWin = None
        self.pankouWin = None
        self.css['bgColor'] = 0x202020
    
    def createWindow(self, parentWnd, rect, style= win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.layout = base_win.GridLayout(('1fr', ), ('1fr', 200), (5, 5))
        self.timelineWin = SimpleTimelineWindow()
        self.timelineWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.pankouWin = PanKouWindow()
        self.pankouWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.layout.setContent(0, 0, self.timelineWin)
        self.layout.setContent(0, 1, self.pankouWin)
        win32gui.PostMessage(self.hwnd, win32con.WM_SIZE, 0, 0)

    def load(self, code, day = None):
        self.timelineWin.load(code, day)
        self.pankouWin.load(code)

if __name__ == '__main__':
    win = TimelinePanKouWindow()
    win.createWindow(None, (0, 0, 1000, 600), win32con.WS_OVERLAPPEDWINDOW)
    win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)
    #win.load('002085', None)
    win.load('300390') # cls82437 sh000001 ; 300390  600611
    win32gui.PumpMessages()