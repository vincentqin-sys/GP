import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os
from multiprocessing import Process
from PIL import Image  # pip install pillow
import orm, number_ocr
import mywin

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

# 查找股票代码
def findCode():
    global THS_MAIN_HWND, THS_TOP_HWND, THS_LEVEL2_CODE_HWND
    if not isInKlineWindow():
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
    DAY_HOT_WIDTH = 120

    def __init__(self):
        self.oldProc = None
        self.wnd = None
        self.rect = None  # 窗口大小 (x, y, w, h)
        self.maxMode = True #  是否是最大化的窗口
        self.hotData = None # 热点数据
        self.lhbData = None # 龙虎榜数据
        self.dataType = 'HOT' # HOT  LHB
        self.selectDay = ''

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
            if self.dataType == "HOT":
                self.drawHot(hdc)
            elif self.dataType == 'LHB':
                self.drawLHB(hdc)
        else:
            self.drawMinMode(hdc)

        win32gui.EndPaint(hwnd, ps)
        win32gui.DeleteObject(font)
        win32gui.DeleteObject(bk)
        # print('WM_PAINT')

    # return [startIdx, endIdx)
    def findDrawDaysIndex(self, days):
        if not days:
            return (0, 0)
        width = self.rect[2]
        num = width // self.DAY_HOT_WIDTH
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
        lastIdx = idx + num
        if lastIdx > len(days):
            lastIdx = len(days)
        if lastIdx - idx < num:
            idx -= num - (lastIdx - idx)
        return (idx, lastIdx)

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

    def drawLHB(self, hdc):
        if not self.lhbData or len(self.lhbData) == 0:
            return
        x = (self.rect[2] % self.DAY_HOT_WIDTH) // 2
        startX = x
        nd = self.lhbData
        days = [d['day'] for d in self.lhbData]
        startIdx, endIdx = self.findDrawDaysIndex(days)
        for i, data in enumerate(nd):
            if i < startIdx or i >= endIdx:
                continue
            self.drawOneDayLHB(hdc, x, data)
            x += self.DAY_HOT_WIDTH
        if startIdx > 0:
            self.drawArrowTip(hdc, max(startX - 5, 0), self.rect[3] // 2, 0)
        if endIdx < len(self.lhbData):
            self.drawArrowTip(hdc, min(x + 5, self.rect[2]), self.rect[3] // 2, 1)
        self.drawLHBSelectTip(hdc, days[startIdx : endIdx])

    def drawLHBSelectTip(self, hdc, showDays):
        if (not self.selectDay) or len(showDays) == 0 or (self.selectDay in showDays):
            return
        idx = -1
        for i in range(0, len(showDays)):
            if showDays[i] < self.selectDay:
                idx = i
        x = idx * self.DAY_HOT_WIDTH + self.DAY_HOT_WIDTH
        if idx >= 0:
            self.drawArrowTip(hdc, x - 20, self.rect[3] - 20, 1, 0x0000ff)
        else:
            self.drawArrowTip(hdc, x + 20, self.rect[3] - 20, 0, 0x0000ff)

    def drawHot(self, hdc):
        if not self.hotData or len(self.hotData) == 0:
            return
        x = (self.rect[2] % self.DAY_HOT_WIDTH) // 2
        startX = x
        nd = self.hotData
        days = [d[0]['day'] for d in self.hotData]
        startIdx, endIdx = self.findDrawDaysIndex(days)
        for i, data in enumerate(nd):
            if i < startIdx or i >= endIdx:
                continue
            self.drawOneDayHot(hdc, x, data)
            x += self.DAY_HOT_WIDTH
        if startIdx > 0:
            self.drawArrowTip(hdc, max(startX - 5, 0), self.rect[3] // 2, 0)
        if endIdx < len(self.hotData):
            self.drawArrowTip(hdc, min(x + 5, self.rect[2]), self.rect[3] // 2, 1)

    def drawOneDayLHB(self, hdc, x, data): # data = {'day': '', 'famous': [] }
        if not data:
            return
        pen = win32gui.CreatePen(win32con.PS_DASH, 1, 0xff0000) # day split vertical line
        y = 0
        WIDTH, HEIGHT = self.DAY_HOT_WIDTH, 14
        day = data['day']
        ds = time.strptime(day, '%Y-%m-%d')
        wd = datetime.date(ds[0], ds[1], ds[2]).isoweekday()
        WDS = '一二三四五六日'
        title = day + ' ' + WDS[wd - 1]
        sdc = 0
        if day == self.selectDay:
            sdc = win32gui.SaveDC(hdc)
            win32gui.SetTextColor(hdc, 0xEE00EE)
        win32gui.DrawText(hdc, title, len(title), (x, 0, x + WIDTH, HEIGHT), win32con.DT_CENTER)
        
        y += 10
        flag = True
        for d in data['famous']:
            y += HEIGHT
            if flag and ('+' not in d):
                flag = False
                y += 10
            win32gui.DrawText(hdc, d, len(d), (x + 10, y, x + WIDTH, y + HEIGHT), win32con.DT_LEFT)
            
        win32gui.SelectObject(hdc, pen)
        win32gui.MoveToEx(hdc, x + WIDTH, 0)
        win32gui.LineTo(hdc, x + WIDTH, self.rect[3])
        win32gui.DeleteObject(pen)
        if day == self.selectDay:
            win32gui.RestoreDC(hdc, sdc)

    def drawOneDayHot(self, hdc, x, data): # data = [ {day:'', time:'', hotValue:xx, hotOrder: '' }, ... ]
        if not data or len(data) == 0:
            return
        pen = win32gui.CreatePen(win32con.PS_DASH, 1, 0xff0000) # day split vertical line
        pen2 = win32gui.CreatePen(win32con.PS_DOT, 1, 0x0000ff) # split one day hor-line
        y = 0
        WIDTH, HEIGHT = self.DAY_HOT_WIDTH, 14
        day = data[0]['day']
        ds = time.strptime(day, '%Y-%m-%d')
        wd = datetime.date(ds[0], ds[1], ds[2]).isoweekday()
        WDS = '一二三四五六日'
        title = day + ' ' + WDS[wd - 1]
        sdc = 0
        if day == self.selectDay:
            sdc = win32gui.SaveDC(hdc)
            win32gui.SetTextColor(hdc, 0xEE00EE)
        win32gui.DrawText(hdc, title, len(title), (x, 0, x + WIDTH, HEIGHT), win32con.DT_CENTER)
        
        isDrawSplit = False
        for d in data:
            y += HEIGHT
            row = '%s  %3d万  %3d' % (d['time'], d['hotValue'], d['hotOrder'])
            win32gui.DrawText(hdc, row, len(row), (x, y, x + WIDTH, y + HEIGHT), win32con.DT_CENTER)
            if d['time'] >= '13:00' and (not isDrawSplit):
                isDrawSplit = True
                win32gui.SelectObject(hdc, pen2)
                win32gui.MoveToEx(hdc, x + 5, y - 2)
                win32gui.LineTo(hdc, x + WIDTH - 5, y - 2)
        win32gui.SelectObject(hdc, pen)
        win32gui.MoveToEx(hdc, x + WIDTH, 0)
        win32gui.LineTo(hdc, x + WIDTH, self.rect[3])
        win32gui.DeleteObject(pen)
        win32gui.DeleteObject(pen2)
        if day == self.selectDay:
            win32gui.RestoreDC(hdc, sdc)

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
        tp = ('HOT', 'LHB')
        idx = tp.index(self.dataType)
        idx = (idx + 1) % len(tp)
        self.dataType = tp[idx]
        win32gui.InvalidateRect(self.wnd, None, True)

    def updateCode(self, code):
        self.updateHotData(code)
        self.updateLHBData(code)

    def updateLHBData(self, code):
        ds = orm.TdxLHB.select().where(orm.TdxLHB.code == code)
        data = []
        for d in ds:
            r = {'day': d.day, 'famous': []}
            famous = str(d.famous).split('//')
            if len(famous) == 2:
                for f in famous[0].strip().split(';'):
                    if f: r['famous'].append(' + ' + f.strip())
                for f in famous[1].strip().split(';'):
                    if f: r['famous'].append(' - ' + f.strip())
            else:
                r['famous'].append('   无知名游资')
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
        mywin.sortInfoWindow.show()
        if liangDianWnd:
            win32gui.ShowWindow(liangDianWnd, win32con.SW_SHOW)
    else:
        mywin.sortInfoWindow.hide()
        if liangDianWnd:
            win32gui.ShowWindow(liangDianWnd, win32con.SW_HIDE)
    if move:
        if liangDianWnd:
            win32gui.SetWindowPos(liangDianWnd, None, 560, 800, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOREDRAW | win32con.SWP_NOZORDER)
        win32gui.SetWindowPos(mywin.sortInfoWindow.wnd, None, 1087, 800, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOREDRAW | win32con.SWP_NOZORDER)

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
    curCode = nowCode
    hotWindow.updateCode(nowCode)
    mywin.sortInfoWindow.changeCode(nowCode)

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
        if isInKlineWindow():
            showHotWindow()
            nowCode = findCode()
            if curCode != nowCode:
                work_updateCode(nowCode)
            selDay = getSelectDay()
            if selDay:
                hotWindow.updateSelectDay(selDay)
            if not hotWindow.maxMode:
                showSortAndLiangDianWindow(True, False)
        elif isInFenShiWindow():
            if not hotWindow.maxMode:
                showSortAndLiangDianWindow(True, True)
            pass
        else:
            mywin.sortInfoWindow.hide()
        

def subprocess_run():
    while True:
        if init():
            break
        time.sleep(10)
    hotWindow.createHotWindow()
    #mywin.eyeWindow.createWindow()
    mywin.sortInfoWindow.createWindow(THS_MAIN_HWND)
    threading.Thread(target = work).start()
    win32gui.PumpMessages()
    print('Quit Sub Process')

if __name__ == '__main__':
    while True:
        p = Process(target = subprocess_run, daemon = True)
        p.start()
        print('start a new sub process, pid=', p.pid)
        p.join()