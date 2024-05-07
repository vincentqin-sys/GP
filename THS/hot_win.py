import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os
from multiprocessing import Process
from PIL import Image  # pip install pillow

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from db import ths_orm, tdx_orm
from Common import base_win
from db import lhb_orm as lhb_orm
from db import tck_orm as tck_orm

class HotWindow(base_win.BaseWindow):
    #  HOT(热度)  LHB(龙虎榜) LS_INFO(两市信息) DDLR（大单流入） ZT_FUPAN(涨停复盘)
    DATA_TYPE = ('LHB', 'LS_INFO', 'DDLR')

    def __init__(self):
        super().__init__()
        self.rect = None  # 窗口大小 (x, y, w, h)
        self.maxMode = True #  是否是最大化的窗口
        self.hotData = None # 热点数据
        self.lhbData = None # 龙虎榜数据
        self.ddlrData = None # 大单流入数据
        self.lsInfoData = None # 两市信息
        self.ztFuPanData = None # 涨停复盘
        self.dataType = HotWindow.DATA_TYPE[0]
        self.selectDay = '' # YYYY-MM-DD

    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className = 'STATIC', title = ''):
        rr = win32gui.GetClientRect(parentWnd)
        print('THS top window: ', rr)
        HEIGHT = 265 #285
        x = 0
        y = rr[3] - rr[1] - HEIGHT + 20
        #w = rr[2] - rr[0]
        w = win32api.GetSystemMetrics(0) # desktop width
        self.rect = (x, y, w, HEIGHT)
        style = (win32con.WS_VISIBLE | win32con.WS_POPUP)
        super().createWindow(parentWnd, self.rect, style, title='HOT-Window')
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        self.changeMode()

    def onDraw(self, hdc):
        if self.maxMode:
            self.drawDataType(hdc)
        else:
            self.drawMinMode(hdc)

    def drawDataType(self, hdc):
        DEFAULT_ITEM_WIDTH = 120
        if self.dataType == 'LHB' and self.lhbData:
            pass
        elif self.dataType == 'LS_INFO' and self.lsInfoData:
            pass
        elif self.dataType == 'DDLR' and self.ddlrData:
            pass

    # format day (int, str(8), str(10)) to YYYY-MM-DD
    def formatDay(self, day):
        if type(day) == int:
            return f'{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}'
        if type(day) == str and len(day) == 8:
            return day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
        return day

    # param days : int, str(8), str(10)
    # return [startIdx, endIdx)
    def findDrawDaysIndex(self, days, itemWidth):
        if not days or len(days) == 0:
            return (0, 0)
        days = [ self.formatDay(d) for d in days ]
        width = self.rect[2]
        num = width // itemWidth
        if num == 0:
            return (0, 0)
        if len(days) <= num:
            return (0, len(days))
        if not self.selectDay:
            return (len(days) - num, len(days))
        #最左
        if self.selectDay <= days[0]:
            return (0, num)
        #最右
        if self.selectDay >= days[len(days) - 1]:
            return (len(days) - num, len(days))

        idx = 0
        for i in range(len(days) - 1): # skip last day
            if (self.selectDay >= days[i]) and (self.selectDay < days[i + 1]):
                idx = i
                break
        # 最右侧优先显示    
        #lastIdx = idx + num
        #if lastIdx > len(days):
        #    lastIdx = len(days)
        #if lastIdx - idx < num:
        #    idx -= num - (lastIdx - idx)
        #return (idx, lastIdx)

        # 居中优先显示
        fromIdx = lastIdx = idx
        while True:
            if lastIdx < len(days):
                lastIdx += 1
            if lastIdx - fromIdx >= num:
                break
            if fromIdx > 0:
                fromIdx -= 1
            if lastIdx - fromIdx >= num:
                break
        return (fromIdx, lastIdx)

    def getRangeOf(self, datas, name, startIdx, endIdx):
        maxVal, minVal = 0, 0
        for i in range(max(startIdx, 0), min(len(datas), endIdx)):
            v = datas[i][name]
            if minVal == 0 and maxVal == 0:
                maxVal = minVal = v
            else:
                maxVal = max(maxVal, v)
                minVal = min(minVal, v)
        return minVal, maxVal

    def drawMinMode(self, hdc):
        title = '【我的热点】'
        rr = win32gui.GetClientRect(self.hwnd)
        win32gui.FillRect(hdc, win32gui.GetClientRect(self.hwnd), win32con.COLOR_WINDOWFRAME)  # background black
        win32gui.SetTextColor(hdc, 0x0000ff)
        win32gui.DrawText(hdc, title, len(title), rr, win32con.DT_CENTER | win32con.DT_VCENTER)

    def changeMode(self):
        if self.maxMode:
            WIDTH, HEIGHT = 150, 20
            y = self.rect[1] + self.rect[3] - HEIGHT - 20
            x = self.rect[2] // 2
            win32gui.SetWindowPos(self.hwnd, 0, x, y, WIDTH, HEIGHT, 0)
        else:
            win32gui.SetWindowPos(self.hwnd, 0, self.rect[0], self.rect[1], self.rect[2], self.rect[3], 0)
        self.maxMode = not self.maxMode
        win32gui.InvalidateRect(self.hwnd, None, True)

    def changeDataType(self):
        if not self.maxMode:
            return
        tp = self.DATA_TYPE
        idx = tp.index(self.dataType)
        idx = (idx + 1) % len(tp)
        self.dataType = tp[idx]
        win32gui.InvalidateRect(self.hwnd, None, True)

    def updateCode(self, code):
        self.updateLHBData(code)
        self.updateLSInfoData(code)
        self.updateDDLRData(code)

    def updateLHBData(self, code):
        def gn(name : str):
            if not name: return name
            name = name.strip()
            i = name.find('(')
            if i < 0: return name
            return name[0 : i]

        ds = lhb_orm.TdxLHB.select().where(lhb_orm.TdxLHB.code == code)
        data = []
        for d in ds:
            r = {'day': d.day, 'famous': []}
            if '累计' in d.title:
                r['famous'].append('    3日')
            famous = str(d.famous).split('//')
            if len(famous) == 2:
                for f in famous[0].strip().split(';'):
                    if f: r['famous'].append('+ ' + gn(f))
                for f in famous[1].strip().split(';'):
                    if f: r['famous'].append('- ' + gn(f))
            else:
                r['famous'].append(' 无知名游资')
            data.append(r)
        self.lhbData = data
        self.selectDay = None
        win32gui.InvalidateRect(self.hwnd, None, True)

    def updateDDLRData(self, code):
        ds = ths_orm.THS_DDLR.select().where(ths_orm.THS_DDLR.code == code)
        self.ddlrData = [d.__data__ for d in ds]
        for d in self.ddlrData:
            d['buy'] = d['activeIn'] + d['positiveIn']
            d['sell'] = d['activeOut'] + d['positiveOut']
        self.selectDay = None
        win32gui.InvalidateRect(self.hwnd, None, True)
    
    def updateLSInfoData(self, code):
        zsDatas = tdx_orm.TdxLSModel.select()
        qxDatas = tck_orm.CLS_SCQX.select().dicts()
        cs = {}
        for c in qxDatas:
            cs[c.day] = c
        dd = []
        for d in zsDatas:
            day = str(d.day)
            day = day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
            cc = cs.get(d.day, None)
            pm = cc.pm if cc else '--'
            item = d.__data__
            item['day'] = day
            item['pm'] = pm
            dd.append(item)
        self.lsInfoData = dd
        self.selectDay = None
        win32gui.InvalidateRect(self.hwnd, None, True)

    def updateSelectDay(self, newDay):
        if not newDay or self.selectDay == newDay:
            return
        self.selectDay = newDay
        win32gui.InvalidateRect(self.hwnd, None, True)

    # @return True: 已处理事件,  False:未处理事件
    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return True
        elif msg == win32con.WM_LBUTTONDBLCLK:
            self.changeMode()
            self.notifyListener(self.Event('mode.change', self, maxMode = self.maxMode))
            return True
        elif msg == win32con.WM_RBUTTONUP:
            self.changeDataType()
            return True
        elif msg == win32con.WM_LBUTTONDOWN:
            win32gui.SendMessage(self.hwnd, win32con.WM_NCLBUTTONDOWN, 2, 0)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)
