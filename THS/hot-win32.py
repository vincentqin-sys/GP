import win32gui as win, win32con , win32api # pip install pywin32
import threading, time
import orm

THS_TOP_HWND = None
THS_MAIN_HWND = None
THS_LEVEL2_CODE_HWND = None

def enumLevel2_Window(hwnd):
    pass

def findLevel2CodeWnd(hwnd):
    global THS_LEVEL2_CODE_HWND
    child = win.GetWindow(hwnd, win32con.GW_CHILD)
    while child:
        title = win.GetWindowText(child)
        if win.IsWindowVisible(child) and title and ('逐笔成交--' in title):
            THS_LEVEL2_CODE_HWND = child
            break
        enumMainWindow(child)
        if THS_LEVEL2_CODE_HWND:
            break
        child = win.GetWindow(child, win32con.GW_HWNDNEXT)

# 当前显示的窗口是否是K线图
def isInKlineWindow():
    if '技术分析' not in win.GetWindowText(THS_TOP_HWND):
        return False
    return win.IsWindowVisible(THS_TOP_HWND)

# 查找股票代码
def findCode():
    global THS_MAIN_HWND, THS_TOP_HWND, THS_LEVEL2_CODE_HWND
    if not isInKlineWindow():
        print('Not in KLine Window')
        return None
    # 逐笔成交明细 Level-2
    if not win.IsWindowVisible(THS_LEVEL2_CODE_HWND):
        findLevel2CodeWnd(THS_MAIN_HWND)
    title = win.GetWindowText(THS_LEVEL2_CODE_HWND) or ''
    code = ''
    if '逐笔成交--' in title:
        code = title[6 : 12]
    return code


def init():
    def callback(hwnd, lparam):
        title = win.GetWindowText(hwnd)
        if '同花顺(v' in title:
            global THS_TOP_HWND
            THS_TOP_HWND = hwnd
        return True
    
    global THS_MAIN_HWND, THS_TOP_HWND
    win.EnumWindows(callback, None)
    # THS_MAIN_HWND = getChildWindow(THS_TOP_HWND, 0xE900)
    THS_MAIN_HWND =  win.FindWindowEx(THS_TOP_HWND, None, 'AfxFrameOrView100s', None)
    print('THS_TOP_HWND = %#X' % THS_TOP_HWND)
    print('THS_MAIN_HWND = %#X' % THS_MAIN_HWND)

#-------------------hot  window ------------
class HotWindow:
    DAY_HOT_WIDTH = 120

    def __init__(self):
        self.oldProc = None
        self.wnd = None
        self.rect = None  # 窗口大小 (x, y, w, h)
        self.maxMode = True #  是否是最大化的窗口
        self.data = None

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
        win.FillRect(hdc, win.GetClientRect(hwnd), 9)  # background black
        win.SetBkMode(hdc, win32con.TRANSPARENT)
        win.SetTextColor(hdc, 0xc0c0c0)

        a = win.LOGFONT()
        a.lfHeight = 12
        a.lfFaceName = '新宋体'
        font = win.CreateFontIndirect(a)
        win.SelectObject(hdc, font)

        pen = win.CreatePen(1, 1, 0xff0000)
        win.SelectObject(hdc, pen)
        # win.Rectangle(hdc, 20, 50, 500, 100)
        
        if self.maxMode:
            self.drawMaxMode(hdc)
        else:
            self.drawMinMode(hdc)

        win.EndPaint(hwnd, ps)
        win.DeleteObject(font)
        print('WM_PAINT')

    def drawMaxMode(self, hdc):
        if not self.data or len(self.data) == 0:
            return
        x = 0
        nd = self.data
        for data in nd:
            self.drawOneDayHot(hdc, x, data)
            x += self.DAY_HOT_WIDTH

    def drawOneDayHot(self, hdc, x, data): # data = [ {day:'', time:'', hotValue:xx, hotOrder: '' }, ... ]
        if not data or len(data) == 0:
            return
        y = 0
        WIDTH, HEIGHT = self.DAY_HOT_WIDTH, 15
        title = data[0]['day']
        win.DrawText(hdc, title, len(title), (x, 0, x + WIDTH, HEIGHT), win32con.DT_CENTER)
        for d in data:
            y += HEIGHT
            row = '%s  %3d万  %3d' % (d['time'], d['hotValue'], d['hotOrder'])
            win.DrawText(hdc, row, len(row), (x, y, x + WIDTH, y + HEIGHT), win32con.DT_CENTER)
        win.MoveToEx(hdc, x + WIDTH, 0)
        win.LineTo(hdc, x + WIDTH, self.rect[3])

    def drawMinMode(self, hdc):
        title = '【我的热点】 双击最大化'
        rr = win.GetClientRect(self.wnd)
        print(rr)
        win.DrawText(hdc, title, len(title), rr, win32con.DT_CENTER | win32con.DT_VCENTER)

    def changeMode(self):
        if self.maxMode:
            WIDTH, HEIGHT = 150, 30
            y = self.rect[1] + self.rect[3] - HEIGHT
            win.SetWindowPos(self.wnd, 0, 0, y, WIDTH, HEIGHT, 0)
        else:
            win.SetWindowPos(self.wnd, 0, self.rect[0], self.rect[1], self.rect[2], self.rect[3], 0)
        self.maxMode = not self.maxMode
        win.InvalidateRect(self.wnd, None, True)

    def updateData(self, data):
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

def work():
    global curCode
    while True:
        time.sleep(0.5)
        nowCode = findCode()
        if curCode == nowCode:
            continue
        ds = orm.THS_Hot.select().where(orm.THS_Hot.code == nowCode)
        hts = [d.__data__ for d in ds]
        if len(hts) > 0:
            print('Load ', hts[0]['name'], ' Number:', len(hts))
        else:
            print('Load ', nowCode , ' not find in DB')
        curCode = nowCode
        hotWindow.updateData(hts)

if __name__ == '__main__':
    init()

    findCode()
    input()

    hotWindow.createHotWindow()
    threading.Thread(target = work).start()
    win.PumpMessages()
