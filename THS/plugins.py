import win32gui, win32con , win32api, win32ui, winerror, pyautogui  # pip install pywin32
import threading, time, datetime, sys, os
from PIL import Image  # pip install pillow
import base_win, number_ocr

class SelDayWindow(base_win.BaseWindow):
    MSG_START = 0xDAEA

    def __init__(self) -> None:
        super().__init__()
        self.thsTopHwnd = None
        self.thsMainHwnd = None
        self.editHwnd = None
        self.ocr = number_ocr.NumberOCR()
        self.needFindSelDay = False
        self.tasks = []

    def _findThsTopWin(self):
        def callback(hwnd, lparam):
            title = win32gui.GetWindowText(hwnd)
            if '同花顺(v' in title:
                self.thsTopHwnd = hwnd
            return True
        win32gui.EnumWindows(callback, None)
    
    def install(self):
        self._findThsTopWin()
        #print(f'thsTopHwnd=0x{self.thsTopHwnd :X}')
        if not self.thsTopHwnd:
            print('[install] Not find thsTopWin')
            return
        self.thsMainHwnd =  win32gui.FindWindowEx(self.thsTopHwnd, None, 'AfxFrameOrView140s', None)
        self.selectDayHwnd = self.findSelectDayHwnd()

        rc = (600, 0, 100, 20)
        style = win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW
        self.createWindow(None, rc, style) # self.thsTopHwnd
        style2 = win32con.WS_VISIBLE | win32con.WS_CHILD
        rc2 = (0, 0, 100, 20)
        self.editHwnd = win32gui.CreateWindow('EDIT', '2023-12-01', style2, *rc2, self.hwnd, 0xEDED, None, None)
        self.editOldProc = win32gui.SetWindowLong(self.editHwnd, win32con.GWL_WNDPROC, self.editWinProc)
        SelDayWindow.bindHwnds[self.editHwnd] = self

    def findSelectDayHwnd(self):
        child = win32gui.GetWindow(self.thsMainHwnd, win32con.GW_CHILD)
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
        if '技术分析' not in win32gui.GetWindowText(self.thsTopHwnd):
            return False
        return win32gui.IsWindowVisible(self.thsTopHwnd)

    # 找到日期对应的K线，并将鼠标放在上面
    def start(self):
        day = win32gui.GetDlgItemText(self.hwnd, 0xEDED)
        if not day or len(day.strip()) != 10:
            return
        day = day.replace('-', '').strip()
        if len(day) != 8:
            return
        for d in day:
            if d < '0' or d > '9':
                return
        print('find day=', day)
        pyautogui.click(300, 250)
        time.sleep(0.5)
        bt = time.time()
        while True:
            et = time.time()
            if et - bt > 6:
                print('time out x')
                return
            beginDay = self.getDayRange()
            print('beginDay=', beginDay)
            if day >= beginDay:
                break # find the day
            pyautogui.moveTo(300, 250)
            pyautogui.press('down')
            pyautogui.press('down')
            time.sleep(0.5)
        self.findTheDay(day)

    def findTheDay(self, day):
        print('begin find day pos')
        step = 5
        bt = time.time()
        diffTag = None
        while True:
            et = time.time()
            if et - bt > 5:
                print('time out')
                break
            selDay = self.getSelectDay()
            if not selDay:
                pyautogui.press('left')
                time.sleep(0.1)
                continue
            sd = datetime.datetime.strptime(selDay, '%Y%m%d')
            dd = datetime.datetime.strptime(day, '%Y%m%d')
            diff = sd - dd
            if diff.days == 0:
                break
            nowDiffTag = diff.days > 0
            if diffTag == None:
                diffTag = nowDiffTag
            if abs(diff.days) <= 3 or nowDiffTag != diffTag:
                pyautogui.press('left' if diff.days > 0 else 'right')
                print('press key left or right')
                time.sleep(0.1)
            else:
                x = - diff.days // 2 * step
                print('move x =', x)
                pyautogui.move(x - 5, 0)
                pyautogui.move(5, 0, 0.2)
    
    # dirs = LEFT, RIGHT, LEFT+RIGHT
    def getDayRange(self):
        pyautogui.click(300, 250)
        time.sleep(0.5)
        pyautogui.moveTo(0, 250, 0.5)
        time.sleep(0.3)
        beginDay = self.getSelectDay()
        return beginDay
    
    def getSelectDay(self):
        if not win32gui.IsWindowVisible(self.selectDayHwnd):
            return None
        dc = win32gui.GetWindowDC(self.selectDayHwnd)
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
        win32gui.ReleaseDC(self.selectDayHwnd, dc)

        sd = selYear + selDay
        #check is a day
        if len(sd) != 8:
            return '' # invalid day
        for s in sd:
            if s < '0' or s > '9':
                return '' # invalid day
        return sd

    def winProc(self, hwnd, msg, wParam, lParam):
        return False
    
    @staticmethod
    def editWinProc(hwnd, msg, wParam, lParam):
        self = SelDayWindow.bindHwnds[hwnd]
        if msg == win32con.WM_CHAR:
            if wParam == 13: # 回车事件
                self.start()
                return 0
        return win32gui.CallWindowProc(self.editOldProc, hwnd, msg, wParam, lParam)

if __name__ == '__main__':
    selWin = SelDayWindow()
    selWin.install()
    win32gui.PumpMessages()

