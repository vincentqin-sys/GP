import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os
from multiprocessing import Process
from multiprocessing import shared_memory # python 3.8+
from PIL import Image # pip install pillow

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from THS import number_ocr
from Common import base_win 

class ThsWindow(base_win.BaseWindow):

    def __init__(self) -> None:
        super().__init__()
        self.topHwnd = None
        self.mainHwnd = None
        self.level2CodeHwnd = None
        self.selDayHwnd = None
        self.ocr = number_ocr.NumberOCR()

    def findLevel2CodeWnd(self, hwnd):
        child = win32gui.GetWindow(hwnd, win32con.GW_CHILD)
        while child:
            title = win32gui.GetWindowText(child)
            if win32gui.IsWindowVisible(child) and title and ('逐笔成交--' in title):
                self.level2CodeHwnd = child
                break
            self.findLevel2CodeWnd(child)
            if self.level2CodeHwnd:
                break
            child = win32gui.GetWindow(child, win32con.GW_HWNDNEXT)

    def findSelectDayWnd(self):
        if not self.mainHwnd:
            return None
        child = win32gui.GetWindow(self.mainHwnd, win32con.GW_CHILD)
        while child:
            if win32gui.GetClassName(child) == '#32770':
                left, top, right, bottom = win32gui.GetClientRect(child)
                w, h = right - left, bottom - top
                if h / 3 > w:
                    return child
            child = win32gui.GetWindow(child, win32con.GW_HWNDNEXT)
        return None    

    # 当前显示的窗口是否是K线图
    def isInKlineWindow(self):
        if '技术分析' not in win32gui.GetWindowText(self.topHwnd):
            return False
        return win32gui.IsWindowVisible(self.topHwnd)

    # 当前显示的窗口是否是分时图
    def isInFenShiWindow(self):
        if '分时走势' not in win32gui.GetWindowText(self.topHwnd):
            return False
        return win32gui.IsWindowVisible(self.topHwnd)

    # 当前显示的窗口是否是“我的首页”
    def isInMyHomeWindow(self):
        if '我的首页' not in win32gui.GetWindowText(self.topHwnd):
            return False
        return win32gui.IsWindowVisible(self.topHwnd)

    # 查找股票代码
    def findCode(self):
        #if (not self.isInKlineWindow()) and (not self.isInMyHomeWindow()):
            #print('Not in KLine Window')
        #    return None
        # 逐笔成交明细 Level-2
        if not win32gui.IsWindowVisible(self.level2CodeHwnd):
            self.level2CodeHwnd = None
            self.findLevel2CodeWnd(self.mainHwnd)
        title = win32gui.GetWindowText(self.level2CodeHwnd) or ''
        code = ''
        if '逐笔成交--' in title:
            code = title[6 : 12]
        return code

    def getSelectDay(self):
        if not win32gui.IsWindowVisible(self.selDayHwnd):
            return None
        dc = win32gui.GetWindowDC(self.selDayHwnd)
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

        selYear = self.ocr.match(im_PIL)
        # print('selYear=', selYear)
        
        # copy day bmp
        srcPos = (14, 38)
        saveDC.BitBlt((0, 0), srcSize, mfcDC, srcPos, win32con.SRCCOPY)
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        im_PIL = Image.frombuffer('RGB',(bmpinfo['bmWidth'], 17), bmpstr, 'raw', 'BGRX', 0, 1) 
        selDay = self.ocr.match(im_PIL)
        # print('selDay=', selDay)
        # im_PIL.show()

        # destory
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(self.selDayHwnd, dc)

        sd = selYear + '-' + selDay[0 : 2] + '-' + selDay[2 : 4]
        #check is a day
        sd2 = sd.replace('-', '')
        if len(sd2) != 8:
            return '' # invalid day
        for s in sd2:
            if s < '0' or s > '9':
                return '' # invalid day
        #print(sd)
        return sd

    def init(self):
        def callback(hwnd, lparam):
            title = win32gui.GetWindowText(hwnd)
            if ('同花顺(v' in title) and ('副屏1' not in title):
                self.topHwnd = hwnd
            return True
        win32gui.EnumWindows(callback, None)
        self.mainHwnd =  win32gui.FindWindowEx(self.topHwnd, None, 'AfxFrameOrView140s', None)
        self.selDayHwnd = self.findSelectDayWnd()

        if (not self.mainHwnd) or (not self.topHwnd) or (not self.selDayHwnd):
            return False
        print('ThsWindow.topHwnd = %#X' % self.topHwnd)
        print('ThsWindow.mainHwnd = %#X' % self.mainHwnd)
        print('ThsWindow.selDayHwnd = %#X' % self.selDayHwnd)
        return True

class ThsFuPingWindow(ThsWindow):
    def __init__(self) -> None:
        super().__init__()

    def init(self):
        def callback(hwnd, lparam):
            title = win32gui.GetWindowText(hwnd)
            if ('同花顺(v' in title) and ('副屏1' in title):
                self.topHwnd = hwnd
            return True
        win32gui.EnumWindows(callback, None)
        self.mainHwnd =  win32gui.FindWindowEx(self.topHwnd, None, 'AfxFrameOrView140s', None)
        self.selDayHwnd = self.findSelectDayWnd()

        if (not self.mainHwnd) or (not self.topHwnd) or (not self.selDayHwnd):
            return False
        print('ThsFuPingWindow.topHwnd = %#X' % self.topHwnd)
        print('ThsFuPingWindow.mainHwnd = %#X' % self.mainHwnd)
        print('ThsFuPingWindow.selDayHwnd = %#X' % self.selDayHwnd)
        return True  

class ThsShareMemory:
    POS_CODE = 0
    POS_SEL_DAY = 1
    _thread = None

    def __init__(self, create : bool = False) -> None:
        self.create = create
        self.listeners = []
        self.shm = None

    # func = function(code, day)
    def addListener(self, name, func):
        for ls in self.listeners:
            if ls[0] == name:
                return
        if func:
            self.listeners.append((name, func))

    def notifyListener(self, curCode, curDay):
        for ls in self.listeners:
            func = ls[1]
            func(curCode, curDay)

    def onListenThread(self):
        curDay, curCode = 0, 0
        while True:
            time.sleep(0.5)
            day = self.readSelDay()
            code = self.readCode()
            if day == 0 or code == 0:
                continue
            if day != curDay or code != curCode:
                curDay = day
                curCode = code
                self.notifyListener(curCode, curDay)

    def open(self):
        if self.shm:
            return
        try:
            if self.create:
                self.shm = shared_memory.SharedMemory('Ths-Share-window-Memory', True, size = 512)
                buf = self.shm.buf.cast('i')
                buf[self.POS_CODE] = 0
                buf[self.POS_SEL_DAY] = 0
            else:
                self.shm = shared_memory.SharedMemory('Ths-Share-window-Memory', False)
            if not ThsShareMemory._thread:
                ThsShareMemory._thread = threading.Thread(target = self.onListenThread, daemon = True)
                ThsShareMemory._thread.start()
        except Exception as e:
            print('ths_win.ThsShareMemory.open exception: ', e)

    def writeCode(self, code):
        if not self.shm:
            return
        try:
            code = int(code)
        except:
            return
        buf = self.shm.buf.cast('i')
        buf[self.POS_CODE] = code

    # return int
    def readCode(self):
        if not self.shm:
            return
        buf = self.shm.buf.cast('i')
        code = buf[0]
        return code
    
    def writeSelDay(self, day):
        if not day or not self.shm:
            return
        if type(day) == str:
            day = day.replace('-', '')
            day = int(day)
        buf = self.shm.buf.cast('i')
        buf[self.POS_SEL_DAY] = day

    # return int
    def readSelDay(self):
        if not self.shm:
            return
        buf = self.shm.buf.cast('i')
        day = buf[self.POS_SEL_DAY]
        return day

    def close(self):
        if not self.shm:
            return
        self.shm.close()

    def unlink(self):
        if not self.shm:
            return
        self.shm.unlink()