import win32gui, win32ui, win32con, re, io
from PIL import Image
import easyocr, ths_win

class ThsOcrUtils:
    def __init__(self) -> None:
        self.titleHwnds = set()
        self.ocr = None
        self.WB_WIN_HEIGHT = 30

    def init(self):
        if not self.ocr:
            self.ocr = easyocr.Reader(['ch_sim'], download_enabled = True )
        
    # wb = 委比 28.45
    # diff = 委差
    # price = 当前成交价
    def calcBS(self, rs):
        wb, diff, price = rs['wb'], rs['diff'], rs['price']
        if wb == 0:
            return
        wb /= 100
        sumv = diff / wb
        b = int((sumv + diff) / 2)
        s = int(b - diff)
        buy = abs(int(b * 100 * price / 10000))
        sell = abs(int(s * 100 * price / 10000))
        rs['buy'] = buy # 万元
        rs['sell'] = sell # 万元

    def dump(self, hwnd):
        if (not win32gui.IsWindow(hwnd)) or (not win32gui.IsWindowVisible(hwnd)):
            return None
        dc = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(dc)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        rc = win32gui.GetWindowRect(hwnd)
        w, h = rc[2] - rc[0], rc[3] - rc[1]
        srcSize = w, h + self.WB_WIN_HEIGHT

        saveBitMap.CreateCompatibleBitmap(mfcDC, *srcSize) # image size W x H
        saveDC.SelectObject(saveBitMap)
        #hbr = win32ui.CreateBrush()
        #hbr.CreateSolidBrush(0x000000)
        #saveDC.FillRect((0, 0, W, H), hbr)
        
        srcPos = 0, 0
        saveDC.BitBlt((0, 0), srcSize, mfcDC, srcPos, win32con.SRCCOPY)
        bmpinfo = saveBitMap.GetInfo()
        self.imgSize = (bmpinfo['bmWidth'], bmpinfo['bmHeight'])
        bits = saveBitMap.GetBitmapBits(True)
        #print(self.imgSize, 'bytes.length = ', len(self.bits))
        img_PIL = Image.frombuffer('RGB',self.imgSize, bits, 'raw', 'BGRX', 0, 1)
        #img_PIL.save('D:/a.bmp')
        #img_PIL.show()
        # destory
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, dc)
        return img_PIL
    
    def parseText(self, result):
        if not result:
            return None
        rs = {}
        cn = result[0][1]
        rs['name'] = cn[0 : len(cn) - 6]
        rs['code'] = cn[-6 : ]

        cc = re.compile('^\\d+[.]\\d{2}')
        px = result[1][1]
        px = px.replace('。', '.')
        ma = cc.match(px)
        if not ma:
            return None
        rs['price'] = float(ma.group(0))
        px = result[1][0]
        rs['price_pos'] = (px[0][0], px[0][1], px[1][0], px[2][1])
        #rs['zdPrice'] = float(result[2][1])
        # find 委比
        wsstrs = ''
        idx = -1
        for i, it in enumerate(result):
            leftTop = it[0][0]
            if leftTop[0] < 5 or '委比' in it[1]:
                idx = i
                wsstrs = it[1]
                px = it[0]
                rs['wb_pos'] = (px[0][0], px[0][1], px[1][0], px[2][1])
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

    def parseNumSign(self, rs : dict, img : Image, name):
        rc = rs[name + '_pos']
        y = (rc[1] + rc[3]) // 2
        #print(rc, 'y = ', y)
        MAX_PIX = 5
        rn, gn = 0, 0
        w, h = img.size
        for x in range(rc[0], max(rc[2], w)):
            r, g, b = img.getpixel((x, y))
            #print(rgb, end = ' ')
            if r > g * 2 and r > b * 2:
                rn += 1
            elif g > r * 2 and g > b * 2:
                gn += 1
            if rn >= MAX_PIX:
                rs[name + '_sign'] = True
                break
            elif gn >= MAX_PIX:
                rs[name + '_sign'] = False
                break

    def runOcr(self, thsMainWin):
        try:
            hwnd = self.getCurStockTitleHwnd(thsMainWin)
            img = self.dump(hwnd)
            if not img:
                return None
            bmpBytes = io.BytesIO()
            img.save(bmpBytes, format = 'bmp')
            bits = bmpBytes.getvalue()
            result = self.ocr.readtext(bits)
            rs = self.parseText(result)
            if (not rs) or ('wb' not in rs) or ('diff' not in rs):
                return None
            #self.parseNumSign(rs, img, 'price')
            self.parseNumSign(rs, img, 'wb')
            if 'wb_sign' in rs:
                rs['wb'] = abs(rs['wb']) if rs['wb_sign'] else -abs(rs['wb'])
                rs['diff'] = abs(rs['diff']) if rs['wb_sign'] else -abs(rs['diff'])
            self.calcBS(rs)
            return rs
        except Exception as e:
            #print('ths_ocr.runOcr Error: ', e)
            pass
        return None

if __name__ == '__main__':
    ths = ths_win.ThsWindow()
    ths.init()
    result = ths.runOnceOcr()
    print(result)