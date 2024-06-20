import os, sys, functools, copy, datetime
import win32gui, win32con
import requests, peewee as pw

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from db import ths_orm, tdx_orm, tck_orm
from Tdx import datafile
from Download import henxin, cls
from Common import base_win, ext_win

class KLineModel_Tdx(datafile.DataFile):
    def __init__(self, code):
        super().__init__(code, datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL)

    def setDataRange(fromIdx, endIdx):
        pass

class KLineModel_Ths(henxin.ThsDataFile):
    def __init__(self, code) -> None:
        super().__init__(code, datafile.DataFile.DT_DAY)

class KLineModel_Cls(cls.ClsDataFile):
    def __init__(self, code) -> None:
        super().__init__(code, datafile.DataFile.DT_DAY)        

# 指标 Vol, Amount, Rate等
class Indicator:
    # config = { height: int 必填
    #            margins: (top, bottom)  可选
    #            name: ''
    #            title: 'xx'
    #        }
    def __init__(self, config = None) -> None:
        self.klineWin = None
        self.config = config or {}
        self.data = None
        self.valueRange = None
        self.visibleRange = None
        self.width = 0
        self.height = 0

    def getSimpleStrCode(self, code):
        if code == None:
            return None
        if type(code) == int:
            return f'{code :06d}'
        if len(code) == 8 and (code[0 : 2] == 'sh' or code[0 : 2] == 'sz'):
            return code[2 : ]
        return code

    def init(self, klineWin):
        self.klineWin = klineWin

    def setData(self, data):
        self.data = data
        self.valueRange = None
        self.visibleRange = None

    def calcValueRange(self, fromIdx, endIdx):
        pass

    def getYAtValue(self, value):
        return self.getYAtValue2(value, self.height)

    def getYAtValue2(self, value, height):
        if not self.valueRange:
            return 0
        if value < self.valueRange[0] or value > self.valueRange[1]:
            return 0
        if self.valueRange[1] == self.valueRange[0]:
            return 0
        p = height * (value - self.valueRange[0]) / (self.valueRange[1] - self.valueRange[0])
        y = height - int(p)
        return y

    def getValueAtY(self, y):
        pass

    def getColor(self, idx, data):
        if getattr(data ,'close', 0) >= getattr(data ,'open', 0):
            return 'red'
        return 'light_green'

    def draw(self, hdc, pens, hbrs):
        pass

    def getItemWidth(self):
        return self.klineWin.klineWidth

    def getItemSpace(self):
        return self.klineWin.klineSpace

    def getVisibleNum(self):
        return self.width // (self.getItemWidth() + self.getItemSpace())
    
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
        x = i * (self.getItemWidth() + self.getItemSpace())
        x += self.getItemWidth() // 2
        return x
    
    def getIdxAtX(self, x):
        if not self.visibleRange:
            return -1
        if x <= 0 or x >= self.width:
            return -1
        idx = x // (self.getItemWidth() + self.getItemSpace())
        idx += self.visibleRange[0]
        if idx >= len(self.data) or idx >= self.visibleRange[1]:
            return -1
        return idx

    def calcVisibleRange(self, idx):
        self.visibleRange = self.calcVisibleRange_1(idx, self.data)

    def calcVisibleRange_1(self, idx, data):
        if not data:
            return None
        num = self.getVisibleNum()
        if idx < 0 or idx >= len(data):
            vr = (max(len(data) - num, 0), len(data))
            return vr
        HALF_NUM = num // 2
        if num >= len(data):
            return (0, len(data))
        leftNum = min(HALF_NUM, idx)
        fromIdx = idx - leftNum
        endIdx = min(fromIdx + num, len(data))
        while endIdx - fromIdx < num:
            endIdx = min(endIdx + 1, len(data))
            if endIdx - fromIdx >= num: break
            fromIdx = max(fromIdx - 1, 0)
        return (fromIdx, endIdx)

class RefZSKDrawer:
    def __init__(self) -> None:
        self.model = None # 关联指数
        self.code = None
        self.zsCode = None
        self.newData = None
        self.valueRange = None

    def updateData(self, code):
        if not code or self.code == code:
            return
        if code[0 : 2] in ('sh', 'sz'):
            code = code[2 : ]
        self.code = code
        self.model = None
        if code[0] not in ('3', '0', '6'):
            return
        gntc = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == code)
        if not gntc or not gntc.hy:
            return
        hys = gntc.hy.split('-')
        zs = ths_orm.THS_ZS.get_or_none(ths_orm.THS_ZS.name == hys[1])
        if not zs:
            return
        if zs.code == self.zsCode:
            return
        self.zsCode = zs.code
        self.model = KLineModel_Ths(self.zsCode)
        self.model.loadDataFile()
        self.model.calcZhangFu()

    def drawKLineItem(self, hdc, pens, hbrs, idx, cx, itemWidth, getYAtValue):
        if not self.newData:
            return
        if idx < 0 or idx >= len(self.newData):
            return
        bx = cx - itemWidth // 2
        ex = bx + itemWidth
        data = self.newData[idx]
        rect = [bx, getYAtValue(data.open), ex, getYAtValue(data.close)]
        if rect[1] == rect[3]:
            rect[1] -=1
        if 'ref-zs-color' not in pens:
            pens['ref-zs-color'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xFFCCCC)
        if 'ref-zs-color' not in hbrs:
            hbrs['ref-zs-color'] = win32gui.CreateSolidBrush(0xFFCCCC)
        win32gui.SelectObject(hdc, pens['ref-zs-color'])
        win32gui.MoveToEx(hdc, cx, getYAtValue(data.low))
        win32gui.LineTo(hdc, cx, getYAtValue(min(data.open, data.close)))
        win32gui.MoveToEx(hdc, cx, getYAtValue(max(data.open, data.close)))
        win32gui.LineTo(hdc, cx, getYAtValue(data.high))
        if data.close >= data.open:
            nullHbr = win32gui.GetStockObject(win32con.NULL_BRUSH)
            win32gui.SelectObject(hdc, nullHbr)
            win32gui.Rectangle(hdc, *rect)
        else:
            win32gui.FillRect(hdc, tuple(rect), hbrs['ref-zs-color'])

    def calcPercentPrice(self, data, fromIdx, endIdx, startDay):
        self.newData = []
        self.valueRange = None
        if not self.model:
            return
        sidx = self.model.getItemIdx(startDay)
        p = self.model.data[sidx].open / data[fromIdx].open
        maxVal, minVal = 0, 9999999
        for i in range(fromIdx, endIdx):
            di = i - fromIdx + sidx
            it = henxin.HexinUrl.ItemData()
            cur = self.model.data[di]
            it.open = cur.open / p
            it.close = cur.close / p
            it.low = cur.low / p
            it.high = cur.high / p
            self.newData.append(it)
            
            maxVal = max(maxVal, it.high)
            minVal = min(minVal, it.low)
        self.valueRange = (minVal, maxVal)

    def getZhangFu(self, day):
        if not self.model:
            return None
        item = self.model.getItemData(day)
        if not item:
            return None
        if hasattr(item, 'zhangFu'):
            return item.zhangFu
        return None

class KLineIndicator(Indicator):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.markDay = None
        self.refZSDrawer = RefZSKDrawer()

    def setData(self, data):
        super().setData(data)
        if data:
            self.refZSDrawer.updateData(self.klineWin.model.code)

    def setMarkDay(self, day):
        if not day:
            self.markDay = None
            return
        if type(day) == int:
            self.markDay = day
        elif type(day) == str:
            self.markDay = int(day.replace('-', ''))

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
            if getattr(d, 'MA5', None): 
                minVal = min(minVal, d.MA5)
                maxVal = max(maxVal, d.MA5)
            if getattr(d, 'MA10', None): 
                minVal = min(minVal, d.MA10)
                maxVal = max(maxVal, d.MA10)
        self.refZSDrawer.calcPercentPrice(self.data, fromIdx, endIdx, self.klineWin.model.data[fromIdx].day)
        # merge ref zs value range
        if self.refZSDrawer.valueRange:
            vr = self.refZSDrawer.valueRange
            if minVal > vr[0]: minVal = vr[0]
            if maxVal < vr[1]: maxVal = vr[1]
        # merge ma5 ma10
        
        self.valueRange = (minVal, maxVal)

    def getValueAtY(self, y):
        if not self.valueRange or not self.height:
            return None
        m = y * (self.valueRange[1] - self.valueRange[0]) / self.height
        val = int(self.valueRange[1] - m)
        if val / 100 >= 1000:
            fval = f'{val // 100}'
        elif val / 100 >= 100:
            fval = f'{val / 100 :0.1f}'
        else:
            fval = f'{val // 100}.{val % 100 :02d}'
        return {'value': val, 'fmtVal': fval, 'valType': 'Price'}

    def getColor(self, idx, data):
        if not self.klineWin.model:
            return 'light_green'
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
        self.drawMarkDay(self.markDay, hdc, pens, hbrs)
        sm = base_win.ThsShareMemory.instance()
        if sm.readMarkDay() != 0:
            self.drawMarkDay(sm.readMarkDay(), hdc, pens, hbrs)
        self.drawKLines(hdc, pens, hbrs)
        self.drawMA(hdc, 5)
        self.drawMA(hdc, 10)
    
    def drawMarkDay(self, markDay, hdc, pens, hbrs):
        if not markDay or not self.klineWin.model or not self.visibleRange:
            return
        idx = self.klineWin.model.getItemIdx(markDay)
        if idx < 0:
            return
        if idx < self.visibleRange[0] or idx >= self.visibleRange[1]:
            return
        x = self.getCenterX(idx)
        sx = x - self.getItemWidth() // 2 - self.getItemSpace()
        ex = x + self.getItemWidth() // 2 + self.getItemSpace()
        rc = (sx, 0, ex, self.height)
        pen = win32gui.GetStockObject(win32con.NULL_PEN)
        win32gui.SelectObject(hdc, pen)
        win32gui.FillRect(hdc, rc, hbrs['drak'])

    def drawKLineItem(self, idx, hdc, pens, hbrs, fillHbr):
        data = self.data[idx]
        cx = self.getCenterX(idx)
        bx = cx - self.getItemWidth() // 2
        ex = bx + self.getItemWidth()
        rect = [bx, self.getYAtValue(data.open), ex, self.getYAtValue(data.close)]
        if rect[1] == rect[3]:
            rect[1] -=1
        color = self.getColor(idx, data)

        win32gui.SelectObject(hdc, pens[color])
        win32gui.MoveToEx(hdc, cx, self.getYAtValue(data.low))
        win32gui.LineTo(hdc, cx, self.getYAtValue(min(data.open, data.close)))
        win32gui.MoveToEx(hdc, cx, self.getYAtValue(max(data.open, data.close)))
        win32gui.LineTo(hdc, cx, self.getYAtValue(data.high))
        if data.close >= data.open:
            nullHbr = win32gui.GetStockObject(win32con.NULL_BRUSH)
            win32gui.SelectObject(hdc, nullHbr)
            #win32gui.SelectObject(hdc, fillHbr)
            win32gui.Rectangle(hdc, *rect)
        else:
            win32gui.FillRect(hdc, tuple(rect), hbrs[color])
    
    def drawKLines(self, hdc, pens, hbrs):
        if not self.visibleRange:
            return
        for idx in range(*self.visibleRange):
            cx = self.getCenterX(idx)
            self.refZSDrawer.drawKLineItem(hdc, pens, hbrs, idx - self.visibleRange[0], cx, self.getItemWidth(), self.getYAtValue)
            self.drawKLineItem(idx, hdc, pens, hbrs, hbrs['black'])

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
                mx = getattr(self.data[i], ma, 0)
                if mx > 0:
                    win32gui.MoveToEx(hdc, self.getCenterX(i), self.getYAtValue(mx))
                    moveToFlag = True
                continue
            win32gui.LineTo(hdc, self.getCenterX(i), self.getYAtValue(getattr(self.data[i], ma)))
        win32gui.DeleteObject(pen)
    
class AmountIndicator(Indicator):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.config['title'] = '[成交额]'

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

    def getValueAtY(self, y):
        rr = self.valueRange
        if not rr:
            return None
        m = (rr[1] - rr[0]) / self.height
        val = int(rr[1] - y * m)
        return {'value': val, 'fmtVal': f'{val / 100000000 :.1f}亿', 'valType': 'Amount'}
    
    def getColor(self, idx, data):
        if idx > 0:
            rv = getattr(data, 'amount', 0)
            prv = getattr(self.data[idx - 1], 'amount', 0)
            if prv > 0 and rv / prv >= 2: # 倍量
                return 'blue'
        return super().getColor(idx, data)

    def drawItem(self, idx, hdc, pens, hbrs):
        data = self.data[idx]
        if not hasattr(data, 'amount') or not self.valueRange:
            return
        cx = self.getCenterX(idx)
        bx = cx - self.getItemWidth() // 2
        ex = bx + self.getItemWidth()
        rect = [bx, self.getYAtValue(self.valueRange[0]), ex, self.getYAtValue(data.amount) + 1]
        if rect[3] - rect[1] == 0 and data.amount > 0:
            rect[1] -= 1
        rect = tuple(rect)
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
        self.drawAmountTip(hdc, pens, hbrs)
        # draw title
        title = self.config.get('title', None)
        if not title:
            return
        rc = (0, 2, 100, 20)
        win32gui.SetTextColor(hdc, 0xab34de)
        win32gui.FillRect(hdc, rc, hbrs['black'])
        win32gui.DrawText(hdc, title, -1, rc, win32con.DT_LEFT)

    def drawAmountTip(self, hdc, pens, hbrs):
        if not self.klineWin.model or self.klineWin.model.code[0] == '8' or self.klineWin.model.code[0 : 3] == '399':
            return
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
    def __init__(self, config = None) -> None:
        super().__init__(config)
        self.config['title'] = '[换手率]'

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
        bx = cx - self.getItemWidth() // 2
        ex = bx + self.getItemWidth()
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
        # draw title
        title = self.config.get('title', None)
        if not title:
            return
        wc, *_ = win32gui.GetTextExtentPoint32(hdc, title)
        rc = (0, 2, wc + 5, 20)
        win32gui.SetTextColor(hdc, 0xab34de)
        win32gui.FillRect(hdc, rc, hbrs['black'])
        win32gui.DrawText(hdc, title, -1, rc, win32con.DT_LEFT)

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

# config = {itemWidth: int}
class CustomIndicator(Indicator):
    def __init__(self, config = None) -> None:
        super().__init__(config)
        if 'itemWidth' not in self.config:
            self.config['itemWidth'] = 80
        self.customData = None

    def init(self, klineWin):
        super().init(klineWin)
        self.klineWin.addListener(self.onSelIdxChanged, None)

    def onSelIdxChanged(self, evt, args):
        if evt.name != 'selIdx.changed':
            return
        idx = evt.selIdx
        self.calcVisibleRange(idx)
        if self.visibleRange:
            self.calcValueRange(*self.visibleRange)

    def getItemWidth(self):
        return self.config['itemWidth']

    def getItemSpace(self):
        return 1
    
    def setCustomData(self, datas):
        self.customData = datas
        if not self.customData:
            return
        for c in self.customData:
            day = c['day']
            if type(day) == str:
                day = day.replace('-', '')
                day = int(day)
            c['__day'] = day

    def translateIdx(self, idx):
        if not self.data or not self.customData:
            return -1
        day = int(self.data[idx].day)
        newIdx = -1
        for i, d in enumerate(self.customData):
            if d['__day'] == day:
                newIdx = i
                break
        return newIdx

    def calcVisibleRange(self, idx):
        if not self.data or not self.customData:
            self.visibleRange = None
            return
        idx = self.translateIdx(idx)
        self.visibleRange = self.calcVisibleRange_1(idx, self.customData)

    def _calcValueRange(self, fromIdx, endIdx, attrName):
        if not self.customData:
            return None
        maxVal = minVal = 0
        for i in range(fromIdx, endIdx):
            d = self.customData[i]
            if maxVal == 0:
                maxVal = d.get(attrName, 0)
                minVal = d.get(attrName, 0)
            else:
                maxVal = max(maxVal, d.get(attrName, 0))
                minVal = min(minVal, d.get(attrName, 0))
        return (0, maxVal)

    def getValueAtY(self, y):
        return

    def getColor(self, idx, data):
        return 'black'

    def drawItem(self, idx, hdc, pens, hbrs, x):
        data = self.customData[idx]
        pass

    def draw(self, hdc, pens, hbrs):
        if not self.visibleRange:
            return
        itemWidth = self.config['itemWidth']
        for idx in range(*self.visibleRange):
            i = (idx - self.visibleRange[0])
            self.drawItemBackground(idx, hdc, pens, hbrs, i * itemWidth)
            self.drawItem(idx, hdc, pens, hbrs, i * itemWidth)
        # draw title
        title = self.config.get('title', None)
        if not title:
            return
        wc, *_ = win32gui.GetTextExtentPoint32(hdc, title)
        rc = (0, 2, wc + 5, 20)
        win32gui.FillRect(hdc, rc, hbrs['black'])
        win32gui.SetTextColor(hdc, 0xab34de)
        win32gui.DrawText(hdc, title, -1, rc, win32con.DT_LEFT)

    def drawItemBackground(self, idx, hdc, pens, hbrs, x):
        WW = self.config['itemWidth']
        win32gui.SelectObject(hdc, pens['light_drak_dash_dot'])
        win32gui.MoveToEx(hdc, x + WW, 0)
        win32gui.LineTo(hdc, x + WW, self.height)

class DdlrIndicator(CustomIndicator):
    PADDING_TOP = 25
    def __init__(self, config = None, isDetail = True) -> None:
        super().__init__(config)
        if isDetail:
            self.config['title'] = '[大单流入]'
            if 'height' not in self.config:
                self.config['height'] = 100
        else:
            self.config['title'] = '[大单净流入]'
            if 'show-rate' not in self.config:
                self.config['show-rate'] = False
            if 'height' not in self.config:
                self.config['height'] = 30
        self.isDetail = isDetail

    def setData(self, data):
        super().setData(data)
        if not data:
            self.setCustomData(None)
            return
        code = self.getSimpleStrCode(self.klineWin.model.code)
        ddlr = ths_orm.THS_DDLR.select().where(ths_orm.THS_DDLR.code == code).order_by(ths_orm.THS_DDLR.day.asc()).dicts()
        maps = {}
        for d in ddlr:
            d['in'] = d['activeIn'] + d['positiveIn']
            d['out'] = d['activeOut'] + d['positiveOut']
            if d['amount'] > 0:
                d['ddRate'] = int(max(d['in'], d['out']) / d['amount'] * 100)
            else:
                d['ddRate'] = 0
            maps[int(d['day'])] = d
        rs = []
        for d in data:
            fd = maps.get(d.day, None)
            if not fd:
                fd = {'day': str(d.day), 'isNone': True, 'in': 0, 'out': 0, 'ddRate' : 0, 'total': 0}
            rs.append(fd)
        self.setCustomData(rs)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        WW = self.config['itemWidth']
        data = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + WW, self.height)
        if selDay == int(data['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        if self.isDetail:
            self.drawItem_Detail(idx, hdc, pens, hbrs, x)
        else:
            self.drawItem_Sum(idx, hdc, pens, hbrs, x)
    
    def drawItem_Sum(self, idx, hdc, pens, hbrs, x):
        WW = self.config['itemWidth']
        data = self.customData[idx]
        if 'isNone' in data:
            return
        jlr = f"{data['total']: .1f} 亿"
        zb = f"({data['ddRate']}%)"
        if self.config['show-rate']:
            HH = self.height // 2
        else:
            HH = self.height
        if data['total'] > 0:
            win32gui.SetTextColor(hdc, 0x0000dd)
        elif data['total'] < 0:
            win32gui.SetTextColor(hdc, 0x00dd00)
        else:
            win32gui.SetTextColor(hdc, 0xcccccc)
        win32gui.DrawText(hdc, jlr, -1, (x, 0, x + WW, HH), win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
        if self.config['show-rate']:
            win32gui.DrawText(hdc, zb, -1, (x, HH, x + WW, self.height), win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

    def drawItem_Detail(self, idx, hdc, pens, hbrs, x):
        if not self.valueRange:
            return
        WW = self.config['itemWidth']
        ITW = 5
        sx = x + 20
        data = self.customData[idx]
        sy = self.getYAtValue(data['in'])
        rc = (sx, sy, sx + ITW, self.getYAtValue(0))
        win32gui.FillRect(hdc, rc, hbrs['red'])
        rcx = (sx - 15, 3, sx + 15 + ITW, self.PADDING_TOP)
        if data['in'] > 0:
            win32gui.DrawText(hdc, f"{data['in'] :.1f}", -1, rcx, win32con.DT_CENTER)

        sx = rc[2] + 30
        sy = self.getYAtValue(data['out'])
        rc = (sx, sy, sx + ITW, self.getYAtValue(0))
        win32gui.FillRect(hdc, rc, hbrs['green'])
        rcx = (sx - 15, 3, sx + 15 + ITW, self.PADDING_TOP)
        if data['out'] > 0:
            win32gui.DrawText(hdc, f"{data['out'] :.1f}", -1, rcx, win32con.DT_CENTER)

    def getYAtValue(self, value):
        return self.getYAtValue2(value, self.height - self.PADDING_TOP - 3) + self.PADDING_TOP

    def calcValueRange(self, fromIdx, endIdx):
        vrIn = self._calcValueRange(fromIdx, endIdx, 'in')
        vrOut = self._calcValueRange(fromIdx, endIdx, 'out')
        if not vrIn or not vrOut:
            self.valueRange = None
        else:
            self.valueRange = (0, max(vrIn[1], vrOut[1]))

class DdlrPmIndicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        super().__init__(config)
        self.config['title'] = '[成交额排名]'
        if 'height' not in self.config:
            self.config['height'] = 30

    def setData(self, data):
        super().setData(data)
        if not data:
            self.setCustomData(None)
            return
        rs = []
        maps = {}
        code = self.getSimpleStrCode(self.klineWin.model.code)
        qr = tdx_orm.TdxVolPMModel.select().where(tdx_orm.TdxVolPMModel.code == code).order_by(tdx_orm.TdxVolPMModel.day.asc()).dicts()
        maps = {}
        for d in qr:
            maps[int(d['day'])] = d
        for d in data:
            fd = maps.get(d.day, None)
            if not fd:
                fd = {'day': str(d.day), 'isNone': True, 'pm': ''}
            rs.append(fd)
        self.setCustomData(rs)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        WW = self.config['itemWidth']
        data = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + WW, self.height)
        if selDay == int(data['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        win32gui.DrawText(hdc, str(data['pm']), -1, rc, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

class HotIndicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 30
        super().__init__(config)
        self.config['title'] = '[热度排名]'

    def setData(self, data):
        super().setData(data)
        model = self.klineWin.model
        code = self.getSimpleStrCode(model.code)
        if not model or not model.code or (type(code) == str and len(code) != 6):
            self.setCustomData(None)
            return
        hots = ths_orm.THS_HotZH.select().where(ths_orm.THS_HotZH.code == int(code)).order_by(ths_orm.THS_HotZH.day.asc()).dicts()
        maps = {}
        for d in hots:
            maps[d['day']] = d
        rs = []
        for d in data:
            fd = maps.get(d.day, None)
            if not fd:
                fd = {'day': d.day, 'zhHotOrder': ''}
            rs.append(fd)
        self.setCustomData(rs)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        WW = self.config['itemWidth']
        data = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + WW, self.height)
        if selDay == int(data['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        win32gui.DrawText(hdc, str(data['zhHotOrder']), -1, rc, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

class DayIndicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 20
        super().__init__(config)
    
    def setData(self, data):
        super().setData(data)
        days = [{'day': str(d.day)} for d in data]
        self.setCustomData(days)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        iw = self.config['itemWidth']
        data = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + iw, self.height)
        if selDay == int(data['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        day = self.customData[idx]['day']
        hday = day[4 : 6] + '-' + day[6 : 8]
        today = datetime.date.today()
        if today.year != int(day[0 : 4]):
            day = day[2: 4] + '-' + hday
        else:
            day = hday
        win32gui.SetTextColor(hdc, 0xcccccc)
        win32gui.DrawText(hdc, day, -1, rc, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

class ThsZsPMIndicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 50
        super().__init__(config)
        if 'title' not in self.config:
            self.config['title'] = '[指数排名]'

    def setData(self, data):
        super().setData(data)
        if not self.klineWin.model:
            self.setCustomData(None)
            return
        code = self.getSimpleStrCode(self.klineWin.model.code)
        hots = ths_orm.THS_ZS_ZD.select().where(ths_orm.THS_ZS_ZD.code == code).order_by(ths_orm.THS_ZS_ZD.day.asc()).dicts()
        maps = {}
        for d in hots:
            day = d['day'].replace('-', '')
            maps[int(day)] = d
        rs = []
        for d in data:
            fd = maps.get(d.day, None)
            if not fd:
                fd = {'day': d.day, 'zdf_50PM': 0, 'zdf_PM': 0}
            rs.append(fd)
        self.setCustomData(rs)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        iw = self.config['itemWidth']
        data = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + iw, self.height)
        if selDay == int(data['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        cdata = self.customData[idx]
        win32gui.SetTextColor(hdc, 0xcccccc)

        if cdata['zdf_50PM'] != 0:
            sy = 5
            rc = (x, sy, x + iw, sy + 16)
            win32gui.DrawText(hdc, f"{cdata['zdf_50PM'] :<3d}", -1, rc, win32con.DT_CENTER) #  | win32con.DT_VCENTER | win32con.DT_SINGLELINE

        if cdata['zdf_PM'] != 0:
            sy = 25
            rc = (x, sy, x + iw, sy + 16)
            win32gui.DrawText(hdc, f"{cdata['zdf_PM'] :<3d}", -1, rc, win32con.DT_CENTER) 

class TckIndicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 50
        if 'itemWidth' not in config:
            config['itemWidth'] = 160
        super().__init__(config)
        if 'title' not in self.config:
            self.config['title'] = '[题材]'

    def setData(self, data):
        super().setData(data)
        if not self.klineWin.model:
            self.setCustomData(None)
            return
        code = self.getSimpleStrCode(self.klineWin.model.code)
        hots = tck_orm.THS_ZT.select().where(tck_orm.THS_ZT.code == code).order_by(tck_orm.THS_ZT.day.asc()).dicts()
        maps = {}
        for d in hots:
            day = d['day'].replace('-', '')
            maps[int(day)] = d
        rs = []
        for d in data:
            fd = maps.get(d.day, None)
            if not fd:
                fd = {'day': d.day, 'ztReason': ''}
            rs.append(fd)
        self.setCustomData(rs)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        iw = self.config['itemWidth']
        cdata = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + iw, self.height)
        if selDay == int(cdata['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        win32gui.SetTextColor(hdc, 0xcccccc)
        rc = (x + 3, 3, x + iw - 3, self.height)
        win32gui.DrawText(hdc, cdata['ztReason'], -1, rc, win32con.DT_CENTER | win32con.DT_WORDBREAK) #  | win32con.DT_VCENTER | win32con.DT_SINGLELINE

class KLineSelTipWindow(base_win.BaseWindow):
    def __init__(self, klineWin) -> None:
        super().__init__()
        self.klineWin = klineWin
        klineWin.addNamedListener('selIdx.changed', self.onSelIdxChanged)

    def onSelIdxChanged(self, evt, args):
        self.invalidWindow()

    def onDraw(self, hdc):
        selIdx = self.klineWin.selIdx
        model = self.klineWin.model
        rc = (0, 0, *self.getClientSize())
        self.drawer.drawRect(hdc, rc, 0x0000dd)
        if selIdx < 0 or (not model) or (not model.data) or selIdx >= len(model.data):
            return
        d = model.data[selIdx]
        amx = d.amount / 100000000
        if amx >= 1000:
            am = f'{int(amx)}'
        elif amx > 100:
            am = f'{amx :.1f}'
        else:
            am =  f'{amx :.2f}'
        txt = f'涨幅\n{getattr(d, "zhangFu", 0):.2f}%\n\n成交额\n{am}亿' # 时间\n{d.day//10000}\n{d.day%10000:04d}\n\n
        if hasattr(d, 'rate'):
            txt += f'\n\n换手率\n{d.rate :.1f}%'
        self.drawer.drawText(hdc, txt, rc, 0xd0d0d0, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_WORDBREAK)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_NCHITTEST:
            return win32con.HTCAPTION
        return super().winProc(hwnd, msg, wParam, lParam)

class KLineWindow(base_win.BaseWindow):
    LEFT_MARGIN, RIGHT_MARGIN = 0, 70

    def __init__(self):
        super().__init__()
        self.model = None
        self.dateType = 'day'
        self.models = {} # {'day': , 'week': xx, 'month': xx}
        self.showSelTip = True # 是否显示选中K线时的竖向提示框
        self.showCodeName = True # 显示代码，名称的提示
        self.klineWidth = 8 # K线宽度
        self.klineSpace = 2 # K线之间的间距离
        self.selIdx = -1
        self.mouseXY = None
        self.indicators = []
        idt = KLineIndicator({'height': -1, 'margins': (30, 20)})
        idt.init(self)
        self.indicators.append(idt)
        self.klineIndicator = idt

    def addIndicator(self, indicator : Indicator):
        indicator.init(self)
        self.indicators.append(indicator)
        self.calcIndicatorsRect()

    # indicator = 'rate' | 'amount'
    def addDefaultIndicator(self, name):
        if 'rate' in name:
            idt = RateIndicator({'height': 60, 'margins': (15, 2)})
            self.indicators.append(idt)
            idt.init(self)
        if 'amount' in name:
            idt = AmountIndicator({'height': 60, 'margins': (15, 2)})
            self.indicators.append(idt)
            idt.init(self)
        self.calcIndicatorsRect()

    def setMarkDay(self, day):
        self.klineIndicator.setMarkDay(day)

    def calcIndicatorsRect(self):
        if not self.hwnd:
            return
        w, h = self.getClientSize()
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
        self.selIdx = -1
        self.dateType = 'day'
        self.model = model
        self.models = {}
        self.hygn = None
        if not model:
            for idt in self.indicators:
                idt.setData(None)
            return
        self.model.calcMA(5)
        self.model.calcMA(10)
        self.model.calcZDT()
        self.model.calcZhangFu()
        gntcObj = ths_orm.THS_GNTC.get_or_none(code = str(self.model.code))
        self.model.hy = []
        self.model.gn = []
        if gntcObj and gntcObj.hy:
            self.model.hy = gntcObj.hy.split('-')
            if len(self.model.hy) == 3:
                del self.model.hy[0]
        if gntcObj and gntcObj.hy:
            self.model.gn = gntcObj.gn.replace('【', '').replace('】', '').split(';')
        for idt in self.indicators:
            idt.setData(self.model.data)
        self.models['day'] = self.model

    def _mergeItem(self, dest, item):
        if hasattr(item, 'high'):
            dest.high = max(getattr(dest, 'high', 0), item.high)
        if hasattr(item, 'low'):
            dest.low = min(getattr(dest, 'low', 99999999), item.low)
        if hasattr(item, 'close'):
            dest.close = item.close
        if hasattr(item, 'amount'):
            dest.amount = getattr(dest, 'amount', 0) + item.amount
        if hasattr(item, 'vol'):
            dest.vol = getattr(dest, 'vol', 0) + item.vol
        if hasattr(item, 'rate'):
            dest.rate = getattr(dest, 'rate', 0) + item.rate
        dest.days += 1

    def _copyItem(self, item):
        it = copy.copy(item)
        EX = ('MA5', 'MA10', 'zhangFu', 'lbs', 'zdt', 'tdb')
        for k in EX:
            if hasattr(it, k):
                delattr(it, k)
        it.days = 1
        return it

    def initWeekModelData(self, ds):
        rs = []
        cur = None
        for item in ds:
            dd = datetime.date(item.day // 10000, item.day // 100 % 100, item.day % 100)
            if cur == None or dd.weekday() == 0:
                cur = self._copyItem(item)
                rs.append(cur)
            else:
                self._mergeItem(cur, item)
        return rs

    def initMonthModelData(self, ds):
        rs = []
        cur = None
        for item in ds:
            if cur == None or item.day // 100 != cur.day // 100:
                cur = self._copyItem(item)
                rs.append(cur)
            else:
                self._mergeItem(cur, item)
        return rs

    # dateType = 'day' 'week'  'month'
    def changeDateModel(self, dateType):
        if self.dateType == dateType:
            return
        self.dateType = dateType
        if dateType not in self.models:
            md = copy.copy(self.models['day'])
            if dateType == 'week':
                md.data = self.initWeekModelData(md.data)
            elif dateType == 'month':
                md.data = self.initMonthModelData(md.data)
            md.calcMA(5)
            md.calcMA(10)
            md.calcZhangFu()
            self.models[dateType] = md
        else:
            md = self.models[dateType]
        self.model = md
        for idt in self.indicators:
            idt.setData(md.data)
        self.makeVisible(-1)
        self.selIdx = len(md.data) - 1
        x = self.klineIndicator.getCenterX(self.selIdx)
        self.mouseXY = (x, self.mouseXY[1])
        self.invalidWindow()

    def onContextMenu(self, x, y):
        selDay = 0
        if self.selIdx >= 0:
            selDay = self.model.data[self.selIdx].day
            if isinstance(selDay, str):
                selDay = selDay.replace('-', '')
                selDay = int(selDay)
        mm = [{'title': '日线', 'name': 'day', 'enable': 'day' != self.dateType}, 
              {'title': '周线', 'name': 'week', 'enable': 'week' != self.dateType}, 
              {'title': '月线', 'name': 'month', 'enable': 'month' != self.dateType},
              {'title': 'LINE'},
              {'title': '标记日期', 'name': 'mark-day', 'enable': selDay > 0},
              ]
        menu = base_win.PopupMenuHelper.create(self.hwnd, mm)
        def onMM(evt, args):
            name = evt.item['name']
            if name in ('day', 'week', 'month'):
                self.changeDateModel(name)
            elif name == 'mark-day':
                base_win.ThsShareMemory.instance().writeMarkDay(selDay)
        menu.addNamedListener('Select', onMM)
        menu.show(* win32gui.GetCursorPos())

    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className = 'STATIC', title = ''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.calcIndicatorsRect()
        if self.showSelTip:
            self.createTipWindow(self.hwnd)
            
    def createTipWindow(self, parentWnd, rect = None, style = win32con.WS_POPUP | win32con.WS_VISIBLE):
        selTipWin = KLineSelTipWindow(self)
        if rect == None:
            prc = win32gui.GetWindowRect(self.hwnd)
            rect = (prc[0] + 10, prc[1] + 80, 80, 140)
        selTipWin.createWindow(self.hwnd, rect, style) # win32con.WS_CAPTION |
    
    # @return True: 已处理事件,  False:未处理事件
    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            self.makeVisible(self.selIdx)
            return True
        if msg == win32con.WM_MOUSEMOVE:
            self.onMouseMove(lParam & 0xffff, (lParam >> 16) & 0xffff)
            self.notifyListener(self.Event('MouseMove', self, x = lParam & 0xffff, y = (lParam >> 16) & 0xffff))
            return True
        if msg == win32con.WM_KEYDOWN:
            keyCode = lParam >> 16 & 0xff
            self.onKeyDown(keyCode)
            self.notifyListener(self.Event('KeyDown', self, keyCode = keyCode))
            return True
        if msg == win32con.WM_LBUTTONDOWN:
            win32gui.SetFocus(self.hwnd)
            return True
        if msg == win32con.WM_LBUTTONDBLCLK:
            #x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            si = self.selIdx
            if si >= 0:
                self.notifyListener(self.Event('DbClick', self, idx = si, data = self.model.data[si], code = self.model.code))
            return True
        if msg == win32con.WM_RBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.onContextMenu(x, y)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

    def updateAttr(self, attrName, attrVal):
        if not self.model:
            return
        if attrName == 'selIdx' and self.selIdx != attrVal:
            self.selIdx = attrVal
            data = self.model.data[attrVal] if attrVal >= 0 else None
            self.notifyListener(self.Event('selIdx.changed', self, selIdx = attrVal, data = data))
            win32gui.InvalidateRect(self.hwnd, None, True)
        
    def onMouseMove(self, x, y):
        si = self.klineIndicator.getIdxAtX(x)
        if si < 0:
            return
        x = self.klineIndicator.getCenterX(si)
        if x < 0:
            return
        if self.selIdx == si and self.mouseXY and y == self.mouseXY[1]:
            return
        self.mouseXY = (x, y)
        self.updateAttr('selIdx', si)
        win32gui.InvalidateRect(self.hwnd, None, True)

    def setSelIdx(self, idx):
        if not self.indicators:
            return
        idt = self.klineIndicator
        if not idt.visibleRange or idx < 0 or idx >= idt.visibleRange[1]:
            return
        data = self.model.data[idx]
        x = idt.getCenterX(idx)
        y = idt.getYAtValue(data.close) + idt.y
        self.mouseXY = (x, y)
        self.updateAttr('selIdx', idx)

    def onKeyDown(self, keyCode):
        if keyCode == 73: # page up
            pass
        elif keyCode == 81: # page down
            pass
        elif keyCode == 75: # left arrow key
            if self.selIdx > 0:
                ni = self.selIdx - 1
                self.setSelIdx(ni)
        elif keyCode == 77: # right arrow key
            if self.klineIndicator.visibleRange and self.selIdx < self.klineIndicator.visibleRange[1] - 1:
                ni = self.selIdx + 1
                self.setSelIdx(ni)
        elif keyCode == 72: # up arrow key
            self.klineWidth += 2
            if self.klineWidth // 2 > self.klineSpace:
                self.klineSpace = min(self.klineSpace + 1, 2)
            if self.selIdx >= 0:
                self.makeVisible(self.selIdx)
                x = self.klineIndicator.getCenterX(self.selIdx)
                self.mouseXY = (x, self.mouseXY[1])
            win32gui.InvalidateRect(self.hwnd, None, True)
        elif keyCode == 80: # down arrow key
            self.klineWidth = max(self.klineWidth - 2, 1)
            if self.klineWidth // 2 < self.klineSpace:
                self.klineSpace = max(self.klineSpace - 1, 0)
            if self.selIdx >= 0:
                self.makeVisible(self.selIdx)
                x = self.klineIndicator.getCenterX(self.selIdx)
                self.mouseXY = (x, self.mouseXY[1])
            win32gui.InvalidateRect(self.hwnd, None, True)
        elif keyCode == 28:
            ks = ('day', 'week', 'month')
            idx = (ks.index(self.dateType) + 1) % len(ks)
            self.changeDateModel(ks[idx])

    def makeVisible(self, idx):
        self.calcIndicatorsRect()
        idt : Indicator = None
        for idt in self.indicators:
            idt.calcVisibleRange(idx)
            vr = idt.visibleRange
            if vr:
                idt.calcValueRange(*vr)
        win32gui.InvalidateRect(self.hwnd, None, True)

    def drawSelDayTip(self, hdc, pens, hbrs):
        if self.selIdx < 0 or (not self.model) or (not self.model.data) or self.selIdx >= len(self.model.data):
            return
        if not self.indicators:
            return
        it : Indicator = self.klineIndicator
        if not hasattr(it, 'y'):
            return
        cx = it.getCenterX(self.selIdx)
        SEL_DAY_WIDTH_HALF = 30
        sy = it.y + it.height + it.getMargins(1) + 1
        rc = (cx - SEL_DAY_WIDTH_HALF , sy, cx + SEL_DAY_WIDTH_HALF, sy + 14)
        d = self.model.data[self.selIdx]
        day = f'{d.day}'
        day = day[4 : 6] + '-' + day[6 : ] # day[0 : 4] + '-' + 
        win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        win32gui.SetTextColor(hdc, 0xdddddd)
        win32gui.DrawText(hdc, day, len(day), rc, win32con.DT_CENTER)

    def drawCodeInfo(self, hdc, pens, hbrs):
        if not self.model:
            return
        code = self.model.code
        name = self.model.name
        # draw gn hy
        gnhy = '【' + ' - '.join(getattr(self.model, "hy", [])) + '】' + '│'.join(getattr(self.model, "gn", []))
        rc = (0, 0, int(self.getClientSize()[0] * 0.7), 70)
        font = self.drawer.getFont('宋体', 12)
        self.drawer.use(hdc, font)
        self.drawer.drawText(hdc, gnhy, rc, 0x00cc00, win32con.DT_LEFT | win32con.DT_EDITCONTROL | win32con.DT_WORDBREAK)
        
        if self.showCodeName:
            sdc = win32gui.SaveDC(hdc)
            font = self.drawer.getFont('黑体', 16, 900)
            tip = f'{code}  {name}'
            w = self.getClientSize()[0]
            sx = int(w* 0.65)
            rc = (sx, 0, sx + 250, 30)
            self.drawer.use(hdc, font)
            self.drawer.drawText(hdc, tip, rc, 0x0000ff)
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
        pens['yellow2'] = win32gui.CreatePen(win32con.PS_SOLID, 2, 0x00ffff)
        pens['0xff00ff'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xff00ff)
        pens['dark_red'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x0000aa) # 暗红色
        pens['dark_red2'] = win32gui.CreatePen(win32con.PS_SOLID, 2, 0x0000aa) # 暗红色
        pens['bk_dot_red'] = win32gui.CreatePen(win32con.PS_DOT, 1, 0x000055) # 背景虚线
        pens['blue_dash_dot'] = win32gui.CreatePen(win32con.PS_DASHDOT, 1, 0xdd5555)
        pens['light_drak_dash_dot'] = win32gui.CreatePen(win32con.PS_DASHDOT, 1, 0x606060)

        hbrs['white'] = win32gui.CreateSolidBrush(0xffffff)
        hbrs['drak'] = win32gui.CreateSolidBrush(0x202020)
        hbrs['red'] = win32gui.CreateSolidBrush(0x0000ff)
        hbrs['green'] = win32gui.CreateSolidBrush(0x00ff00)
        hbrs['light_green'] = win32gui.CreateSolidBrush(0xfcfc54)
        hbrs['blue'] = win32gui.CreateSolidBrush(0xff0000)
        hbrs['yellow'] = win32gui.CreateSolidBrush(0x00ffff)
        hbrs['black'] = win32gui.CreateSolidBrush(0x000000)
        hbrs['0xff00ff'] = win32gui.CreateSolidBrush(0xff00ff)
        hbrs['light_dark'] = win32gui.CreateSolidBrush(0x202020)
        
        w, h = self.getClientSize()
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
        win32gui.SelectObject(hdc, pens['yellow'])
        win32gui.MoveToEx(hdc, 0, h - 2)
        win32gui.LineTo(hdc, w, h - 2)
        self.drawMouse(hdc, pens)
        #self.drawSelTip(hdc, pens, hbrs)
        self.drawCodeInfo(hdc, pens, hbrs)
        self.drawSelDayTip(hdc, pens, hbrs)

        if self.mouseXY:
            self.drawTipPrice(hdc, self.mouseXY[1], pens, hbrs)
        for k in pens:
            win32gui.DeleteObject(pens[k])
        for k in hbrs:
            win32gui.DeleteObject(hbrs[k])

        # draw day | week | month
        cf = self.klineIndicator
        y = cf.getMargins(1) + cf.height
        title = {'day': '日线', 'week': '周线', 'month': '月线'}
        title = '【' + title[self.dateType] + '】'
        self.drawer.use(hdc, self.drawer.getFont(fontSize = 18))
        rc = (5, y, 100, y + 30)
        self.drawer.drawText(hdc, title, rc, color = 0x00dddd, align = win32con.DT_LEFT)

        if self.selIdx > 0 and self.model and self.selIdx < len(self.model.data):
            cur = self.model.data[self.selIdx]
            pre = self.model.data[self.selIdx - 1]
            lb = cur.amount / pre.amount # 量比
            rc = (0, 0, cf.width, 20)
            self.drawer.use(hdc, self.drawer.getFont(fontSize = 14))
            zf = cf.refZSDrawer.getZhangFu(cur.day)
            if zf is None:
                zf = '--'
            else:
                zf = f'{zf :+.02f}%'
            title = f'指数({zf}) 同比({lb :.1f})'
            self.drawer.drawText(hdc, title, rc, color = 0x00dddd, align = win32con.DT_RIGHT)

    def drawMouse(self, hdc, pens):
        if not self.mouseXY:
            return
        x, y = self.mouseXY
        w, h = self.getClientSize()
        for it in self.indicators:
            if isinstance(it, CustomIndicator):
                h = it.y - 2
                break
        wp = win32gui.CreatePen(win32con.PS_DOT, 1, 0xffffff)
        win32gui.SelectObject(hdc, wp)
        win32gui.MoveToEx(hdc, self.LEFT_MARGIN, y)
        win32gui.LineTo(hdc, w, y)
        win32gui.MoveToEx(hdc, x, self.klineIndicator.getMargins(1))
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
        w = self.getClientSize()[0]
        H = 16
        rc = (w - self.RIGHT_MARGIN + 10 + 1, y - H // 2, w, y + H // 2)
        hb = win32gui.CreateSolidBrush(0x800040)
        win32gui.FillRect(hdc, rc, hb)
        win32gui.DrawText(hdc, val['fmtVal'], len(val['fmtVal']), rc, win32con.DT_CENTER)
        win32gui.DeleteObject(hb)

class CodeWindow(ext_win.CellRenderWindow):
    def __init__(self) -> None:
        super().__init__((80, '1fr'), 5)
        self.curCode = None
        self.data = None
        self.cacheData = {}
        base_win.ThreadPool.start()
        self.init()
    
    def getCell(self, rowInfo, idx):
        cell = {'text': '', 'color': 0xcccccc, 'textAlign': win32con.DT_LEFT, 'fontSize': 15}
        if not self.data:
            return cell
        name = rowInfo['name']
        val = self.data.get(name, None)
        if val == None:
            cell['text'] = '--'
            return cell
        if name == '委比': cell['text'] = f'{int(val)} %'
        elif '市值' in name: cell['text'] = f'{val // 100000000}' + ' 亿'
        elif '市盈率' in name:
            if val < 0: cell['text'] = '亏损'
            else: cell['text'] = f'{int(val)}'
        elif '涨幅' == name: cell['text'] = f'{val :.2f} %'
        else: cell['text'] = str(val)

        if name == '涨幅' or name == '委比' or '市盈率' in name:
            cell['color'] = 0x0000ff if int(val) >= 0 else 0x00ff00
        return cell
    
    def getCodeCell(self, rowInfo, idx):
        cell = {'text': '', 'color': 0x5050ff, 'textAlign': win32con.DT_CENTER, 'fontSize': 15, 'fontWeight': 1000, 'span': 2}
        if not self.data:
            return cell
        if rowInfo['name'] == 'code':
            code = self.data.get('code', None)
            cell['text'] = code
        else:
            name = self.data.get('name', None)
            cell['text'] = name
        return cell

    def init(self):
        RH = 25
        self.addRow({'height': 25, 'margin': 20, 'name': 'code'}, self.getCodeCell)
        self.addRow({'height': 25, 'margin': 5, 'name': 'name'}, self.getCodeCell)
        KEYS = ('涨幅', '委比', '流通市值', '总市值', '市盈率_静', '市盈率_TTM')
        for k in KEYS:
            self.addRow({'height': RH, 'margin': 5, 'name': k}, {'text': k, 'color': 0xcccccc}, self.getCell)

    def loadZS(self, code):
        name = ths_orm.THS_ZS_ZD.select(ths_orm.THS_ZS_ZD.name).where(ths_orm.THS_ZS_ZD.code == code).scalar()
        self.data = {'code': self.curCode, 'name': name}
        self.invalidWindow()

    def loadCodeBasic(self, code):
        if code[0] == '8':
            self.loadZS(code)
            return
        url = cls.ClsUrl()
        data = url.loadBasic(code)
        data['code'] = code
        self.cacheData[code] = data
        self._useCacheData(code)

    def _useCacheData(self, code):
        if code != self.curCode or code not in self.cacheData:
            return
        self.data = self.cacheData[code]
        self.invalidWindow()
        
    def changeCode(self, code):
        scode = f'{code :06d}' if type(code) == int else code
        if (self.curCode == scode) or (not scode):
            return
        self.curCode = scode
        self.data = None
        #if len(scode) != 6 or (scode[0] not in ('0', '3', '6')):
        #    self.invalidWindow()
        #    return
        if scode in self.cacheData:
            self._useCacheData(scode)
        else:
            base_win.ThreadPool.addTask(scode, self.loadCodeBasic, scode)

class KLineCodeWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0x101010
        self.layout = None
        self.klineWin = KLineWindow()
        self.klineWin.showSelTip = True
        self.klineWin.showCodeName = False
        self.codeWin = CodeWindow()
        self.codeList = None
        self.code = None
        self.idxCodeList = 0
        self.idxCodeWin = None

    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title = ''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.layout = base_win.GridLayout(('100%', ), ('1fr', 150), (5, 5))
        self.klineWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.layout.setContent(0, 0, self.klineWin)
        self.codeWin.createWindow(self.hwnd, (0, 0, 150, 280))

        rightLayout = base_win.AbsLayout()
        rightLayout.setContent(0, 0, self.codeWin)
        btn = base_win.Button({'title': '<<', 'name': 'LEFT'})
        btn.createWindow(self.hwnd, (0, 0, 40, 30))
        btn.addNamedListener('Click', self.onLeftRight)
        rightLayout.setContent(0, 300, btn)
        btn = base_win.Button({'title': '>>', 'name': 'RIGHT'})
        btn.createWindow(self.hwnd, (0, 0, 40, 30))
        btn.addNamedListener('Click', self.onLeftRight)
        rightLayout.setContent(110, 300, btn)
        self.idxCodeWin = base_win.Label()
        self.idxCodeWin.createWindow(self.hwnd, (0, 0, 70, 30))
        self.idxCodeWin.css['textAlign'] |= win32con.DT_CENTER
        rightLayout.setContent(40, 300, self.idxCodeWin)
        self.layout.setContent(0, 1, rightLayout)
        self.layout.resize(0, 0, *self.getClientSize())

    def _getCode(self, d):
        if type(d) == dict:
            return d.get('code', None) or d.get('secu_code', None)
        if type(d) == str:
            return d
        if type(d) == int:
            return f'{d :06d}'
        return d

    def _findIdx(self):
        for idx, d in enumerate(self.codeList):
            if self._getCode(d) == self.code:
                return idx
        return -1

    def onLeftRight(self, evt, args):
        if not self.codeList or not self.code:
            return
        idx = self._findIdx()
        if evt.info['name'] == 'LEFT':
            if idx == 0: return
            idx -= 1
        else:
            if idx == len(self.codeList) - 1: return
            idx += 1
        cur = self.codeList[idx]
        self.changeCode(self._getCode(cur))

    # nameOrObj : str = 'rate amount'
    # nameOrObj : Indicator
    def addIndicator(self, nameOrObj):
        if isinstance(nameOrObj, str):
            self.klineWin.addDefaultIndicator(nameOrObj)
        if isinstance(nameOrObj, Indicator):
            self.klineWin.addIndicator(nameOrObj)

    def changeCode(self, code):
        self.code = code
        self.codeWin.changeCode(code)
        if type(code) == int:
            code = f'{code :06d}'
        if code[0] == '8':
            model = KLineModel_Ths(code)
        else:
            model = KLineModel_Cls(code)
        model.loadDataFile()
        self.klineWin.setModel(model)
        self.klineWin.makeVisible(-1)
        self.klineWin.invalidWindow()
        self.updateCodeIdx()
    
    def updateCodeIdx(self):
        if not self.codeList:
            self.idxCodeWin.setText('')
            return
        idx = self._findIdx()
        if idx >= 0:
            self.idxCodeWin.setText(f'{idx + 1} / {len(self.codeList)}')

    # codes = [ str, str, ... ]  |  [ int, int, ... ]
    #         [ {'code':xxx, }, ... ]  | [ {'secu_code':xxx, }, ... ]
    def setCodeList(self, codes):
        self.codeList = codes
        self.idxCodeList = 0
        self.updateCodeIdx()

if __name__ == '__main__':
    sm = base_win.ThsShareMemory.instance()
    sm.open()
    win = KLineCodeWindow()
    win.addIndicator('rate amount')
    win.addIndicator(DayIndicator({'height': 20}))
    win.addIndicator(HotIndicator()) # {'height' : 50}
    win.addIndicator(TckIndicator()) # {'height' : 50}
    rect = (0, 0, 1550, 750)
    win.createWindow(None, rect, win32con.WS_VISIBLE | win32con.WS_OVERLAPPEDWINDOW)
    win.changeCode('002085') # cls82475 002085 603390 002085 002869
    win32gui.PumpMessages()