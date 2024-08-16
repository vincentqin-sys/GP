import win32gui, win32ui, win32con, re
from PIL import Image
import easyocr, ths_win

ocr = easyocr.Reader(['ch_sim'], download_enabled = True )

class ThsOcrUtils:
    def __init__(self) -> None:
        self.titleHwnds = set()
        
    # wb = 委比 28.45
    # diff = 委差
    # price = 当前成交价
    def calcBS(self, wb, diff, price):
        if wb == 0:
            return None
        wb /= 100
        sumv = diff / wb
        b = int((sumv + diff) / 2)
        s = int(b - diff)
        
        buy = abs(int(b * 100 * price / 10000))
        sell = abs(int(s * 100 * price / 10000))
        #print('sell > ', sell, '万元')
        #print('buy < ', buy, '万元')
        return buy, sell

    def dump(self, hwnd):
        if (not win32gui.IsWindow(hwnd)) or (not win32gui.IsWindowVisible(hwnd)):
            return None
        dc = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(dc)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        W, H = 600, 300
        rc = win32gui.GetWindowRect(hwnd)
        w, h = rc[2] - rc[0], rc[3] - rc[1]
        srcSize = min(W, w), min(H, h + 30)

        saveBitMap.CreateCompatibleBitmap(mfcDC, *srcSize) # image size W x H
        saveDC.SelectObject(saveBitMap)
        hbr = win32ui.CreateBrush()
        #hbr.CreateSolidBrush(0x000000)
        #saveDC.FillRect((0, 0, W, H), hbr)
        
        srcPos = 0, 0
        saveDC.BitBlt((0, 0), srcSize, mfcDC, srcPos, win32con.SRCCOPY)
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        img_PIL = Image.frombuffer('RGB',(bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)
        img_PIL.save('D:/a.bmp')
        #img_PIL.show()
        #print(img_PIL.getcolors(), img_PIL.mode)
        result = ocr.readtext('D:/a.bmp')
        print(result)
        # destory
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, dc)
        return result

    def parse(self, result):
        if not result:
            return None
        rs = {}
        cn = result[0][1]
        rs['name'] = cn[0 : len(cn) - 6]
        rs['code'] = cn[-6 : ]

        rs['price'] = float(result[1][1])
        #rs['zdPrice'] = float(result[2][1])
        # find 委比
        wsstrs = ''
        idx = -1
        for i, it in enumerate(result):
            leftTop = it[0][0]
            if leftTop[0] < 5 or '委比' in it[1]:
                idx = i
                wsstrs = it[1]
            elif idx > 0:
                wsstrs += ' ' + it[1]
        if idx < 0:
            return rs
        
        cc = re.compile('^委比\\s*([+-]?\\d+[.]*\\d*)%\s*([+-]?\\d+)')
        ma = cc.match(wsstrs)
        if not ma:
            return rs
        rs['wb'] = float(ma.group(1))
        rs['diff'] = int(ma.group(2))
        if rs['wb'] < 0 or rs['diff'] < 0:
            rs['wb'] = -abs(rs['wb'])
            rs['diff'] = -abs(rs['diff'])
        return rs
    
    def findStockTitleHwnd(self, parentWnd, after):
        if not parentWnd:
            return
        while True:
            hwnd = win32gui.FindWindowEx(parentWnd, after, None, None)
            if not hwnd:
                break
            cl = win32gui.GetClassName(hwnd)
            if cl == 'stock_title_page':
                self.titleHwnds.add(hwnd)
            else:
                self.findStockTitleHwnd(hwnd, None)
            after = hwnd

    def getCurStockTitleHwnd(self, thsMainWin):
        rs = list(self.titleHwnds)
        for hwnd in rs:
            if not win32gui.IsWindow(hwnd):
                self.titleHwnds.remove(hwnd)
                continue
            if win32gui.IsWindowVisible(hwnd):
                return hwnd
        self.findStockTitleHwnd(thsMainWin, None)
        for hwnd in self.titleHwnds:
            if win32gui.IsWindowVisible(hwnd):
                return hwnd
        return None

    def runOnce(self, thsMainWin):
        hwnd = self.getCurStockTitleHwnd(thsMainWin)
        result = self.dump(hwnd)
        rs = self.parse(result)
        if not rs:
            return
        if ('wb' in rs) and ('diff' in rs):
            bs = self.calcBS(rs['wb'], rs['diff'], rs['price'])
            if bs:
                rs['总买'] = bs[0] # 万元
                rs['总卖'] = bs[1] # 万元
        print(rs)

ths = ths_win.ThsWindow()
ths.init()
obj = ThsOcrUtils()
obj.runOnce(ths.mainHwnd)