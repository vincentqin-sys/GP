import sys, json
import win32gui, win32con , win32api, win32ui, pyautogui# pip install pywin32
from datafile import *
from orm import *

# 涨停连板复盘
class LBFuPan:
    instance = None

    def __init__(self, fromDay, curCodeIdx = 0):
        LBFuPan.instance = self
        self.curCodeIdx = curCodeIdx - 1
        self.curCodes = []
        self.fromDay = fromDay
        self.days = []
        

    # 最高板到二连板排序
    def calcTopZTList(self, dfs, day):
        rs = []
        for df in dfs:
            dt = df.getItemData(day)
            if dt and getattr(dt, 'lbs', 0) >= config['minLBS']:
                rs.append({'day': day, 'code': df.code, 'lbs': dt.lbs})
        rs = sorted(rs, key=lambda it: it['lbs'], reverse=True)
        return rs

    def initData(self):
        codes = DataFileUtils.listAllCodes()
        self.days = DataFileUtils.calcDays(self.fromDay, True)
        #self.days = self.days[0 : 30]
        dfs = [DataFile(c, DataFile.DT_DAY, True) for c in codes]
        for df in dfs:
            df.calcZDT()
        self.curCodes = []
        for d in self.days:
            rs = self.calcTopZTList(dfs, d)
            self.curCodes.extend(rs)

    def next(self):
        if self.curCodeIdx >= len(self.curCodes):
            print('[ZhangTingFuPan].next Finish')
            return None
        self.curCodeIdx += 1
        dt = self.curCodes[self.curCodeIdx]
        day = dt['day']
        fromIdx, endIdx = self.curCodeIdx, self.curCodeIdx
        while fromIdx > 0 and self.curCodes[fromIdx - 1]['day'] == day:
            fromIdx -= 1
        while endIdx < len(self.curCodes) - 1 and self.curCodes[endIdx + 1]['day'] == day:
            endIdx += 1
        num = endIdx - fromIdx + 1
        idx = self.curCodeIdx - fromIdx + 1
        dt['pos'] = idx
        dt['num'] = num
        dt['idx'] = self.curCodeIdx
        return dt
    
    def prev(self):
        if self.curCodeIdx <= 0:
            print('[ZhangTingFuPan].prev Finish')
            return None
        self.curCodeIdx -= 1
        return self.curCodes[self.curCodeIdx]

class ThsWindow:
    SIZE = (150, 80)
    instance = None

    def __init__(self):
        ThsWindow.instance = self
        self.hwnd = None
        self.hwndText = '[None]'
        self.THS_MAIN_HWND = self.THS_TOP_HWND = None
        def callback(hwnd, lparam):
            title = win32gui.GetWindowText(hwnd)
            if '同花顺(v' in title:
                self.THS_TOP_HWND = hwnd
            return True
        win32gui.EnumWindows(callback, None)
        if self.THS_TOP_HWND:
            self.THS_MAIN_HWND =  win32gui.FindWindowEx(self.THS_TOP_HWND, None, 'AfxFrameOrView140s', None)
        print(f'[ThsWindow.init] Find HTS_TOP_WINDOW = {self.THS_TOP_HWND:X}', )
        if not self.THS_TOP_HWND:
            raise Exception('Not find THS_TOP_WINDOW')

    def buildViews(self):
        if not self.THS_TOP_HWND:
            return
        style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_BORDER | win32con.SS_CENTER
        rect = win32gui.GetWindowRect(self.THS_TOP_HWND)
        if rect[2] - rect[0] > 1500:
            xy = (1350, 250)
        else:
            xy = (800, 250)
        self.hwnd = win32gui.CreateWindow('STATIC', 'ZTInfo-Window', style, *xy, *self.SIZE, self.THS_TOP_HWND, None, None, None)
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_WNDPROC, ThsWindow.winProc)
        win32gui.PostMessage(self.hwnd, win32con.WM_PAINT)

    def draw(self, hwnd):
        hdc, ps = win32gui.BeginPaint(hwnd)
        bk = win32gui.CreateSolidBrush(0xffffff)
        win32gui.FillRect(hdc, win32gui.GetClientRect(hwnd), bk)
        win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
        win32gui.SetTextColor(hdc, 0x0)
        a = win32gui.LOGFONT()
        a.lfHeight = 16
        a.lfFaceName = '新宋体'
        font = win32gui.CreateFontIndirect(a)
        win32gui.SelectObject(hdc, font)
        win32gui.DrawText(hdc, self.hwndText, len(self.hwndText), (10, 10, *self.SIZE), win32con.DT_CENTER)
        win32gui.EndPaint(hwnd, ps)
        win32gui.DeleteObject(font)
        win32gui.DeleteObject(bk)

    @staticmethod
    def winProc(hwnd, msg, wparam, lparam):
        if msg == win32con.WM_RBUTTONUP:
            # next
            info = LBFuPan.instance.next()
            print('[Next]', info)
            day = str(info['day'])
            day = day[0 : 4] + '-' + day[4: 6] + '-' + day[6 :]
            txt = f"{day} \n\n{info['code']} \n {info['lbs']}连板 [{info['pos']}/{info['num']}]"
            ThsWindow.instance.hwndText = txt
            if info:
                pyautogui.typewrite(info['code'], 0.1)
                pyautogui.press('enter')
                win32gui.InvalidateRect(hwnd, None, True)
                config['idx'] = info['idx']
                saveFuPanConfig()
            return 0
        elif msg == win32con.WM_LBUTTONUP:
            # pre
            info = LBFuPan.instance.prev()
            print('[Prev]', info)
            day = str(info['day'])
            day = day[0 : 4] + '-' + day[4: 6] + '-' + day[6 :]
            txt = f"{day} \n\n{info['code']} \n {info['lbs']}连板 [{info['pos']}/{info['num']}]"
            ThsWindow.instance.hwndText = txt
            if info:
                pyautogui.typewrite(info['code'], 0.1)
                pyautogui.press('enter')
                win32gui.InvalidateRect(hwnd, None, True)
                config['idx'] = info['idx']
                saveFuPanConfig()
            return 0
        if msg == win32con.WM_PAINT:
            ThsWindow.instance.draw(hwnd)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

def loadFuPanConfig():
    config = {'day': 20230201, 'idx': 0}
    path = 'fupan.config'
    if not os.path.exists(path):
        return config
    f = open(path, 'r')
    js = json.load(f)
    f.close()
    return js

def saveFuPanConfig():
    path = 'fupan.config'
    txt = json.dumps(config)
    f = open(path, 'w')
    f.write(txt)
    f.close()

config = loadFuPanConfig()

if __name__ == '__main__':
    thsWin = ThsWindow()
    thsWin.buildViews()
    fupan = LBFuPan(config['day'], config['idx'])
    fupan.initData()
    thsWin.hwndText = 'Init End'
    win32gui.InvalidateRect(thsWin.hwnd, None, True)
    print('-----------init end-------')
    win32gui.PumpMessages()
