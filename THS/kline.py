import os, sys
import win32gui, win32con
import requests

cwd = os.getcwd()
w = cwd.index('GP')
cwd = cwd[0 : w + 2]
sys.path.append(cwd)
from THS import base_win
from Tdx import datafile
from THS.download import henxin

class KLineModel_Tdx(datafile.DataFile):
    def __init__(self, code):
        super().__init__(code, datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL)

    def setDataRange(fromIdx, endIdx):
        pass

class KLineModel_Ths(henxin.ThsDataFile):
    def __init__(self, code) -> None:
        super().__init__(code, datafile.DataFile.DT_DAY)

class KLineWindow(base_win.BaseWindow):
    FLAG_SHOW_AMOUNT = 1
    FLAG_SHOW_RATE = 2
    MONEY_RATE_HEIGHT = 120 # 显示高度
    LEFT_MARGIN, RIGHT_MARGIN = 0, 70

    def __init__(self, flags = FLAG_SHOW_AMOUNT | FLAG_SHOW_RATE):
        super().__init__()
        self.model = None
        self.klineWidth = 6 # K线宽度
        self.klineSpace = 2 # K线之间的间距离
        self.visibleRange = None # K线显示范围
        self.priceRange = None # 价格显示范围
        self.selIdx = -1
        self.mouseXY = None
        self.flags = flags
        self.rateRange = None
        self.amountRange = None

    def getKLineRect(self):
        rect = self.getRect()
        h = self.MONEY_RATE_HEIGHT if self.flags & self.FLAG_SHOW_AMOUNT else 0
        h += self.MONEY_RATE_HEIGHT if self.flags & self.FLAG_SHOW_RATE else 0
        TOP_MARGIN, BOTTOM_MARGIN = 30, 0
        return [self.LEFT_MARGIN, TOP_MARGIN, rect[2] - self.LEFT_MARGIN - self.RIGHT_MARGIN, rect[3] - TOP_MARGIN - BOTTOM_MARGIN - h]

    def getAmountRect(self):
        if not (self.flags & self.FLAG_SHOW_AMOUNT):
            return [0, 0, 0, 0]
        *_, w, h = self.getRect()
        MARGIN_TOP = 20
        return [self.LEFT_MARGIN, h - self.MONEY_RATE_HEIGHT + MARGIN_TOP, w - self.LEFT_MARGIN - self.RIGHT_MARGIN, self.MONEY_RATE_HEIGHT - MARGIN_TOP]
    
    def getRateRect(self):
        if not (self.flags & self.FLAG_SHOW_RATE):
            return [0, 0, 0, 0]
        *_, w, h = self.getRect()
        mr = self.getAmountRect()
        MARGIN_TOP = 20
        return [self.LEFT_MARGIN, h - mr[3] - self.MONEY_RATE_HEIGHT, mr[2], self.MONEY_RATE_HEIGHT - MARGIN_TOP]

    def setModel(self, model):
        self.model = model
        self.visibleRange = None
        self.priceRange = None
        if not model:
            return
        self.model.calcMA(5)
        self.model.calcMA(10)
        self.model.calcZDT()
        self.model.calcZhangFu()

    # @return True: 已处理事件,  False:未处理事件
    def winProc(self, hwnd, msg, wParam, lParam):
        rt = super().winProc(hwnd, msg, wParam, lParam)
        if rt: return True
        if msg == win32con.WM_SIZE:
            self.makeVisible(self.selIdx)
            return True
        if msg == win32con.WM_MOUSEMOVE:
            self.onMouseMove(lParam & 0xffff, (lParam >> 16) & 0xffff)
            return True
        if msg == win32con.WM_KEYDOWN:
            oem = lParam >> 16 & 0xff
            self.onKeyDown(oem)
            return True
        return False

    def updateAttr(self, attrName, attrVal):
        if attrName == 'selIdx':
            self.selIdx = attrVal
            data = self.model.data[attrVal] if attrVal >= 0 else None
            self.notifyListener('selIdx.changed', {'selIdx': attrVal, 'data': data})
            win32gui.InvalidateRect(self.hwnd, None, True)

    def onMouseMove(self, x, y):
        self.mouseXY = (x, y)
        si = self.getIdxAtX(x)
        if self.selIdx != si:
            self.updateAttr('selIdx', si)
        win32gui.InvalidateRect(self.hwnd, None, True)
        #print('[onMouseMove] price=', self.getPriceAtY(y))

    def setSelIdx(self, idx):
        if not self.visibleRange or idx < 0 or idx >= self.visibleRange[1]:
            return
        data = self.model.data[idx]
        x = self.getCenterX(idx)
        y = self.getYAtKLinePrice(data.close)
        self.mouseXY = (x, y)
        self.updateAttr('selIdx', idx)

    def onKeyDown(self, oem):
        if oem == 73: # page up
            pass
        elif oem == 81: # page down
            pass
        elif oem == 75: # left arrow key
            if self.selIdx > 0:
                ni = self.selIdx - 1
                self.setSelIdx(ni)
        elif oem == 77: # right arrow key
            if self.visibleRange and self.selIdx < self.visibleRange[1] - 1:
                ni = self.selIdx + 1
                self.setSelIdx(ni)
        elif oem == 72: # up arrow key
            self.klineWidth += 2
            if self.selIdx >= 0:
                self.makeVisible(self.selIdx)
                x = self.getCenterX(self.selIdx)
                self.mouseXY = (x, self.mouseXY[1])
            win32gui.InvalidateRect(self.hwnd, None, True)
        elif oem == 80: # down arrow key
            self.klineWidth = max(self.klineWidth - 2, 2)
            if self.selIdx >= 0:
                self.makeVisible(self.selIdx)
                x = self.getCenterX(self.selIdx)
                self.mouseXY = (x, self.mouseXY[1])
            win32gui.InvalidateRect(self.hwnd, None, True)

    # 可见K线的数量
    def getVisibleKLineNum(self):
        *_, w, h = self.getRect()
        w = self.getKLineRect()[2]
        return w // (self.klineWidth + self.klineSpace)

    def calcVisibleRange(self, idx):
        self.visibleRange = None
        num = self.getVisibleKLineNum()
        if idx < 0 or idx >= len(self.model.data):
            self.visibleRange = (max(len(self.model.data) - num, 0), len(self.model.data))
            return
        RIGHT_NUM = num // 2
        endIdx = min(idx + RIGHT_NUM, len(self.model.data))
        leftNum = num - (endIdx - idx + 1)
        fromIdx = max(idx - leftNum, 0)
        self.visibleRange = (fromIdx, endIdx)

    # 必须先计算visibleRange
    def calcPriceRange(self):
        self.priceRange = None
        if not self.visibleRange:
            return None
        maxVal = minVal = 0
        for i in range(*self.visibleRange):
            d = self.model.data[i]
            if maxVal == 0:
                maxVal = d.high
                minVal = d.low
                continue
            maxVal = max(maxVal, d.high)
            minVal = min(minVal, d.low)
        self.priceRange = (minVal, maxVal)

    def makeVisible(self, idx):
        self.calcVisibleRange(idx)
        self.calcPriceRange()
        self.calcRateRange()
        self.calcAmountRange()
        win32gui.InvalidateRect(self.hwnd, None, True)
    
    def getYAtKLinePrice(self, price):
        if not self.priceRange:
            return 0
        if price < self.priceRange[0] or price > self.priceRange[1]:
            return 0
        p = (price - self.priceRange[0]) / (self.priceRange[1] - self.priceRange[0])
        rect = self.getKLineRect()
        H = rect[3]
        y = H - int(p * H)
        return y + rect[1]
    
    def getYAtAmount(self, amount):
        rect = self.getAmountRect()
        if not self.amountRange:
            return rect[1]
        if amount < self.amountRange[0] or amount > self.amountRange[1]:
            return rect[1]
        p = (amount - self.amountRange[0]) / (self.amountRange[1] - self.amountRange[0])
        H = rect[3]
        y = H - int(p * H)
        return y + rect[1]
    
    def getYAtRate(self, rate):
        rect = self.getRateRect()
        if not self.rateRange:
            return rect[1]
        if rate < self.rateRange[0] or rate > self.rateRange[1]:
            return rect[1]
        p = (rate - self.rateRange[0]) / (self.rateRange[1] - self.rateRange[0])
        H = rect[3]
        y = H - int(p * H)
        return y + rect[1]

    # return {value:, fmtVal: valType: 'Price' | 'Rate' | 'Amount'}
    def getValueAtY(self, y):
        if y <= 0:
            return None
        rect = self.getKLineRect()
        if y >= 0 and y <= rect[1] + rect[3] and self.priceRange: # in kline-view
            m = (self.priceRange[1] - self.priceRange[0]) / rect[3]
            y -= rect[1]
            val = int(self.priceRange[1] - y * m)
            return {'value': val, 'fmtVal': f'{val // 100}.{val % 100 :02d}', 'valType': 'Price'}
        rect = self.getRateRect()
        if y >= rect[1] and y <= rect[1] + rect[3] and self.rateRange: # in rate-view
            y -= rect[1]
            rr = self.rateRange
            m = (rr[1] - rr[0]) / rect[3]
            val = int(rr[1] - y * m)
            return {'value': val, 'fmtVal': f'{val :.1f}%', 'valType': 'Rate'}
        rect = self.getAmountRect()
        if y >= rect[1] and y <= rect[1] + rect[3] and self.amountRange: # in money-view
            y -= rect[1]
            rr = self.amountRange
            m = (rr[1] - rr[0]) / rect[3]
            val = int(rr[1] - y * m)
            return {'value': val, 'fmtVal': f'{val / 100000000 :.1f}亿', 'valType': 'Amount'}
        return None
        
    def calcRateRange(self):
        self.rateRange = None
        if not self.visibleRange:
            return
        maxVal = minVal = 0
        for i in range(*self.visibleRange):
            d = self.model.data[i]
            if maxVal == 0:
                maxVal = d.rate
                minVal = d.rate
                continue
            maxVal = max(maxVal, d.rate)
            minVal = min(minVal, d.rate)
        self.rateRange = (minVal, maxVal)

    def calcAmountRange(self):
        self.amountRange = None
        if not self.visibleRange:
            return
        maxVal = minVal = 0
        for i in range(*self.visibleRange):
            d = self.model.data[i]
            if maxVal == 0:
                maxVal = d.amount
                minVal = d.amount
                continue
            maxVal = max(maxVal, d.amount)
            minVal = min(minVal, d.amount)
        self.amountRange = (minVal, maxVal)

    def getCenterX(self, idx):
        if not self.visibleRange:
            return -1
        if idx < self.visibleRange[0] or idx > self.visibleRange[1]:
            return -1
        rect = self.getKLineRect()
        i = idx - self.visibleRange[0]
        x = rect[0] + i * (self.klineWidth + self.klineSpace)
        x += self.klineWidth // 2
        return x

    def getIdxAtX(self, x):
        if not self.visibleRange:
            return -1
        rect = self.getKLineRect()
        if x <= rect[0] or x >= rect[0] + rect[2]:
            return -1
        x -= rect[0]
        idx = x // (self.klineWidth + self.klineSpace)
        idx += self.visibleRange[0]
        if idx >= len(self.model.data):
            return -1
        return idx

    def drawKLine(self, hdc, idx, pens, hbrs):
        data = self.model.data[idx]
        cx = self.getCenterX(idx)
        bx = cx - self.klineWidth // 2
        ex = bx + self.klineWidth
        rect = (bx, self.getYAtKLinePrice(data.open), ex, self.getYAtKLinePrice(data.close) + 1)
        color = self.getColor(idx, data)
        win32gui.SelectObject(hdc, pens[color])
        win32gui.MoveToEx(hdc, cx, self.getYAtKLinePrice(data.low))
        win32gui.LineTo(hdc, cx, self.getYAtKLinePrice(data.high))
        if data.close >= data.open:
            win32gui.SelectObject(hdc, hbrs['black'])
            win32gui.Rectangle(hdc, *rect)
        else:
            win32gui.FillRect(hdc, rect, hbrs[color])

    def drawSelTip(self, hdc, pens, hbrs):
        if self.selIdx < 0 or (not self.model) or (not self.model.data) or self.selIdx >= len(self.model.data):
            return
        sdc = win32gui.SaveDC(hdc)
        d = self.model.data[self.selIdx]
        txt = f'{self.model.code}\n{self.model.name}\n\n时间\n{d.day//10000}\n{d.day%10000:04d}\n\n涨幅\n{d.zhangFu:.2f}%\n\n成交额\n{d.amount/100000000:.02f}亿'
        if hasattr(d, 'rate'):
            txt += f'\n\n换手率\n{d.rate :.1f}%'
        rr = self.getKLineRect()
        rc = (0, 60, 60, 300)
        win32gui.SelectObject(hdc, hbrs['black'])
        win32gui.SelectObject(hdc, pens['red'])
        win32gui.Rectangle(hdc, *rc)
        win32gui.SetTextColor(hdc, 0xffffff)
        win32gui.DrawText(hdc, txt, len(txt), rc, win32con.DT_CENTER)
        win32gui.RestoreDC(hdc, sdc)

    def drawRateView(self, hdc, idx, pens, hbrs):
        data = self.model.data[idx]
        if not hasattr(data, 'rate') or not self.rateRange:
            return
        cx = self.getCenterX(idx)
        bx = cx - self.klineWidth // 2
        ex = bx + self.klineWidth
        rect = (bx, self.getYAtRate(self.rateRange[0]), ex, self.getYAtRate(data.rate) + 1)
        color = self.getZBColor(idx, data, self.FLAG_SHOW_RATE)
        win32gui.SelectObject(hdc, pens[color])
        if data.close >= data.open:
            win32gui.SelectObject(hdc, hbrs['black'])
            win32gui.Rectangle(hdc, *rect)
        else:
            win32gui.FillRect(hdc, rect, hbrs[color])

    def drawAmountView(self, hdc, idx, pens, hbrs):
        data = self.model.data[idx]
        if not hasattr(data, 'amount') or not self.amountRange:
            return
        cx = self.getCenterX(idx)
        bx = cx - self.klineWidth // 2
        ex = bx + self.klineWidth
        rect = (bx, self.getYAtAmount(self.amountRange[0]), ex, self.getYAtAmount(data.amount) + 1)
        color = self.getZBColor(idx, data, self.FLAG_SHOW_AMOUNT)
        win32gui.SelectObject(hdc, pens[color])
        if data.close >= data.open:
            win32gui.SelectObject(hdc, hbrs['black'])
            win32gui.Rectangle(hdc, *rect)
        else:
            win32gui.FillRect(hdc, rect, hbrs[color])

    def draw(self, hdc):
        if not self.visibleRange:
            return
        pens = {}
        hbrs = {}
        pens['white'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xffffff)
        pens['red'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x0000ff)
        pens['green'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ff00)
        pens['light_green'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xfcfc54)
        pens['blue'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xff0000)
        pens['yellow'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
        pens['0xff00ff'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xff00ff)

        hbrs['white'] = win32gui.CreateSolidBrush(0xffffff)
        hbrs['red'] = win32gui.CreateSolidBrush(0x0000ff)
        hbrs['green'] = win32gui.CreateSolidBrush(0x00ff00)
        hbrs['light_green'] = win32gui.CreateSolidBrush(0xfcfc54)
        hbrs['blue'] = win32gui.CreateSolidBrush(0xff0000)
        hbrs['yellow'] = win32gui.CreateSolidBrush(0x00ffff)
        hbrs['black'] = win32gui.CreateSolidBrush(0x000000)
        hbrs['0xff00ff'] = win32gui.CreateSolidBrush(0xff00ff)
        
        fs = (self.drawKLine, self.drawRateView, self.drawAmountView)
        for i in range(*self.visibleRange):
            for ff in fs:
                sdc = win32gui.SaveDC(hdc)
                ff(hdc, i, pens, hbrs)
                win32gui.RestoreDC(hdc, sdc)
        self.drawMA(hdc, 5)
        self.drawMA(hdc, 10)
        self.drawMouse(hdc, pens)
        self.drawMarkLines(hdc, pens, hbrs)
        self.drawSelTip(hdc, pens, hbrs)

        if self.mouseXY:
            self.drawTipPrice(hdc, self.mouseXY[1], pens, hbrs)
        for k in pens:
            win32gui.DeleteObject(pens[k])
        for k in hbrs:
            win32gui.DeleteObject(hbrs[k])

    def drawMA(self, hdc, n):
        if n == 5:
            pen = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
            win32gui.SelectObject(hdc, pen)
        elif n == 10:
            pen = win32gui.CreatePen(win32con.PS_SOLID, 2, 0xee00ee)
            win32gui.SelectObject(hdc, pen)
        bi = self.visibleRange[0]

        ma = f'MA{n}'
        moveToFlag = False
        for i in range(bi, self.visibleRange[1]):
            if not moveToFlag:
                mx = getattr(self.model.data[bi], ma, 0)
                if mx > 0:
                    win32gui.MoveToEx(hdc, self.getCenterX(bi), self.getYAtKLinePrice(mx))
                    moveToFlag = True
                continue
            win32gui.LineTo(hdc, self.getCenterX(i), self.getYAtKLinePrice(getattr(self.model.data[i], ma)))
        win32gui.DeleteObject(pen)

    def drawMouse(self, hdc, pens):
        if not self.mouseXY:
            return
        x, y = self.mouseXY
        *_, w, h = self.getRect()
        wp = win32gui.CreatePen(win32con.PS_DASH, 1, 0xffffff)
        win32gui.SelectObject(hdc, wp)
        win32gui.MoveToEx(hdc, self.LEFT_MARGIN, y)
        win32gui.LineTo(hdc, w, y)
        win32gui.MoveToEx(hdc, x, 0)
        win32gui.LineTo(hdc, x, h)
        win32gui.DeleteObject(wp)

    def getColor(self, idx, data):
        if self.model.code[0 : 2] == '88' and idx > 0: # 指数
            zdfd = abs((self.model.data[idx].close - self.model.data[idx - 1].close) / self.model.data[idx - 1].close * 100)
            mdfd = abs((max(self.model.data[idx].high, self.model.data[idx - 1].close)- self.model.data[idx].low) / self.model.data[idx - 1].close * 100)
            if zdfd >= 3.5 or mdfd >= 3.5:
                return '0xff00ff'
        if getattr(data, 'tdb', False):
            return 'green'
        zdt = getattr(data, 'zdt', None)
        if zdt == 'ZT' or zdt == 'ZTZB':
            return 'blue'
        if zdt == 'DT' or zdt == 'DTZB':
            return 'yellow'
        if data.close >= data.open:
            return 'red'
        return 'light_green'

    # 指标
    def getZBColor(self, idx, data, flag):
        if idx > 0 and (flag & self.FLAG_SHOW_AMOUNT) and self.amountRange:
                rv = data.amount
                prv = self.model.data[idx - 1].amount
                if prv > 0 and rv / prv >= 2: # 倍量
                    return 'blue'
        if data.close >= data.open:
            return 'red'
        return 'light_green'

    def drawTipPrice(self, hdc, y, pens, hbrs):
        if not self.priceRange:
            return
        val = self.getValueAtY(y)
        if not val:
            return
        win32gui.SetTextColor(hdc, 0x0000ff)
        w = self.getRect()[2]
        H = 16
        rc = (w - 50, y - H // 2, w, y + H // 2)
        hb = win32gui.CreateSolidBrush(0x800040)
        win32gui.FillRect(hdc, rc, hb)
        win32gui.DrawText(hdc, val['fmtVal'], len(val['fmtVal']), rc, win32con.DT_CENTER)
        win32gui.DeleteObject(hb)

    def drawMarkLines(self, hdc, pens, hbrs):
        sdc = win32gui.SaveDC(hdc)
        *_, w, h = self.getRect()
        dred = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x0000aa) # 暗红色
        dred2 = win32gui.CreatePen(win32con.PS_SOLID, 2, 0x0000aa) # 暗红色
        win32gui.SelectObject(hdc, dred)
        # 右边竖线
        win32gui.MoveToEx(hdc, w - self.RIGHT_MARGIN + 10, 0)
        win32gui.LineTo(hdc, w - self.RIGHT_MARGIN + 10, h)
        # KLine图下方的横线
        win32gui.SelectObject(hdc, dred2)
        klineRect = self.getKLineRect()
        y = klineRect[1] + klineRect[3] + 4
        win32gui.MoveToEx(hdc, 0, y)
        win32gui.LineTo(hdc, w, y)
        # Rate下方横线
        rateRect = self.getRateRect()
        if rateRect[3] > 0:
            win32gui.SelectObject(hdc, dred)
            y = rateRect[1] + rateRect[3] + 2
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, w, y)
        amountRect = self.getAmountRect()
        if amountRect[3] > 0:
            win32gui.SelectObject(hdc, dred)
            y = amountRect[1] + amountRect[3] + 2
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, w, y)

        win32gui.RestoreDC(hdc, sdc)
        win32gui.DeleteObject(dred)
        win32gui.DeleteObject(dred2)

if __name__ == '__main__':
    win = KLineWindow()
    rect = (0, 0, 1000, 500)
    win.createWindow(None, rect, win32con.WS_VISIBLE | win32con.WS_OVERLAPPEDWINDOW)
    hexinUrl = henxin.HexinUrl()
    model = KLineModel_Ths('002682')
    model.loadDataFile(hexinUrl)
    win.setModel(model)
    win.makeVisible(-1)
    win32gui.PumpMessages()