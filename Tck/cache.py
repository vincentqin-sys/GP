import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, json
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Download import henxin, ths_ddlr, cls
from THS import ths_win, hot_utils
from Common import base_win, timeline, kline, table

base_win.ThreadPool.start()

class CacheManager(base_win.Listener):
    def __init__(self) -> None:
        self.cache = {}

    def _needUpdate(self, data):
        now = datetime.datetime.now()
        cc : datetime.datetime = data['_load_time']
        scc = cc.strftime('%H:%M')
        if scc > '15:00':
            return False
        delta : datetime.timedelta = now - cc
        if delta.seconds >= 180:
            return True
        return False

    def getData(self, code, win):
        if type(code) == int:
            code = f'{code :05d}'
        if code not in self.cache:
            self.download(code, win)
            return None
        data = self.cache[code]
        if self._needUpdate(data):
            self.cache.pop(code)
            self.download(code, win)
            return None
        return data
    
    def download(self, code, win):
        base_win.ThreadPool.addTask(code, self._download, code, win)

    def _calcZF(self, data):
        if (not data.get('pre', 0)) or (not data.get('dataArr', None)) :
            return None
        pre = data['pre']
        last = data['dataArr'][-1]
        price = last['price']
        if not price:
            return
        return (price - pre) / pre

    def _download(self, code, win):
        hx = henxin.HexinUrl()
        ds = hx.loadUrlData( hx.getFenShiUrl(code) )
        ds['code'] = code
        zf = self._calcZF(ds)
        render = TimelineRender()
        render.setData(ds)
        rs = {'_load_time': datetime.datetime.now(), 'render': render, 'zf': zf}
        self.cache[code] = rs
        win.invalidWindow()

_cache = CacheManager()

class TimelineRender:
    def __init__(self) -> None:
        self.data = None
        self.paddings = (0, 5, 35, 5)
        self.priceRange = None
        self.maxPrice = None
        self.minPrice = None

    def calcPriceRange(self):
        minVal = 100000
        maxVal = -10000
        for d in self.data['dataArr']:
            minVal = min(d['price'], minVal)
            maxVal = max(d['price'], maxVal)
        self.maxPrice = maxVal
        self.minPrice = minVal
        minVal = min(self.data['pre'], minVal)
        maxVal = max(self.data['pre'], maxVal)
        self.priceRange = (minVal, maxVal)

    def setData(self, data):
        self.priceRange = None
        self.data = data
        if not data:
            return
        self.calcPriceRange()
    
    def getYAtPrice(self, price, height):
        ph = self.priceRange[1] - self.priceRange[0]
        if ph == 0:
            return 0
        height -= self.paddings[1] + self.paddings[3]
        y = (self.priceRange[1] - price) / ph * height + self.paddings[1]
        return int(y)
    
    def getPriceColor(self, price):
        color = 0x0
        GREEN = 0xA3C252
        RED = 0x2204de
        # check is zt
        code = self.data['code']
        zf = 0.1
        if code[0] == '3' or code[0 : 3] == '688':
            zf = 0.20
        pre = self.data['pre']
        ztPrice = int(int(pre * 100 + 0.5) * (1 + zf) + 0.5)
        if int(price * 100 + 0.5) >= ztPrice:
            return 0xdd0000
        dtPrice = int(int(pre * 100 + 0.5) * (1 - zf) + 0.5)
        if int(price * 100 + 0.5) <= dtPrice:
            return 0x00dddd
        if price > self.data['pre']:
            color = RED
        elif price < self.data['pre']:
            color = GREEN
        return color

    def onDraw(self, hdc, drawer : base_win.Drawer, rect):
        if not self.priceRange or self.priceRange[1] - self.priceRange[0] <= 0:
            return
        cwidth = rect[2] - rect[0] - self.paddings[0] - self.paddings[2]
        height = rect[3] - rect[1]
        da = self.data['dataArr']
        if not da:
            return
        dx = cwidth / 240
        drawer.use(hdc, drawer.getPen(self.getPriceColor(da[-1]['price'])))
        for i, d in enumerate(da):
            x = int(i * dx + self.paddings[0])
            y = self.getYAtPrice(d['price'], height)
            if i == 0:
                win32gui.MoveToEx(hdc, x + rect[0], y + rect[1])
            else:
                win32gui.LineTo(hdc, x + rect[0], y + rect[1])
        # draw zero line
        GREEY = 0x909090
        drawer.use(hdc, drawer.getPen(GREEY, win32con.PS_DOT))
        py = self.getYAtPrice(self.data['pre'], height)
        win32gui.MoveToEx(hdc, rect[0] + self.paddings[0], py + rect[1])
        win32gui.LineTo(hdc, rect[2] - self.paddings[2], py + rect[1])
        # draw max price
        mzf = (self.maxPrice - self.data['pre']) / self.data['pre'] * 100
        szf = (self.minPrice - self.data['pre']) / self.data['pre'] * 100
        ZFW = 50
        rc = [rect[2] - ZFW, rect[1], rect[2], rect[1] + 20]
        drawer.use(hdc, drawer.getFont(fontSize = 10))
        drawer.drawText(hdc, f'{mzf :.2f}%', rc, self.getPriceColor(self.maxPrice), win32con.DT_RIGHT | win32con.DT_TOP)
        rc = [rect[2] - ZFW, rect[3] - 12, rect[2], rect[3]]
        drawer.drawText(hdc, f'{szf :.2f}%', rc, self.getPriceColor(self.minPrice), win32con.DT_RIGHT | win32con.DT_BOTTOM)

# 分时图
def renderTimeline(win : base_win.TableWindow, hdc, row, col, colName, value, rowData, rect):
    global _cache
    if 'secu_code' in rowData:
        code = rowData['secu_code'][2 : ]
    elif 'code' in rowData:
        code = rowData['code']
    else:
        return
    data = _cache.getData(code, win)
    if not data:
        return
    data['render'].onDraw(hdc, win.drawer, rect)

# 涨幅
def renderZF(win : base_win.TableWindow, hdc, row, col, colName, value, rowData, rect):
    GREEN = 0xA3C252
    RED = 0x2204de
    global _cache
    if value == None:
        return
    if 'secu_code' in rowData:
        code = rowData['secu_code'][2 : ]
    elif 'code' in rowData:
        code = rowData['code']
    else:
        return
    data = _cache.getData(code, win)
    if data and 'zf' in data:
        value = data['zf']
    color = 0x00
    if value > 0: color = RED
    elif value < 0: color = GREEN
    value *= 100
    win.drawer.drawText(hdc, f'{value :.2f} %', rect, color, win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)    