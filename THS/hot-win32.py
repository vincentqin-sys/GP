import win32gui as win, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime
from PIL import Image
import orm, number_ocr

# pip installl opencv-python

THS_TOP_HWND = None
THS_MAIN_HWND = None
THS_LEVEL2_CODE_HWND = None
THS_SELECT_DAY_HWND = None

ocr = number_ocr.NumberOCR()

def findLevel2CodeWnd(hwnd):
    global THS_LEVEL2_CODE_HWND
    child = win.GetWindow(hwnd, win32con.GW_CHILD)
    while child:
        title = win.GetWindowText(child)
        if win.IsWindowVisible(child) and title and ('逐笔成交--' in title):
            THS_LEVEL2_CODE_HWND = child
            break
        findLevel2CodeWnd(child)
        if THS_LEVEL2_CODE_HWND:
            break
        child = win.GetWindow(child, win32con.GW_HWNDNEXT)

def findSelectDayWnd():
    global THS_MAIN_HWND
    child = win.GetWindow(THS_MAIN_HWND, win32con.GW_CHILD)
    while child:
        if win.GetClassName(child) == '#32770':
            left, top, right, bottom = win.GetClientRect(child)
            w, h = right - left, bottom - top
            if h / 3 > w:
                return child
        child = win.GetWindow(child, win32con.GW_HWNDNEXT)
    return None

# 当前显示的窗口是否是K线图
def isInKlineWindow():
    if '技术分析' not in win.GetWindowText(THS_TOP_HWND):
        return False
    return win.IsWindowVisible(THS_TOP_HWND)

# 查找股票代码
def findCode():
    global THS_MAIN_HWND, THS_TOP_HWND, THS_LEVEL2_CODE_HWND
    if not isInKlineWindow():
        #print('Not in KLine Window')
        return None
    # 逐笔成交明细 Level-2
    if not win.IsWindowVisible(THS_LEVEL2_CODE_HWND):
        THS_LEVEL2_CODE_HWND = None
        findLevel2CodeWnd(THS_MAIN_HWND)
        #print('THS_LEVEL2_CODE_HWND = %#X' % THS_LEVEL2_CODE_HWND)
    title = win.GetWindowText(THS_LEVEL2_CODE_HWND) or ''
    code = ''
    if '逐笔成交--' in title:
        code = title[6 : 12]
    return code

def getSelectDay():
    global THS_SELECT_DAY_HWND, ocr
    if not win.IsWindowVisible(THS_SELECT_DAY_HWND):
        return None
    dc = win.GetWindowDC(THS_SELECT_DAY_HWND)
    #mdc = win.CreateCompatibleDC(dc)
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
    win.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win.ReleaseDC(THS_SELECT_DAY_HWND, dc)

    sd = selYear + '-' + selDay[0 : 2] + '-' + selDay[2 : 4]
    #print(sd)
    return sd


def init():
    def callback(hwnd, lparam):
        title = win.GetWindowText(hwnd)
        if '同花顺(v' in title:
            global THS_TOP_HWND
            THS_TOP_HWND = hwnd
        return True
    
    global THS_MAIN_HWND, THS_TOP_HWND, THS_SELECT_DAY_HWND
    win.EnumWindows(callback, None)
    # THS_MAIN_HWND = getChildWindow(THS_TOP_HWND, 0xE900)
    THS_MAIN_HWND =  win.FindWindowEx(THS_TOP_HWND, None, 'AfxFrameOrView100s', None)
    THS_SELECT_DAY_HWND = findSelectDayWnd()
    print('THS_TOP_HWND = %#X' % THS_TOP_HWND)
    print('THS_MAIN_HWND = %#X' % THS_MAIN_HWND)
    print('THS_SELECT_DAY_HWND = %#X' % THS_SELECT_DAY_HWND)


#-------------------hot  window ------------
class HotWindow:
    DAY_HOT_WIDTH = 120

    def __init__(self):
        self.oldProc = None
        self.wnd = None
        self.rect = None  # 窗口大小 (x, y, w, h)
        self.maxMode = True #  是否是最大化的窗口
        self.data = None
        self.selectDay = ''

    def createHotWindow(self):
        global THS_TOP_HWND, THS_MAIN_HWND
        # WS_CLIPCHILDREN:0x02000000L
        # 0x40000000 child-win ;  0x80000000 popup-win
        rr = win.GetClientRect(THS_TOP_HWND)
        print('THS top window: ', rr)
        style = 0x00800000 | 0x10000000 | win32con.WS_CHILD
        HEIGHT = 285
        x = 0
        y = rr[3] - rr[1] - HEIGHT
        w = rr[2] - rr[0]
        self.rect = (x, y, w, HEIGHT)
        self.wnd = win.CreateWindow('STATIC', 'HOT-Window', style, x, y, w, HEIGHT, THS_TOP_HWND, None, None, None)
        win.SetWindowPos(self.wnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        self.oldProc = win.GetWindowLong(self.wnd, -4) # GWL_WNDPROC
        win.SetWindowLong(self.wnd, -4, hotWinProc)
        print('hotWnd = %#X' % self.wnd, x, y, w, HEIGHT)
        win.SendMessage(self.wnd, win32con.WM_PAINT)

    def destroy(self):
        win.DestroyWindow(self.wnd)
    
    def drawHotWin(self, hwnd):
        hdc, ps = win.BeginPaint(hwnd)
        bk = win.CreateSolidBrush(0xffffff)
        win.FillRect(hdc, win.GetClientRect(hwnd), bk)
        win.SetBkMode(hdc, win32con.TRANSPARENT)
        win.SetTextColor(hdc, 0x0)

        a = win.LOGFONT()
        a.lfHeight = 12
        a.lfFaceName = '新宋体'
        font = win.CreateFontIndirect(a)
        win.SelectObject(hdc, font)
        
        if self.maxMode:
            self.drawMaxMode(hdc)
        else:
            self.drawMinMode(hdc)

        win.EndPaint(hwnd, ps)
        win.DeleteObject(font)
        win.DeleteObject(bk)
        # print('WM_PAINT')

    # return [startIdx, endIdx)
    def findDrawDaysIndex(self):
        if not self.data:
            return (0, 0)
        width = self.rect[2]
        num = width // self.DAY_HOT_WIDTH
        if num == 0:
            return (0, 0)
        if len(self.data) <= num:
            return (0, len(self.data))
        if not self.selectDay:
            return (len(self.data) - num, len(self.data))
        days = [d[0]['day'] for d in self.data]
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

    def drawMoreTip(self, hdc, x, y, op):
        sdc = win.SaveDC(hdc)
        br = win.CreateSolidBrush(0xff0000)
        win.SelectObject(hdc, br)
        pts = None
        CW ,CH = 5, 6
        if op == 0: # left more arrow
            pts = [(x, y), (x + CW, y - CH), (x + CW, y + CH)]
        else: # right more arrow
            pts = [(x, y), (x - CW, y - CH), (x - CW, y + CH)]
        win.Polygon(hdc, pts)
        win.RestoreDC(hdc, sdc)

    def drawMaxMode(self, hdc):
        if not self.data or len(self.data) == 0:
            return
        x = (self.rect[2] % self.DAY_HOT_WIDTH) // 2
        startX = x
        nd = self.data
        startIdx, endIdx = self.findDrawDaysIndex()
        for i, data in enumerate(nd):
            if i < startIdx or i >= endIdx:
                continue
            self.drawOneDayHot(hdc, x, data)
            x += self.DAY_HOT_WIDTH
        if startIdx > 0:
            self.drawMoreTip(hdc, max(startX - 5, 0), self.rect[3] // 2, 0)
        if endIdx < len(self.data):
            self.drawMoreTip(hdc, min(x + 5, self.rect[2]), self.rect[3] // 2, 1)

    def drawOneDayHot(self, hdc, x, data): # data = [ {day:'', time:'', hotValue:xx, hotOrder: '' }, ... ]
        if not data or len(data) == 0:
            return
        pen = win.CreatePen(win32con.PS_DASH, 1, 0xff0000) # day split vertical line
        pen2 = win.CreatePen(win32con.PS_DOT, 1, 0x0000ff) # split one day hor-line
        y = 0
        WIDTH, HEIGHT = self.DAY_HOT_WIDTH, 15
        day = data[0]['day']
        ds = time.strptime(day, '%Y-%m-%d')
        wd = datetime.date(ds[0], ds[1], ds[2]).isoweekday()
        WDS = '一二三四五六日'
        title = day + ' ' + WDS[wd - 1]
        sdc = 0
        if day == self.selectDay:
            sdc = win.SaveDC(hdc)
            win.SetTextColor(hdc, 0xEE00EE)
        win.DrawText(hdc, title, len(title), (x, 0, x + WIDTH, HEIGHT), win32con.DT_CENTER)
        
        isDrawSplit = False
        for d in data:
            y += HEIGHT
            row = '%s  %3d万  %3d' % (d['time'], d['hotValue'], d['hotOrder'])
            win.DrawText(hdc, row, len(row), (x, y, x + WIDTH, y + HEIGHT), win32con.DT_CENTER)
            if d['time'] >= '13:00' and (not isDrawSplit):
                isDrawSplit = True
                win.SelectObject(hdc, pen2)
                win.MoveToEx(hdc, x + 5, y - 2)
                win.LineTo(hdc, x + WIDTH - 5, y - 2)
        win.SelectObject(hdc, pen)
        win.MoveToEx(hdc, x + WIDTH, 0)
        win.LineTo(hdc, x + WIDTH, self.rect[3])
        win.DeleteObject(pen)
        win.DeleteObject(pen2)
        if day == self.selectDay:
            win.RestoreDC(hdc, sdc)

    def drawMinMode(self, hdc):
        title = '【我的热点】\n\n双击最大化'
        rr = win.GetClientRect(self.wnd)
        win.FillRect(hdc, win.GetClientRect(self.wnd), win32con.COLOR_WINDOWFRAME)  # background black
        win.SetTextColor(hdc, 0x0000ff)
        win.DrawText(hdc, title, len(title), rr, win32con.DT_CENTER | win32con.DT_VCENTER)

    def changeMode(self):
        if self.maxMode:
            WIDTH, HEIGHT = 150, 50
            y = self.rect[1] + self.rect[3] - HEIGHT
            win.SetWindowPos(self.wnd, 0, 0, y, WIDTH, HEIGHT, 0)
        else:
            win.SetWindowPos(self.wnd, 0, self.rect[0], self.rect[1], self.rect[2], self.rect[3], 0)
        self.maxMode = not self.maxMode
        win.InvalidateRect(self.wnd, None, True)

    def updateData(self, data):
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
        self.data = rs
        win.InvalidateRect(self.wnd, None, True)

    def updateSelectDay(self, newDay):
        if not newDay or self.selectDay == newDay:
            return
        self.selectDay = newDay
        win.InvalidateRect(self.wnd, None, True)

def hotWinProc(hwnd, msg, wparam, lparam):
    global hotWindow
    if msg == win32con.WM_PAINT:
        hotWindow.drawHotWin(hwnd)
        return 0
    elif msg == win32con.WM_DESTROY:
        win.PostQuitMessage(0)
        return 0
    elif msg == win32con.WM_LBUTTONDBLCLK:
        hotWindow.changeMode()
        return 0
    else:
        return win.DefWindowProc(hwnd, msg, wparam, lparam)
        # win.CallWindowProc(hotWindow.oldProc, hwnd, msg, wparam, lparam)

#----------------------------------------
hotWindow = HotWindow()
curCode = None

def work_updateCode(nowCode):
    global curCode
    ds = orm.THS_Hot.select().where(orm.THS_Hot.code == nowCode)
    hts = [d.__data__ for d in ds]
    if len(hts) > 0:
        print('Load ', nowCode, hts[0]['name'], ' Count:', len(hts))
    elif nowCode:
        print('Load ', nowCode , ' not find in DB')
    curCode = nowCode
    hotWindow.updateData(hts)

def work():
    global curCode
    while True:
        time.sleep(0.5)
        nowCode = findCode()
        if curCode != nowCode:
            work_updateCode(nowCode)
        selDay = getSelectDay()
        if selDay:
            hotWindow.updateSelectDay(selDay)

if __name__ == '__main__':
    init()
    hotWindow.createHotWindow()
    threading.Thread(target = work).start()
    win.PumpMessages()
