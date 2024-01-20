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

# 指标 Vol, Amount, Rate等
class Indicator:
    # config = {height: xx, width:xx, name:'', margins:(top, bottom), }
    def __init__(self, klineWin, config) -> None:
        self.klineWin = klineWin
        self.config = config
        self.data = None
        self.valueRange = None
        self.visibleRange = None
        self.width = 0
        self.height = 0

    def setData(self, model, data):
        self.model = model
        self.data = data

    def calcValueRange(self, fromIdx, endIdx):
        pass

    def getYAtValue(self, value):
        pass

    def getValueAtY(self, y):
        pass

    def getColor(self, idx, data):
        if data.close >= data.open:
            return 'red'
        return 'light_green'

    def draw(self, hdc, pens, hbrs):
        pass

    def getVisibleNum(self):
        return self.width // (self.klineWin.klineWidth + self.klineWin.klineSpace)
    
    def getMargins(self, idx):
        cf = self.config.get('margins', None)
        if cf and idx >= 0 and idx < len(cf):
            return cf[idx]
        return 0

    def getCenterX(self, idx):
        if not self.visibleRange:
            return -1
        if idx < self.visibleRange[0] or idx > self.visibleRange[1]:
            return -1
        i = idx - self.visibleRange[0]
        x = i * (self.klineWin.klineWidth + self.klineWin.klineSpace)
        x += self.klineWin.klineWidth // 2
        return x
    
    def getIdxAtX(self, x):
        if not self.visibleRange:
            return -1
        if x <= 0 or x >= self.width:
            return -1
        idx = x // (self.klineWin.klineWidth + self.klineWin.klineSpace)
        idx += self.visibleRange[0]
        if idx >= len(self.data):
            return -1
        return idx

    def calcVisibleRange(self, idx):
        self.visibleRange = None
        num = self.getVisibleNum()
        if idx < 0 or idx >= len(self.data):
            self.visibleRange = (max(len(self.data) - num, 0), len(self.data))
            return
        RIGHT_NUM = num // 2
        endIdx = min(idx + RIGHT_NUM, len(self.data))
        leftNum = num - (endIdx - idx + 1)
        fromIdx = max(idx - leftNum, 0)
        self.visibleRange = (fromIdx, endIdx)

class KLineIndicator(Indicator):
    def __init__(self, klineWin, config) -> None:
        super().__init__(klineWin, config)

    def calcValueRange(self, fromIdx, endIdx):
        self.valueRange = None
        maxVal = minVal = 0
        for i in range(fromIdx, endIdx):
            d = self.data[i]
            if maxVal == 0:
                maxVal = d.high
                minVal = d.low
            else:
                maxVal = max(maxVal, d.high)
                minVal = min(minVal, d.low)
        self.valueRange = (minVal, maxVal)

    def getYAtValue(self, value):
        if not self.valueRange:
            return 0
        if value < self.valueRange[0] or value > self.valueRange[1]:
            return 0
        p = (value - self.valueRange[0]) / (self.valueRange[1] - self.valueRange[0])
        H = self.height
        y = H - int(p * H)
        return y

    def getValueAtY(self, y):
        if not self.valueRange:
            return None
        m = (self.valueRange[1] - self.valueRange[0]) / self.height
        val = int(self.valueRange[1] - y * m)
        return {'value': val, 'fmtVal': f'{val // 100}.{val % 100 :02d}', 'valType': 'Price'}

    def getColor(self, idx, data):
        code = self.klineWin.model.code
        if code[0 : 2] == '88' and idx > 0: # 指数
            zdfd = abs((self.data[idx].close - self.data[idx - 1].close) / self.data[idx - 1].close * 100)
            mdfd = abs((max(self.data[idx].high, self.data[idx - 1].close)- self.data[idx].low) / self.data[idx - 1].close * 100)
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

    def draw(self, hdc, pens, hbrs):
        if not self.visibleRange:
            return
        self.drawBackground(hdc, pens, hbrs)
        for idx in range(*self.visibleRange):
            data = self.data[idx]
            cx = self.getCenterX(idx)
            bx = cx - self.klineWin.klineWidth // 2
            ex = bx + self.klineWin.klineWidth
            rect = (bx, self.getYAtValue(data.open), ex, self.getYAtValue(data.close) + 1)
            color = self.getColor(idx, data)
            win32gui.SelectObject(hdc, pens[color])
            win32gui.MoveToEx(hdc, cx, self.getYAtValue(data.low))
            win32gui.LineTo(hdc, cx, self.getYAtValue(data.high))
            if data.close >= data.open:
                win32gui.SelectObject(hdc, hbrs['black'])
                win32gui.Rectangle(hdc, *rect)
            else:
                win32gui.FillRect(hdc, rect, hbrs[color])
        self.drawMA(hdc, 5)
        self.drawMA(hdc, 10)

    def drawBackground(self, hdc, pens, hbrs):
        sdc = win32gui.SaveDC(hdc)
        win32gui.SelectObject(hdc, pens['bk_dot_red'])
        SP = self.height // 4
        for i in range(0, 4):
            y = SP * i
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, self.width, y)
            price = self.getValueAtY(y)
            if not price:
                continue
            price = price['fmtVal']
            win32gui.SetTextColor(hdc, 0xab34de)
            x = self.width + 20
            rt = (x, y - 8, x + 60, y + 8)
            win32gui.DrawText(hdc, price, len(price), rt, win32con.DT_LEFT)

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
                mx = getattr(self.data[bi], ma, 0)
                if mx > 0:
                    win32gui.MoveToEx(hdc, self.getCenterX(bi), self.getYAtValue(mx))
                    moveToFlag = True
                continue
            win32gui.LineTo(hdc, self.getCenterX(i), self.getYAtValue(getattr(self.data[i], ma)))
        win32gui.DeleteObject(pen)
    
class AmountIndicator(Indicator):
    def __init__(self, klineWin, config) -> None:
        super().__init__(klineWin, config)

    def calcValueRange(self, fromIdx, endIdx):
        self.valueRange = None
        if fromIdx < 0 or endIdx < 0:
            return
        maxVal = minVal = 0
        for i in range(fromIdx, endIdx):
            d = self.data[i]
            if maxVal == 0:
                maxVal = getattr(d, 'amount', 0)
                minVal = getattr(d, 'amount', 0)
            else:
                maxVal = max(maxVal, getattr(d, 'amount', 0))
                minVal = min(minVal, getattr(d, 'amount', 0))
        self.valueRange = (0, maxVal)

    def getYAtValue(self, value):
        if not self.valueRange or (not self.valueRange[1]):
            return 0
        if value < self.valueRange[0] or value > self.valueRange[1]:
            return 0
        p = (value - self.valueRange[0]) / self.valueRange[1]
        H = self.height
        y = H - int(p * H)
        return y

    def getValueAtY(self, y):
        rr = self.valueRange
        if not rr:
            return None
        m = (rr[1] - rr[0]) / self.height
        val = int(rr[1] - y * m)
        return {'value': val, 'fmtVal': f'{val / 100000000 :.1f}亿', 'valType': 'Amount'}
    
    def getColor(self, idx, data):
        if idx > 0:
            rv = data.amount
            prv = self.data[idx - 1].amount
            if prv > 0 and rv / prv >= 2: # 倍量
                return 'blue'
        return super().getColor(idx, data)

    def drawItem(self, idx, hdc, pens, hbrs):
        data = self.data[idx]
        if not hasattr(data, 'amount') or not self.valueRange:
            return
        cx = self.getCenterX(idx)
        bx = cx - self.klineWin.klineWidth // 2
        ex = bx + self.klineWin.klineWidth
        rect = (bx, self.getYAtValue(self.valueRange[0]), ex, self.getYAtValue(data.amount) + 1)
        color = self.getColor(idx, data)
        win32gui.SelectObject(hdc, pens[color])
        if data.close >= data.open:
            win32gui.SelectObject(hdc, hbrs['black'])
            win32gui.Rectangle(hdc, *rect)
        else:
            win32gui.FillRect(hdc, rect, hbrs[color])

    def draw(self, hdc, pens, hbrs):
        if not self.visibleRange:
            return
        self.drawBackground(hdc, pens, hbrs)
        for idx in range(*self.visibleRange):
            self.drawItem(idx, hdc, pens, hbrs)
        win32gui.SelectObject(hdc, pens['dark_red'])
        
        亿 = 100000000
        w = self.width
        if self.valueRange[1] >= 5 * 亿 and 5 * 亿  >= self.valueRange[0]:
            win32gui.SelectObject(hdc, pens['blue'])
            y = self.getYAtValue(5 * 亿)
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, w, y)
        if self.valueRange[1] >= 10 * 亿 and 10 * 亿  >= self.valueRange[0]:
            win32gui.SelectObject(hdc, pens['0xff00ff'])
            y = self.getYAtValue(10 * 亿)
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, w, y)
        if self.valueRange[1] >= 20 * 亿 and 20 * 亿  >= self.valueRange[0]:
            win32gui.SelectObject(hdc, pens['yellow'])
            y = self.getYAtValue(20 * 亿)
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, w, y)

    def drawBackground(self, hdc, pens, hbrs):
        sdc = win32gui.SaveDC(hdc)
        win32gui.SelectObject(hdc, pens['bk_dot_red'])
        y = self.getYAtValue(self.valueRange[1])
        win32gui.MoveToEx(hdc, 0, y)
        win32gui.LineTo(hdc, self.width, y)
        win32gui.SetTextColor(hdc, 0xab34de)
        txt = f'{self.valueRange[1] / 100000000 :.1f}亿'
        rt = (self.width + 20, y - 8, self.width + 100, y + 8)
        win32gui.DrawText(hdc, txt, len(txt), rt, win32con.DT_LEFT)
        win32gui.RestoreDC(hdc, sdc)

class RateIndicator(Indicator):
    def __init__(self, klineWin, config) -> None:
        super().__init__(klineWin, config)

    def calcValueRange(self, fromIdx, endIdx):
        self.valueRange = None
        maxVal = minVal = 0
        for i in range(fromIdx, endIdx):
            d = self.data[i]
            if maxVal == 0:
                maxVal = getattr(d, 'rate', 0)
                minVal = getattr(d, 'rate', 0)
            else:
                maxVal = max(maxVal, getattr(d, 'rate', 0))
                minVal = min(minVal, getattr(d, 'rate', 0))
        self.valueRange = (0, maxVal)

    def getYAtValue(self, value):
        if not self.valueRange or (not self.valueRange[1]):
            return 0
        if value < self.valueRange[0] or value > self.valueRange[1]:
            return rect[1]
        p = (value - self.valueRange[0]) / (self.valueRange[1])
        H = self.height
        y = H - int(p * H)
        return y

    def getValueAtY(self, y):
        if not self.valueRange:
            return None
        rr = self.valueRange
        m = (rr[1] - rr[0]) / self.height
        val = int(rr[1] - y * m)
        return {'value': val, 'fmtVal': f'{val :.1f}%', 'valType': 'Rate'}

    def getColor(self, idx, data):
        if data.close >= data.open:
            return 'red'
        return 'light_green'

    def drawItem(self, idx, hdc, pens, hbrs):
        data = self.data[idx]
        if not hasattr(data, 'rate') or not self.valueRange:
            return
        cx = self.getCenterX(idx)
        bx = cx - self.klineWin.klineWidth // 2
        ex = bx + self.klineWin.klineWidth
        rect = (bx, self.getYAtValue(self.valueRange[0]), ex, self.getYAtValue(data.rate) + 1)
        color = self.getColor(idx, data)
        win32gui.SelectObject(hdc, pens[color])
        if data.close >= data.open:
            win32gui.SelectObject(hdc, hbrs['black'])
            win32gui.Rectangle(hdc, *rect)
        else:
            win32gui.FillRect(hdc, rect, hbrs[color])

    def draw(self, hdc, pens, hbrs):
        if not self.visibleRange:
            return
        self.drawBackground(hdc, pens, hbrs)
        w = self.width
        for idx in range(*self.visibleRange):
            self.drawItem(idx, hdc, pens, hbrs)
        if self.valueRange[1] >= 5:
            win32gui.SelectObject(hdc, pens['blue'])
            y = self.getYAtValue(5)
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, w, y)
        if self.valueRange[1] >= 10:
            win32gui.SelectObject(hdc, pens['0xff00ff'])
            y = self.getYAtValue(10)
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, w, y)
        if self.valueRange[1] >= 20:
            win32gui.SelectObject(hdc, pens['yellow'])
            y = self.getYAtValue(20)
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, w, y)

    def drawBackground(self, hdc, pens, hbrs):
        sdc = win32gui.SaveDC(hdc)
        win32gui.SelectObject(hdc, pens['bk_dot_red'])
        y = self.getYAtValue(self.valueRange[1])
        win32gui.MoveToEx(hdc, 0, y)
        win32gui.LineTo(hdc, self.width, y)
        win32gui.SetTextColor(hdc, 0xab34de)
        txt = f'{self.valueRange[1] :.1f}%'
        rt = (self.width + 20, y - 8, self.width + 100, y + 8)
        win32gui.DrawText(hdc, txt, len(txt), rt, win32con.DT_LEFT)
        win32gui.RestoreDC(hdc, sdc)
    
class KLineWindow(base_win.BaseWindow):
    LEFT_MARGIN, RIGHT_MARGIN = 0, 70
    INDICATOR_KLINE = 1
    INDICATOR_AMOUNT = 2
    INDICATOR_RATE = 4

    def __init__(self):
        super().__init__()
        self.model = None
        self.klineWidth = 6 # K线宽度
        self.klineSpace = 2 # K线之间的间距离
        self.selIdx = -1
        self.mouseXY = None
        self.indicators = []

    def addIndicator(self, indicator):
        self.indicators.append(indicator)

    # indicator = INDICATOR_KLINE | INDICATOR_AMOUNT | INDICATOR_RATE
    def addDefaultIndicator(self, indicator = 7):
        if indicator & KLineWindow.INDICATOR_KLINE:
            idt = KLineIndicator(self, {'height': -1, 'margins': (30, 20)})
            self.indicators.append(idt)
        if indicator & KLineWindow.INDICATOR_RATE:
            idt = RateIndicator(self, {'height': 60, 'margins': (15, 0)})
            self.indicators.append(idt)
        if indicator & KLineWindow.INDICATOR_AMOUNT:
            idt = AmountIndicator(self, {'height': 60, 'margins': (15, 0)})
            self.indicators.append(idt)

    def calcIndicatorsRect(self):
        *_, w, h = self.getRect()
        fixHeight = 0
        for i in range(0, len(self.indicators)):
            cf = self.indicators[i]
            fixHeight += cf.getMargins(0) + cf.getMargins(1)
            if cf.config['height'] >= 0:
                fixHeight += cf.config['height']
        exHeight = max(h - fixHeight, 0)
        y = 0
        for i in range(0, len(self.indicators)):
            cf = self.indicators[i]
            cf.x = self.LEFT_MARGIN
            y = y + cf.getMargins(0)
            cf.y = y
            cf.width = w - self.RIGHT_MARGIN - cf.x
            if cf.config['height'] < 0:
                cf.height = exHeight
            else:
                cf.height = cf.config['height']
            y += cf.height + cf.getMargins(1)

    def getRectByIndicator(self, indicatorOrIdx):
        if type(indicatorOrIdx) == int:
            idx = indicatorOrIdx
        elif isinstance(indicatorOrIdx, Indicator):
            for i in range(0, len(self.indicators)):
                if self.indicators[i] == indicatorOrIdx:
                    idx = i
                    break
        if idx < 0 or idx >= len(self.indicators):
            return None
        idt = self.indicators[idx]
        return [idt.x, idt.y, idt.width, idt.height]

    def setModel(self, model):
        self.model = model
        if not model:
            return
        self.model.calcMA(5)
        self.model.calcMA(10)
        self.model.calcZDT()
        self.model.calcZhangFu()
        for idt in self.indicators:
            idt.setData(self.model, self.model.data)

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
        si = self.indicators[0].getIdxAtX(x)
        if self.selIdx != si:
            self.updateAttr('selIdx', si)
        win32gui.InvalidateRect(self.hwnd, None, True)
        #print('[onMouseMove] price=', self.getPriceAtY(y))

    def setSelIdx(self, idx):
        idt : Indicator = self.indicators[0] # KlineIndictor
        if not idt.visibleRange or idx < 0 or idx >= idt.visibleRange[1]:
            return
        data = self.model.data[idx]
        x = idt.getCenterX(idx)
        y = idt.getYAtValue(data.close) + idt.y
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
            if self.indicators[0].visibleRange and self.selIdx < self.indicators[0].visibleRange[1] - 1:
                ni = self.selIdx + 1
                self.setSelIdx(ni)
        elif oem == 72: # up arrow key
            self.klineWidth += 2
            if self.klineWidth // 2 > self.klineSpace:
                self.klineSpace = min(self.klineSpace + 1, 2)
            if self.selIdx >= 0:
                self.makeVisible(self.selIdx)
                x = self.indicators[0].getCenterX(self.selIdx)
                self.mouseXY = (x, self.mouseXY[1])
            win32gui.InvalidateRect(self.hwnd, None, True)
        elif oem == 80: # down arrow key
            self.klineWidth = max(self.klineWidth - 2, 1)
            if self.klineWidth // 2 < self.klineSpace:
                self.klineSpace = max(self.klineSpace - 1, 0)
            if self.selIdx >= 0:
                self.makeVisible(self.selIdx)
                x = self.indicators[0].getCenterX(self.selIdx)
                self.mouseXY = (x, self.mouseXY[1])
            win32gui.InvalidateRect(self.hwnd, None, True)

    def makeVisible(self, idx):
        self.calcIndicatorsRect()
        idt : Indicator = None
        for idt in self.indicators:
            idt.calcVisibleRange(idx)
            vr = idt.visibleRange
            if vr:
                idt.calcValueRange(*vr)
        win32gui.InvalidateRect(self.hwnd, None, True)

    def drawSelTip(self, hdc, pens, hbrs):
        if self.selIdx < 0 or (not self.model) or (not self.model.data) or self.selIdx >= len(self.model.data):
            return
        sdc = win32gui.SaveDC(hdc)
        d = self.model.data[self.selIdx]
        txt = f'{self.model.code}\n{self.model.name}\n\n时间\n{d.day//10000}\n{d.day%10000:04d}\n\n涨幅\n{d.zhangFu:.2f}%\n\n成交额\n{d.amount/100000000:.02f}亿'
        if hasattr(d, 'rate'):
            txt += f'\n\n换手率\n{d.rate :.1f}%'
        rc = (0, 60, 60, 300)
        win32gui.SelectObject(hdc, hbrs['black'])
        win32gui.SelectObject(hdc, pens['red'])
        win32gui.Rectangle(hdc, *rc)
        win32gui.SetTextColor(hdc, 0xffffff)
        win32gui.DrawText(hdc, txt, len(txt), rc, win32con.DT_CENTER)
        win32gui.RestoreDC(hdc, sdc)

    def onDraw(self, hdc):
        pens = {}
        hbrs = {}
        pens['white'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xffffff)
        pens['red'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x0000ff)
        pens['green'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ff00)
        pens['light_green'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xfcfc54)
        pens['blue'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xff0000)
        pens['yellow'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
        pens['0xff00ff'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xff00ff)
        pens['dark_red'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x0000aa) # 暗红色
        pens['dark_red2'] = win32gui.CreatePen(win32con.PS_SOLID, 2, 0x0000aa) # 暗红色
        pens['bk_dot_red'] = win32gui.CreatePen(win32con.PS_DOT, 1, 0x000055) # 背景虚线

        hbrs['white'] = win32gui.CreateSolidBrush(0xffffff)
        hbrs['red'] = win32gui.CreateSolidBrush(0x0000ff)
        hbrs['green'] = win32gui.CreateSolidBrush(0x00ff00)
        hbrs['light_green'] = win32gui.CreateSolidBrush(0xfcfc54)
        hbrs['blue'] = win32gui.CreateSolidBrush(0xff0000)
        hbrs['yellow'] = win32gui.CreateSolidBrush(0x00ffff)
        hbrs['black'] = win32gui.CreateSolidBrush(0x000000)
        hbrs['0xff00ff'] = win32gui.CreateSolidBrush(0xff00ff)
        
        *_, w, h = self.getRect()
        for i, idt in enumerate(self.indicators):
            sdc = win32gui.SaveDC(hdc)
            win32gui.SetViewportOrgEx(hdc, idt.x, idt.y)
            idt.draw(hdc, pens, hbrs)
            if i == 0:
                win32gui.SelectObject(hdc, pens['dark_red2'])
            else:
                win32gui.SelectObject(hdc, pens['dark_red'])
            y = idt.height + idt.getMargins(1)
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, w, y)
            win32gui.RestoreDC(hdc, sdc)
        
        win32gui.SelectObject(hdc, pens['dark_red'])
        win32gui.MoveToEx(hdc, w - self.RIGHT_MARGIN + 10, 0)
        win32gui.LineTo(hdc, w - self.RIGHT_MARGIN + 10, h)
        self.drawMouse(hdc, pens)
        self.drawSelTip(hdc, pens, hbrs)

        if self.mouseXY:
            self.drawTipPrice(hdc, self.mouseXY[1], pens, hbrs)
        for k in pens:
            win32gui.DeleteObject(pens[k])
        for k in hbrs:
            win32gui.DeleteObject(hbrs[k])

    def drawMouse(self, hdc, pens):
        if not self.mouseXY:
            return
        x, y = self.mouseXY
        *_, w, h = self.getRect()
        wp = win32gui.CreatePen(win32con.PS_DOT, 1, 0xffffff)
        win32gui.SelectObject(hdc, wp)
        win32gui.MoveToEx(hdc, self.LEFT_MARGIN, y)
        win32gui.LineTo(hdc, w, y)
        win32gui.MoveToEx(hdc, x, 0)
        win32gui.LineTo(hdc, x, h)
        win32gui.DeleteObject(wp)

    def getValueAtY(self, y):
        for i in range(0, len(self.indicators)):
            rect = self.getRectByIndicator(i)
            if y >= rect[1] and y < rect[3] + rect[1]:
                return self.indicators[i].getValueAtY(y - rect[1])
        return None

    def drawTipPrice(self, hdc, y, pens, hbrs):
        val = self.getValueAtY(y)
        if not val:
            return
        win32gui.SetTextColor(hdc, 0x0000ff)
        w = self.getRect()[2]
        H = 16
        rc = (w - self.RIGHT_MARGIN + 10 + 1, y - H // 2, w, y + H // 2)
        hb = win32gui.CreateSolidBrush(0x800040)
        win32gui.FillRect(hdc, rc, hb)
        win32gui.DrawText(hdc, val['fmtVal'], len(val['fmtVal']), rc, win32con.DT_CENTER)
        win32gui.DeleteObject(hb)

if __name__ == '__main__':
    win = KLineWindow()
    win.addDefaultIndicator()
    rect = (0, 0, 1000, 650)
    win.createWindow(None, rect, win32con.WS_VISIBLE | win32con.WS_OVERLAPPEDWINDOW)
    model = KLineModel_Ths('002682')
    model.loadDataFile()
    win.setModel(model)
    win.makeVisible(-1)
    win32gui.PumpMessages()