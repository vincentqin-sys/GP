import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os
from multiprocessing import Process
from PIL import Image  # pip install pillow
import orm, number_ocr
import sort_win32

# pip installl opencv-python

THS_TOP_HWND = None
THS_MAIN_HWND = None
THS_LEVEL2_CODE_HWND = None
THS_SELECT_DAY_HWND = None

ocr = number_ocr.NumberOCR()

def findLevel2CodeWnd(hwnd):
    global THS_LEVEL2_CODE_HWND
    child = win32gui.GetWindow(hwnd, win32con.GW_CHILD)
    while child:
        title = win32gui.GetWindowText(child)
        if win32gui.IsWindowVisible(child) and title and ('逐笔成交--' in title):
            THS_LEVEL2_CODE_HWND = child
            break
        findLevel2CodeWnd(child)
        if THS_LEVEL2_CODE_HWND:
            break
        child = win32gui.GetWindow(child, win32con.GW_HWNDNEXT)

def findSelectDayWnd():
    global THS_MAIN_HWND
    if not THS_MAIN_HWND:
        return None
    child = win32gui.GetWindow(THS_MAIN_HWND, win32con.GW_CHILD)
    while child:
        if win32gui.GetClassName(child) == '#32770':
            left, top, right, bottom = win32gui.GetClientRect(child)
            w, h = right - left, bottom - top
            if h / 3 > w:
                return child
        child = win32gui.GetWindow(child, win32con.GW_HWNDNEXT)
    return None

# 当前显示的窗口是否是K线图
def isInKlineWindow():
    if '技术分析' not in win32gui.GetWindowText(THS_TOP_HWND):
        return False
    return win32gui.IsWindowVisible(THS_TOP_HWND)

# 当前显示的窗口是否是分时图
def isInFenShiWindow():
    if '分时走势' not in win32gui.GetWindowText(THS_TOP_HWND):
        return False
    return win32gui.IsWindowVisible(THS_TOP_HWND)

# 当前显示的窗口是否是“我的首页”
def isInMyHomeWindow():
    if '我的首页' not in win32gui.GetWindowText(THS_TOP_HWND):
        return False
    return win32gui.IsWindowVisible(THS_TOP_HWND)

# 查找股票代码
def findCode():
    global THS_MAIN_HWND, THS_TOP_HWND, THS_LEVEL2_CODE_HWND
    if (not isInKlineWindow()) and (not isInMyHomeWindow()):
        #print('Not in KLine Window')
        return None
    # 逐笔成交明细 Level-2
    if not win32gui.IsWindowVisible(THS_LEVEL2_CODE_HWND):
        THS_LEVEL2_CODE_HWND = None
        findLevel2CodeWnd(THS_MAIN_HWND)
        #print('THS_LEVEL2_CODE_HWND = %#X' % THS_LEVEL2_CODE_HWND)
    title = win32gui.GetWindowText(THS_LEVEL2_CODE_HWND) or ''
    code = ''
    if '逐笔成交--' in title:
        code = title[6 : 12]
    return code

def getSelectDay():
    global THS_SELECT_DAY_HWND, ocr
    if not win32gui.IsWindowVisible(THS_SELECT_DAY_HWND):
        return None
    dc = win32gui.GetWindowDC(THS_SELECT_DAY_HWND)
    #mdc = win32gui.CreateCompatibleDC(dc)
    mfcDC = win32ui.CreateDCFromHandle(dc)
    saveDC = mfcDC.CreateCompatibleDC()
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, 50, 20) # image size 50 x 20
    saveDC.SelectObject(saveBitMap)

    # copy year bmp
    srcPos = (14, 20)
    srcSize = (30, 17)
    saveDC.BitBlt((0, 0), srcSize, mfcDC, srcPos, win32con.SRCCOPY)
    #saveBitMap.SaveBitmapFile(saveDC, 'SD.bmp')
    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    im_PIL = Image.frombuffer('RGB',(bmpinfo['bmWidth'], 17), bmpstr, 'raw', 'BGRX', 0, 1) # bmpinfo['bmHeight']

    selYear = ocr.match(im_PIL)
    # print('selYear=', selYear)
    
    # copy day bmp
    srcPos = (14, 38)
    saveDC.BitBlt((0, 0), srcSize, mfcDC, srcPos, win32con.SRCCOPY)
    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    im_PIL = Image.frombuffer('RGB',(bmpinfo['bmWidth'], 17), bmpstr, 'raw', 'BGRX', 0, 1) 
    selDay = ocr.match(im_PIL)
    # print('selDay=', selDay)
    # im_PIL.show()

    # destory
    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(THS_SELECT_DAY_HWND, dc)

    sd = selYear + '-' + selDay[0 : 2] + '-' + selDay[2 : 4]
    #print(sd)
    return sd


def init():
    global THS_MAIN_HWND, THS_TOP_HWND, THS_SELECT_DAY_HWND
    THS_MAIN_HWND = THS_TOP_HWND = THS_SELECT_DAY_HWND = None
    def callback(hwnd, lparam):
        title = win32gui.GetWindowText(hwnd)
        if '同花顺(v' in title:
            global THS_TOP_HWND
            THS_TOP_HWND = hwnd
        return True
    
    win32gui.EnumWindows(callback, None)
    THS_MAIN_HWND =  win32gui.FindWindowEx(THS_TOP_HWND, None, 'AfxFrameOrView140s', None)
    THS_SELECT_DAY_HWND = findSelectDayWnd()

    if (not THS_MAIN_HWND) or (not THS_TOP_HWND) or (not THS_SELECT_DAY_HWND):
        return False

    print('THS_TOP_HWND = %#X' % THS_TOP_HWND)
    print('THS_MAIN_HWND = %#X' % THS_MAIN_HWND)
    print('THS_SELECT_DAY_HWND = %#X' % THS_SELECT_DAY_HWND)
    return True

#-------------------hot  window ------------
class HotWindow:
    DATA_TYPE = ('HOT', 'LHB', 'LS_INFO') # # HOT(热度)  LHB(龙虎榜) LS_INFO(两市信息，含成交额排名) DDLR（大单流入）

    def __init__(self):
        self.oldProc = None
        self.wnd = None
        self.rect = None  # 窗口大小 (x, y, w, h)
        self.maxMode = True #  是否是最大化的窗口
        self.hotData = None # 热点数据
        self.lhbData = None # 龙虎榜数据
        self.ddlrData = None # 大单流入数据
        self.lsInfoData = None # 成交额排名
        self.dataType = 'HOT'
        self.selectDay = '' # YYYY-MM-DD

    def createHotWindow(self):
        global THS_TOP_HWND, THS_MAIN_HWND
        # WS_CLIPCHILDREN:0x02000000L
        # 0x40000000 child-win ;  0x80000000 popup-win
        rr = win32gui.GetClientRect(THS_TOP_HWND)
        print('THS top window: ', rr)
        style = 0x00800000 | 0x10000000 | win32con.WS_CHILD
        HEIGHT = 265 #285
        x = 0
        y = rr[3] - rr[1] - HEIGHT
        #w = rr[2] - rr[0]
        w = win32api.GetSystemMetrics(0) # desktop width
        self.rect = (x, y, w, HEIGHT)
        self.wnd = win32gui.CreateWindow('STATIC', 'HOT-Window', style, x, y, w, HEIGHT, THS_TOP_HWND, None, None, None)
        win32gui.SetWindowPos(self.wnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        self.oldProc = win32gui.GetWindowLong(self.wnd, -4) # GWL_WNDPROC
        win32gui.SetWindowLong(self.wnd, -4, hotWinProc)
        print('hotWnd = %#X' % self.wnd, x, y, w, HEIGHT)
        win32gui.SendMessage(self.wnd, win32con.WM_PAINT)
        self.changeMode()

    def destroy(self):
        win32gui.DestroyWindow(self.wnd)
    
    def draw(self, hwnd):
        hdc, ps = win32gui.BeginPaint(hwnd)
        bk = win32gui.CreateSolidBrush(0xffffff)
        win32gui.FillRect(hdc, win32gui.GetClientRect(hwnd), bk)
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

        win32gui.EndPaint(hwnd, ps)
        win32gui.DeleteObject(font)
        win32gui.DeleteObject(bk)
        # print('WM_PAINT')

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

    # param days: [YYYY-MM-DD, ....]
    # return [startIdx, endIdx)
    def findDrawDaysIndex(self, days, itemWidth):
        if not days:
            return (0, 0)
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

    # day = YYYY-MM-DD
    def drawDayTitle(self, hdc, x, day, itemWidth):
        WIDTH, HEIGHT = itemWidth, 14
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

    def drawOneDayLSInfo(self, hdc, data, x, itemWidth, *args):
        def getRangeOf(name):
            maxVal, minVal = 0, 0
            for i in range(startIdx, endIdx):
                v = self.lsInfoData[i][name]
                if minVal == 0 and maxVal == 0:
                    maxVal = minVal = v
                    continue
                maxVal = max(maxVal, v)
                minVal = min(minVal, v)
            return minVal, maxVal

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
        # 涨跌数量图表
        upRate =  data['upNum'] / (data['upNum'] + data['downNum'])
        startY = 30
        spY = startY + int(upRate * (endY - startY))
        win32gui.FillRect(hdc, (x + 5, startY, x + 10, spY), hbrRed)
        win32gui.FillRect(hdc, (x + 5, spY, x + 10, endY), hbrGreen)
        # 涨跌停数量图表
        ztX, ztStartY = x + 20, startY + 30
        ztMin, ztMax = getRangeOf('ztNum')
        ZT_NUM_BASE = ztMin // 2
        ztY = int(ztStartY + (1 - (data['ztNum'] - ZT_NUM_BASE) / (ztMax - ZT_NUM_BASE)) * (endY - ztStartY))
        win32gui.FillRect(hdc, (ztX, ztY, ztX + 5, endY), hbrBlue)
        info = str(data['ztNum'])
        win32gui.DrawText(hdc, info, len(info), (ztX - 4, ztY - 12, ztX + 8, ztY), win32con.DT_CENTER)
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
        dtY = int(ztStartY + (1 - (data['dtNum']) / ztMax) * (endY - ztStartY))
        win32gui.FillRect(hdc, (dtX, dtY, dtX + 5, endY), hbrYellow)
        info = str(data['dtNum'])
        win32gui.DrawText(hdc, info, len(info), (dtX - 4, dtY - 12, dtX + 8, dtY), win32con.DT_CENTER)
        # 成交额图表
        BASE_VOL = 6000 #基准成交额为6000亿
        lsvol = max(data['amount'] - BASE_VOL, 100)
        maxVol = 100
        for i in range(startIdx, endIdx):
            maxVol = max(self.lsInfoData[i]['amount'] - BASE_VOL, maxVol)
        volY = int(startY + (1 - lsvol / maxVol) * (endY - startY))
        volX = dtX + 23
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


    def drawMinMode(self, hdc):
        title = '【我的热点】'
        rr = win32gui.GetClientRect(self.wnd)
        win32gui.FillRect(hdc, win32gui.GetClientRect(self.wnd), win32con.COLOR_WINDOWFRAME)  # background black
        win32gui.SetTextColor(hdc, 0x0000ff)
        win32gui.DrawText(hdc, title, len(title), rr, win32con.DT_CENTER | win32con.DT_VCENTER)

    def changeMode(self):
        if self.maxMode:
            WIDTH, HEIGHT = 150, 20
            y = self.rect[1] + self.rect[3] - HEIGHT
            win32gui.SetWindowPos(self.wnd, 0, 0, y, WIDTH, HEIGHT, 0)
        else:
            win32gui.SetWindowPos(self.wnd, 0, self.rect[0], self.rect[1], self.rect[2], self.rect[3], 0)
        self.maxMode = not self.maxMode
        win32gui.InvalidateRect(self.wnd, None, True)

    def changeDataType(self):
        if not self.maxMode:
            return
        tp = self.DATA_TYPE
        idx = tp.index(self.dataType)
        idx = (idx + 1) % len(tp)
        self.dataType = tp[idx]
        win32gui.InvalidateRect(self.wnd, None, True)

    def updateCode(self, code):
        self.updateHotData(code)
        self.updateLHBData(code)
        self.updateLSInfoData(code)

    def updateLHBData(self, code):
        ds = orm.TdxLHB.select().where(orm.TdxLHB.code == code)
        data = []
        for d in ds:
            r = {'day': d.day, 'famous': []}
            if '累计' in d.title:
                r['famous'].append('    3日')
            famous = str(d.famous).split('//')
            if len(famous) == 2:
                for f in famous[0].strip().split(';'):
                    if f: r['famous'].append('+ ' + f.strip())
                for f in famous[1].strip().split(';'):
                    if f: r['famous'].append('- ' + f.strip())
            else:
                r['famous'].append(' 无知名游资')
            data.append(r)
        self.lhbData = data
        self.selectDay = None
        win32gui.InvalidateRect(self.wnd, None, True)

    def updateHotData(self, code):
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
        win32gui.InvalidateRect(self.wnd, None, True)

    def updateDDLRData(self, code):
        ds = orm.THS_DDLR.select().where(orm.THS_DDLR.code == code)
        self.ddlrData = [d.__data__ for d in ds]
        self.selectDay = None
        win32gui.InvalidateRect(self.wnd, None, True)
    
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
        win32gui.InvalidateRect(self.wnd, None, True)

    def updateSelectDay(self, newDay):
        if not newDay or self.selectDay == newDay:
            return
        self.selectDay = newDay
        win32gui.InvalidateRect(self.wnd, None, True)

def hotWinProc(hwnd, msg, wparam, lparam):
    global hotWindow
    if msg == win32con.WM_PAINT:
        hotWindow.draw(hwnd)
        return 0
    elif msg == win32con.WM_DESTROY:
        win32gui.PostQuitMessage(0)
        return 0
    elif msg == win32con.WM_LBUTTONDBLCLK:
        hotWindow.changeMode()
        showSortAndLiangDianWindow(not hotWindow.maxMode, True)
        return 0
    elif msg == win32con.WM_RBUTTONUP:
        hotWindow.changeDataType()
        return 0
    else:
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
        # win32gui.CallWindowProc(hotWindow.oldProc, hwnd, msg, wparam, lparam)

# show-hide sort wnd, liang dian wnd
def showSortAndLiangDianWindow(show, move):
    liangDianWnd = win32gui.FindWindow('smallF10_dlg', '小F10')
    if show:
        sort_win32.sortInfoWindow.show()
        if liangDianWnd:
            win32gui.ShowWindow(liangDianWnd, win32con.SW_SHOW)
    else:
        sort_win32.sortInfoWindow.hide()
        if liangDianWnd:
            win32gui.ShowWindow(liangDianWnd, win32con.SW_HIDE)
    if move:
        if liangDianWnd:
            win32gui.SetWindowPos(liangDianWnd, None, 560, 800, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOREDRAW | win32con.SWP_NOZORDER)
        win32gui.SetWindowPos(sort_win32.sortInfoWindow.wnd, None, 1087, 800, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOREDRAW | win32con.SWP_NOZORDER)

#----------------------------------------
hotWindow = HotWindow()
curCode = None

def formatThsHot(thsHot):
    day = str(thsHot['day'])
    day = day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 :]
    t = str(thsHot['time'])
    if len(t) < 4:
        t = '0' + t
    t = t[0 : 2] + ':' + t[2 : ]
    rt = {'day' : day, 'time': t, 'code': thsHot['code'], 'hotValue': thsHot['hotValue'], 'hotOrder': thsHot['hotOrder']}
    return rt

def work_updateCode(nowCode):
    global curCode
    try:
        icode = int(nowCode)
    except Exception as e:
        nowCode = '0'
    if curCode == nowCode:
        return
    curCode = nowCode
    hotWindow.updateCode(nowCode)
    sort_win32.sortInfoWindow.changeCode(nowCode)

def showHotWindow():
    # check window size changed
    if hotWindow.rect[1] > 0: # y > 0
        return
    rr = win32gui.GetClientRect(THS_TOP_HWND)
    y = rr[3] - rr[1] - hotWindow.rect[3]
    if y < 0:
        return
    x = hotWindow.rect[0]
    win32gui.SetWindowPos(hotWindow.wnd, 0, x, y, 0, 0, 0x0010|0x0200|0x0001|0x0004)
    hotWindow.rect = (x, y, hotWindow.rect[2], hotWindow.rect[3])

def work():
    global curCode
    while True:
        time.sleep(0.5)
        #mywin.eyeWindow.show()
        if not win32gui.IsWindow(THS_TOP_HWND):
            #win32gui.PostQuitMessage(0)
            #sys.exit(0)  #仅退出当前线程
            os._exit(0) # 退出进程
            break
        if isInKlineWindow() or isInMyHomeWindow():
            showHotWindow()
            nowCode = findCode()
            if curCode != nowCode:
                work_updateCode(nowCode)
            selDay = getSelectDay()
            if selDay:
                hotWindow.updateSelectDay(selDay)
            if (not hotWindow.maxMode) and (not isInMyHomeWindow()):
                showSortAndLiangDianWindow(True, False)
        elif isInFenShiWindow():
            if not hotWindow.maxMode:
                showSortAndLiangDianWindow(True, True)
            pass
        else:
            sort_win32.sortInfoWindow.hide()
        

def subprocess_run():
    while True:
        if init():
            break
        time.sleep(10)
    hotWindow.createHotWindow()
    sort_win32.sortInfoWindow.createWindow(THS_MAIN_HWND)
    threading.Thread(target = work).start()
    win32gui.PumpMessages()
    print('Quit Sub Process')

if __name__ == '__main__':
    while True:
        p = Process(target = subprocess_run, daemon = True)
        p.start()
        print('start a new sub process, pid=', p.pid)
        p.join()