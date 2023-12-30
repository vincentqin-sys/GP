import os, sys
import win32gui, win32con

cwd = os.getcwd()
w = cwd.index('GP')
cwd = cwd[0 : w + 2]
sys.path.append(cwd)
from UI import basewin
from Tdx import datafile

class KLineModel(datafile.DataFile):
    def __init__(self, code):
        super().__init__(code, datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL)

    def setDataRange(fromIdx, endIdx):
        pass

class KLineWindow(basewin.BaseWindow):
    LEFT_MARGIN = 5 # 左间距
    RIGHT_MARGIN = 80 # 右间距
    TOP_BOTTOM_MARGIN = 20 # 上下间距

    def __init__(self):
        super().__init__()
        self.model : KLineModel = None # KLineModel
        self.klineWidth = 6 # K线宽度
        self.klineSpace = 2 # K线之间的间距离
        self.visibleRange = None # K线显示范围
        self.priceRange = None # 价格显示范围
        self.selIdx = -1
        self.mouseXY = None

    def loadCode(self, code):
        self.model = KLineModel(code)
        self.model.calcMA(5)
        self.model.calcMA(10)
        self.model.calcZDT()
        self.model.calcZhangFu()
        self.visibleRange = None
        self.priceRange = None
    
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
        if msg == win32con.WM_KEYUP:
            oem = lParam >> 16 & 0xff
            self.onKeyUp(oem)
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

    def onKeyUp(self, oem):
        if oem == 73: # page up
            pass
        elif oem == 81: # page down
            pass
        elif oem == 75: # left arrow key
            if self.selIdx > 0:
                ni = self.selIdx - 1
                data = self.model.data[ni]
                x = self.getCenterX(ni)
                y = self.getYAtPrice(data.close)
                self.mouseXY = (x, y)
                self.updateAttr('selIdx', ni)
        elif oem == 77: # right arrow key
            if self.visibleRange and self.selIdx < self.visibleRange[1] - 1:
                ni = self.selIdx + 1
                data = self.model.data[ni]
                x = self.getCenterX(ni)
                y = self.getYAtPrice(data.close)
                self.mouseXY = (x, y)
                self.updateAttr('selIdx', ni)
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
        w -= self.RIGHT_MARGIN - self.LEFT_MARGIN
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
        win32gui.InvalidateRect(self.hwnd, None, True)
    
    def getYAtPrice(self, price):
        if not self.priceRange:
            return 0
        if price < self.priceRange[0] or price > self.priceRange[1]:
            return 0
        p = (price - self.priceRange[0]) / (self.priceRange[1] - self.priceRange[0])
        H = self.getRect()[3]
        p = int(p * (H - self.TOP_BOTTOM_MARGIN * 2))
        y = H - self.TOP_BOTTOM_MARGIN - p
        return y

    def getPriceAtY(self, y):
        if not self.priceRange:
            return 0
        h = self.getRect()[3]
        m = (self.priceRange[1] - self.priceRange[0]) / (h - self.TOP_BOTTOM_MARGIN * 2)
        z0 = self.TOP_BOTTOM_MARGIN * m + self.priceRange[1]
        return int(z0 - y * m)

    def getCenterX(self, idx):
        if not self.visibleRange:
            return -1
        if idx < self.visibleRange[0] or idx > self.visibleRange[1]:
            return -1
        i = idx - self.visibleRange[0]
        x = self.LEFT_MARGIN + i * (self.klineWidth + self.klineSpace)
        x += self.klineWidth // 2
        return x

    def getIdxAtX(self, x):
        if not self.visibleRange:
            return -1
        w = self.getRect()[2]
        if x <= self.LEFT_MARGIN or x >= w - self.RIGHT_MARGIN:
            return -1
        x -= self.LEFT_MARGIN
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
        rect = (bx, self.getYAtPrice(data.open), ex, self.getYAtPrice(data.close))
        color = self.getColor(data)
        win32gui.SelectObject(hdc, pens[color])
        win32gui.MoveToEx(hdc, cx, self.getYAtPrice(data.low))
        win32gui.LineTo(hdc, cx, self.getYAtPrice(data.high))
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
        hbrs['white'] = win32gui.CreateSolidBrush(0xffffff)
        hbrs['red'] = win32gui.CreateSolidBrush(0x0000ff)
        hbrs['green'] = win32gui.CreateSolidBrush(0x00ff00)
        hbrs['light_green'] = win32gui.CreateSolidBrush(0xfcfc54)
        hbrs['blue'] = win32gui.CreateSolidBrush(0xff0000)
        hbrs['yellow'] = win32gui.CreateSolidBrush(0x00ffff)
        hbrs['black'] = win32gui.CreateSolidBrush(0x000000)
        for i in range(*self.visibleRange):
            sdc = win32gui.SaveDC(hdc)
            self.drawKLine(hdc, i, pens, hbrs)
            win32gui.RestoreDC(hdc, sdc)
        self.drawMA(hdc, 5)
        self.drawMA(hdc, 10)
        self.drawMouse(hdc, pens)
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
                    win32gui.MoveToEx(hdc, self.getCenterX(bi), self.getYAtPrice(mx))
                    moveToFlag = True
                continue
            win32gui.LineTo(hdc, self.getCenterX(i), self.getYAtPrice(getattr(self.model.data[i], ma)))
        win32gui.DeleteObject(pen)

    def drawMouse(self, hdc, pens):
        if not self.mouseXY:
            return
        x, y = self.mouseXY
        *_, w, h = self.getRect()
        win32gui.SelectObject(hdc, pens['white'])
        win32gui.MoveToEx(hdc, 0, y)
        win32gui.LineTo(hdc, w, y)
        win32gui.MoveToEx(hdc, x, 0)
        win32gui.LineTo(hdc, x, h)

    def getColor(self, data):
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

    def drawTipPrice(self, hdc, y, pens, hbrs):
        if not self.priceRange:
            return
        price = self.getPriceAtY(y)
        if price <= 0:
            return
        price = f'{price//100}.{price%100:02d}'
        win32gui.SetTextColor(hdc, 0x0000ff)
        w = self.getRect()[2]
        H = 16
        rc = (w - 50, y - H // 2, w, y + H // 2)
        hb = win32gui.CreateSolidBrush(0x800040)
        win32gui.FillRect(hdc, rc, hb)
        win32gui.DrawText(hdc, price, len(price), rc, win32con.DT_CENTER)
        win32gui.DeleteObject(hb)

class KLineTipWindow(basewin.BaseWindow):
    def __init__(self):
        super().__init__()
        self.data : datafile.ItemData = None

    def createWindow(self, parentWnd):
        rect = (0, 0, 80, 200)
        style = win32con.WS_VISIBLE | win32con.WS_POPUP  | win32con.WS_CAPTION
        super().createWindow(parentWnd, rect, style)

    def updateItemData(self, data):
        self.data = data
        win32gui.InvalidateRect(self.hwnd, None, True)

    def draw(self, hdc):
        if not self.data:
            return
        d = self.data
        txt = f'时间\n{d.day//10000}\n{d.day%10000:04d}\n\n涨幅\n{d.zhangFu:.2f}%\n\n成交额\n{d.amount/100000000:.02f}亿'
        rr = self.getRect()
        rc = (0, 10, rr[2], rr[3])
        win32gui.SetTextColor(hdc, 0xffffff)
        win32gui.DrawText(hdc, txt, len(txt), rc, win32con.DT_CENTER)

    def onListen(self, evtName, info):
        #print(evtName, info)
        if evtName == 'selIdx.changed':
            self.data = info['data']
            win32gui.InvalidateRect(self.hwnd, None, True)

class AmountWindow(basewin.BaseWindow):
    def __init__(self) -> None:
        super().__init__()


if __name__ == '__main__':
    win = KLineWindow()
    rect = (0, 0, 1000, 500)
    win.createWindow(None, rect, win32con.WS_VISIBLE | win32con.WS_OVERLAPPEDWINDOW)
    tipWin = KLineTipWindow()
    tipWin.createWindow(win.hwnd)
    win.addListener(tipWin)
    win.loadCode(300093)
    win.makeVisible(-1)
    win32gui.PumpMessages()