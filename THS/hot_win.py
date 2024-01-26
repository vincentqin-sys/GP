import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os
from multiprocessing import Process
from PIL import Image  # pip install pillow
import orm, THS.hot_win_small as hot_win_small, base_win, ths_win

class HotWindow(base_win.BaseWindow):
    #  HOT(热度)  LHB(龙虎榜) LS_INFO(两市信息) DDLR（大单流入） ZT_FUPAN(涨停复盘)
    DATA_TYPE = ('HOT', 'LHB', 'LS_INFO', 'DDLR') 

    def __init__(self):
        super().__init__()
        self.oldProc = None
        self.rect = None  # 窗口大小 (x, y, w, h)
        self.maxMode = True #  是否是最大化的窗口
        self.hotData = None # 热点数据
        self.lhbData = None # 龙虎榜数据
        self.ddlrData = None # 大单流入数据
        self.lsInfoData = None # 两市信息
        self.ztFuPanData = None # 涨停复盘
        self.dataType = HotWindow.DATA_TYPE[0]
        self.selectDay = '' # YYYY-MM-DD

    def createWindow(self, topHwnd):
        rr = win32gui.GetClientRect(topHwnd)
        print('THS top window: ', rr)
        HEIGHT = 265 #285
        x = 0
        y = rr[3] - rr[1] - HEIGHT + 20
        #w = rr[2] - rr[0]
        w = win32api.GetSystemMetrics(0) # desktop width
        self.rect = (x, y, w, HEIGHT)
        style = (win32con.WS_VISIBLE | win32con.WS_POPUP)  # | win32con.WS_CAPTION & ~win32con.WS_SYSMENU | win32con.WS_BORDER | 
        super().createWindow(topHwnd, self.rect, style, title='HOT-Window')
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        win32gui.SendMessage(self.hwnd, win32con.WM_PAINT)
        self.changeMode()

    def destroy(self):
        win32gui.DestroyWindow(self.hwnd)
    
    def onDraw(self):
        hdc, ps = win32gui.BeginPaint(self.hwnd)
        bk = win32gui.CreateSolidBrush(0xffffff)
        win32gui.FillRect(hdc, win32gui.GetClientRect(self.hwnd), bk)
        win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
        win32gui.SetTextColor(hdc, 0x0)
        a = win32gui.LOGFONT()
        a.lfHeight = 12
        a.lfFaceName = '新宋体'
        font = win32gui.CreateFontIndirect(a)
        win32gui.SelectObject(hdc, font)
        if self.maxMode:
            self.drawDataType(hdc)
        else:
            self.drawMinMode(hdc)
        win32gui.EndPaint(self.hwnd, ps)
        win32gui.DeleteObject(font)
        win32gui.DeleteObject(bk)

    def drawDataType(self, hdc):
        DEFAULT_ITEM_WIDTH = 120
        if self.dataType == "HOT" and self.hotData:
            days = [d[0]['day'] for d in self.hotData]
            self._drawDataType(hdc, days, self.hotData, DEFAULT_ITEM_WIDTH, self.drawOneDayHot)
        elif self.dataType == 'LHB' and self.lhbData:
            days = [d['day'] for d in self.lhbData]
            self._drawDataType(hdc, days, self.lhbData, DEFAULT_ITEM_WIDTH, self.drawOneDayLHB)
        elif self.dataType == 'LS_INFO' and self.lsInfoData:
            days = [d['day'] for d in self.lsInfoData]
            self._drawDataType(hdc, days, self.lsInfoData, DEFAULT_ITEM_WIDTH, self.drawOneDayLSInfo)
        elif self.dataType == 'DDLR' and self.ddlrData:
            days = [d['day'] for d in self.ddlrData]
            self._drawDataType(hdc, days, self.ddlrData, DEFAULT_ITEM_WIDTH - 30, self.drawOneDayDDLR)
        elif self.dataType == 'ZT_FUPAN' and self.ztFuPanData:
            days = [d['day'] for d in self.ztFuPanData]
            self._drawDataType(hdc, days, self.ztFuPanData, DEFAULT_ITEM_WIDTH, self.drawOneDayZTFuPan)

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

    def drawArrowTip(self, hdc, x, y, op, color = 0xff0000):
        sdc = win32gui.SaveDC(hdc)
        br = win32gui.CreateSolidBrush(color)
        win32gui.SelectObject(hdc, br)
        pen = win32gui.CreatePen(win32con.PS_SOLID, 1, color)
        win32gui.SelectObject(hdc, pen)
        pts = None
        CW ,CH = 5, 6
        if op == 0: # left more arrow
            pts = [(x, y), (x + CW, y - CH), (x + CW, y + CH)]
        else: # right more arrow
            pts = [(x, y), (x - CW, y - CH), (x - CW, y + CH)]
        win32gui.Polygon(hdc, pts)
        win32gui.RestoreDC(hdc, sdc)
        win32gui.DeleteObject(br)
        win32gui.DeleteObject(pen)

    def _drawDataType(self, hdc, days, datas, itemWidth, drawOneDay, optParams = None):
        if not datas or len(datas) == 0:
            return
        x = (self.rect[2] % itemWidth) // 2
        startX = x
        pen = win32gui.CreatePen(win32con.PS_DASH, 1, 0xff0000) # day split vertical line
        startIdx, endIdx = self.findDrawDaysIndex(days, itemWidth)
        for i, data in enumerate(datas):
            if i < startIdx or i >= endIdx:
                continue
            sdc = win32gui.SaveDC(hdc)
            if data:
                drawOneDay(hdc, data, x, itemWidth, i, startIdx, endIdx, optParams)
            # draw vertical split line
            win32gui.SelectObject(hdc, pen)
            win32gui.MoveToEx(hdc, x + itemWidth, 0)
            win32gui.LineTo(hdc, x + itemWidth, self.rect[3])
            win32gui.RestoreDC(hdc, sdc)
            x += itemWidth
        if startIdx > 0:
            self.drawArrowTip(hdc, max(startX - 5, 0), self.rect[3] // 2, 0)
        if endIdx < len(datas):
            self.drawArrowTip(hdc, min(x + 5, self.rect[2]), self.rect[3] // 2, 1)
        win32gui.DeleteObject(pen)

    def drawOneDayLHB(self, hdc, data, x, itemWidth, *args): # data = {'day': '', 'famous': [] }
        y = 0
        WIDTH, HEIGHT = itemWidth, 14
        day = data['day']
        sdc = self.drawDayTitle(hdc, x, day, itemWidth)

        y += 10
        flag = True
        for d in data['famous']:
            y += HEIGHT
            if flag and ('-' == d[0]):
                flag = False
                y += 10
            win32gui.DrawText(hdc, d, len(d), (x + 5, y, x + WIDTH, y + HEIGHT), win32con.DT_LEFT)

    def drawOneDayHot(self, hdc, data, x, itemWidth, *args): # data = [ {day:'', time:'', hotValue:xx, hotOrder: '' }, ... ]
        if not data or len(data) == 0:
            return
        pen2 = win32gui.CreatePen(win32con.PS_DOT, 1, 0x0000ff) # split one day hor-line
        win32gui.SelectObject(hdc, pen2)
        y = 0
        WIDTH, HEIGHT = itemWidth, 14
        day = data[0]['day']
        sdc = self.drawDayTitle(hdc, x, day, itemWidth)
        isDrawSplit = False
        for d in data:
            y += HEIGHT
            row = '%s  %3d万  %3d' % (d['time'], d['hotValue'], d['hotOrder'])
            win32gui.DrawText(hdc, row, len(row), (x, y, x + WIDTH, y + HEIGHT), win32con.DT_CENTER)
            if d['time'] >= '13:00' and (not isDrawSplit):
                isDrawSplit = True
                win32gui.MoveToEx(hdc, x + 5, y - 2)
                win32gui.LineTo(hdc, x + WIDTH - 5, y - 2)
        win32gui.DeleteObject(pen2)

    # day = int, str(8), str(10)
    def drawDayTitle(self, hdc, x, day, itemWidth):
        WIDTH, HEIGHT = itemWidth, 14
        day = self.formatDay(day)
        ds = time.strptime(day, '%Y-%m-%d')
        wd = datetime.date(ds[0], ds[1], ds[2]).isoweekday()
        WDS = '一二三四五六日'
        title = day + ' ' + WDS[wd - 1]
        sdc = 0
        if day == self.selectDay:
            sdc = win32gui.SaveDC(hdc)
            win32gui.SetTextColor(hdc, 0xEE00EE)
        win32gui.DrawText(hdc, title, len(title), (x, 0, x + WIDTH, HEIGHT), win32con.DT_CENTER)
        return sdc

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

    def drawOneDayLSInfo(self, hdc, data, x, itemWidth, *args):
        idx, startIdx, endIdx, *_ = args
        if idx <= 0:
            return
        day = data['day']
        sdc = self.drawDayTitle(hdc, x, day, itemWidth)
        #info = '  排名: ' + str(data['pm'])
        #win32gui.DrawText(hdc, info, len(info), (x, 20, x + itemWidth, 80), win32con.DT_LEFT)

        startY, endY = 60, self.rect[3] - 40
        hbrRed = win32gui.CreateSolidBrush(0x0000ff)
        hbrGreen = win32gui.CreateSolidBrush(0x00ff00)
        hbrBlue = win32gui.CreateSolidBrush(0xff0000)
        hbrYellow = win32gui.CreateSolidBrush(0x00ffff)
        hbrYellow2 = win32gui.CreateSolidBrush(0x00aaaa)
        # 涨跌数量图表
        upRate =  data['upNum'] / (data['upNum'] + data['downNum'])
        startY = 30
        spY = startY + int(upRate * (endY - startY))
        win32gui.FillRect(hdc, (x + 5, startY, x + 10, spY), hbrRed)
        win32gui.FillRect(hdc, (x + 5, spY, x + 10, endY), hbrGreen)
        # 涨跌停数量图表
        ztX, ztStartY = x + 20, startY + 30
        ztMin, ztMax = self.getRangeOf(self.lsInfoData, 'ztNum', startIdx, endIdx)
        ZT_NUM_BASE = ztMin // 2
        ztY = int(ztStartY + (1 - (data['ztNum'] - ZT_NUM_BASE) / (ztMax - ZT_NUM_BASE)) * (endY - ztStartY))
        win32gui.FillRect(hdc, (ztX, ztY, ztX + 5, endY), hbrBlue)
        info = str(data['ztNum'])
        win32gui.DrawText(hdc, info, len(info), (ztX - 10, ztY - 12, ztX + 8, ztY), win32con.DT_CENTER)
        #连板数量图表
        lbX = ztX + 15
        lbY = int(ztStartY + (1 - (data['lbNum']) / ztMax) * (endY - ztStartY))
        win32gui.FillRect(hdc, (lbX, lbY, lbX + 5, endY), hbrBlue)
        info = str(data['lbNum'])
        win32gui.DrawText(hdc, info, len(info), (lbX - 4, lbY - 12, lbX + 8, lbY), win32con.DT_CENTER)
        #最高板数量图表
        zgbX = lbX + 15
        zgbY = int(ztStartY + (1 - (data['zgb']) / ztMax) * (endY - ztStartY))
        win32gui.FillRect(hdc, (zgbX, zgbY, zgbX + 5, endY), hbrBlue)
        info = str(data['zgb'])
        win32gui.DrawText(hdc, info, len(info), (zgbX - 4, zgbY - 12, zgbX + 8, zgbY), win32con.DT_CENTER)
        #跌停数量图表
        dtX = zgbX + 15
        dtMin, dtMax = self.getRangeOf(self.lsInfoData, 'dtNum', startIdx, endIdx)
        dtMax = max(ztMax, dtMax)
        dtY = int(ztStartY + (1 - (data['dtNum']) / dtMax) * (endY - ztStartY))
        #dtY = max(dtY, ztStartY)
        win32gui.FillRect(hdc, (dtX, dtY, dtX + 5, endY), hbrYellow)
        info = str(data['dtNum'])
        win32gui.DrawText(hdc, info, len(info), (dtX - 4, dtY - 12, dtX + 8, dtY), win32con.DT_CENTER)
        #下跌超过7%的个股数量图表
        d7X = dtX + 15
        _, d7Max = self.getRangeOf(self.lsInfoData, 'down7Num', startIdx, endIdx)
        d7Max = max(d7Max, ztMax)
        d7Y = int(ztStartY + (1 - (data['down7Num']) / d7Max) * (endY - ztStartY))
        win32gui.FillRect(hdc, (d7X, d7Y, d7X + 5, endY), hbrYellow2)
        info = str(data['down7Num'])
        win32gui.DrawText(hdc, info, len(info), (d7X - 8, d7Y - 12, d7X + 15, d7Y), win32con.DT_CENTER)
        # 成交额图表
        BASE_VOL = 6000 #基准成交额为6000亿
        lsvol = max(data['amount'] - BASE_VOL, 100)
        maxVol = 100
        for i in range(startIdx, endIdx):
            maxVol = max(self.lsInfoData[i]['amount'] - BASE_VOL, maxVol)
        volY = int(startY + (1 - lsvol / maxVol) * (endY - startY))
        volX = d7X + 15
        hbr = hbrRed if data['amount'] >= 8000 else hbrGreen # 8000亿以上显示红色，以下为绿色
        win32gui.FillRect(hdc, (volX, volY, volX + 10, endY), hbr)
        info = f"{int(data['amount'])}"
        win32gui.DrawText(hdc, info, len(info), (volX - 10, volY - 12, volX + 20, volY + 30), win32con.DT_CENTER)
        info = f"{int(data['amount'] - self.lsInfoData[idx - 1]['amount']) :+d}"
        win32gui.DrawText(hdc, info, len(info), (volX - 10, endY, volX + 20, endY + 15), win32con.DT_CENTER)
        # 显示当前选中日期的图标
        if day == self.selectDay:
            hbrBlack = win32gui.CreateSolidBrush(0x000000)
            win32gui.FillRect(hdc, (x + 40, self.rect[3] - 15, x + 70, self.rect[3] - 10), hbrBlack)
            win32gui.DeleteObject(hbrBlack)
        win32gui.DeleteObject(hbrRed)
        win32gui.DeleteObject(hbrGreen)
        win32gui.DeleteObject(hbrBlue)
        win32gui.DeleteObject(hbrYellow)

    def drawOneDayDDLR(self, hdc, data, x, itemWidth, *args):
        idx, startIdx, endIdx, *_ = args
        self.drawDayTitle(hdc, x, data['day'], itemWidth)
        startY, endY = 60, self.rect[3] - 40
        hbrRed = win32gui.CreateSolidBrush(0x0000ff)
        hbrGreen = win32gui.CreateSolidBrush(0x00ff00)
        buyMin, buyMax  = self.getRangeOf(self.ddlrData, 'buy', startIdx, endIdx)
        sellMin, sellMax = self.getRangeOf(self.ddlrData, 'sell', startIdx, endIdx)
        maxVal = max(buyMax, sellMax)
        
        # buy
        spY = int(startY + (1 - (data['buy']) / maxVal) * (endY - startY))
        spX = x + 20
        win32gui.FillRect(hdc, (spX, spY, spX + 8, endY), hbrRed)
        info = f'{data["buy"] :+.1f}'
        win32gui.DrawText(hdc, info, len(info), (spX - 10, spY - 12, spX + 20, spY), win32con.DT_CENTER)
        # sell
        spX += 35
        spY = int(startY + (1 - (data['sell']) / maxVal) * (endY - startY))
        win32gui.FillRect(hdc, (spX, spY, spX + 8, endY), hbrGreen)
        info = f'{data["sell"] :.1f}'
        win32gui.DrawText(hdc, info, len(info), (spX - 10, spY - 12, spX + 20, spY), win32con.DT_CENTER)
        # rate
        if data['amount']:
            spX = x + 40
            spY = 40
            bb = max(data['buy'], data['sell'])
            rate = int(bb / data['amount'] * 100)
            rate = f'占 {rate}%'
            win32gui.DrawText(hdc, rate, len(rate), (spX - 15, spY - 12, spX + 25, spY), win32con.DT_CENTER)
        # 显示当前选中日期的图标
        if self.formatDay(data['day']) == self.selectDay:
            hbrBlack = win32gui.CreateSolidBrush(0x000000)
            sx = (itemWidth - 30) // 2 + x
            win32gui.FillRect(hdc, (sx, self.rect[3] - 15, sx + 30, self.rect[3] - 10), hbrBlack)
            win32gui.DeleteObject(hbrBlack)
        win32gui.DeleteObject(hbrRed)
        win32gui.DeleteObject(hbrGreen)
    
    def drawOneDayZTFuPan(self, hdc, data, x, itemWidth, *args):
        idx, startIdx, endIdx, *_ = args
        self.drawDayTitle(hdc, x, data['day'], itemWidth)
        info = f'{data["ztTime"]}\n\n{data["status"]}\n\n{data["ztReason"]}\n\n{data["tag"]}'
        win32gui.DrawText(hdc, info, len(info), (x, 40, x + itemWidth, 150), win32con.DT_CENTER)

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
        self.updateHotData(code)
        self.updateLHBData(code)
        self.updateLSInfoData(code)
        self.updateDDLRData(code)
        self.updateZtFuPanData(code)

    def updateLHBData(self, code):
        def gn(name : str):
            if not name: return name
            name = name.strip()
            i = name.find('(')
            if i < 0: return name
            return name[0 : i]

        ds = orm.TdxLHB.select().where(orm.TdxLHB.code == code)
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

    def updateHotData(self, code):
        def formatThsHot(thsHot):
            day = thsHot['day']
            day = f'{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}'
            t = thsHot['time']
            t = f'{t // 100: 02d}:{t % 100 :02d}'
            thsHot['day'] = day
            thsHot['time'] = t
            return thsHot

        ds = orm.THS_Hot.select().where(orm.THS_Hot.code == int(code))
        hts = [formatThsHot(d.__data__) for d in ds]
        if len(hts) > 0:
            print('Load ', code, ' Count:', len(hts))
        elif code:
            print('Load ', code , ' not find in DB')
        data = hts
        self.selectDay = None
        lastDay = None
        newDs = None
        rs = []
        for d in data:
            if lastDay != d['day']:
                lastDay = d['day']
                newDs = []
                rs.append(newDs)
            newDs.append(d)
        self.hotData = rs
        win32gui.InvalidateRect(self.hwnd, None, True)

    def updateDDLRData(self, code):
        ds = orm.THS_DDLR.select().where(orm.THS_DDLR.code == code)
        self.ddlrData = [d.__data__ for d in ds]
        for d in self.ddlrData:
            d['buy'] = d['activeIn'] + d['positiveIn']
            d['sell'] = d['activeOut'] + d['positiveOut']
        self.selectDay = None
        win32gui.InvalidateRect(self.hwnd, None, True)
    
    def updateLSInfoData(self, code):
        zsDatas = orm.TdxLSModel.select()
        codeDatas = orm.TdxVolPMModel.select().where(orm.TdxVolPMModel.code == code)
        cs = {}
        for c in codeDatas:
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

    def updateZtFuPanData(self, code):
        ds = orm.KPL_ZT_FuPan.select().where(orm.KPL_ZT_FuPan.code == code).order_by(orm.KPL_ZT_FuPan.day.asc())
        self.ztFuPanData = [d.__data__ for d in ds]
        self.selectDay = None
        win32gui.InvalidateRect(self.hwnd, None, True)

    def updateSelectDay(self, newDay):
        if not newDay or self.selectDay == newDay:
            return
        self.selectDay = newDay
        win32gui.InvalidateRect(self.hwnd, None, True)

    # @return True: 已处理事件,  False:未处理事件
    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_PAINT:
            self.onDraw()
            return True
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return True
        elif msg == win32con.WM_LBUTTONDBLCLK:
            self.changeMode()
            self.notifyListener('mode.change', {'maxMode' : self.maxMode})
            return True
        elif msg == win32con.WM_RBUTTONUP:
            self.changeDataType()
            return True
        elif msg == win32con.WM_LBUTTONDOWN:
            win32gui.SendMessage(self.hwnd, win32con.WM_NCLBUTTONDOWN, 2, 0)
            return True
        return False
