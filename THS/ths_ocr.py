import win32gui, win32ui, win32con, re, io, traceback
from PIL import Image
import easyocr, ths_win

class BitImage:
    def __init__(self, srcImg) -> None:
        oimg = srcImg.convert('L') # 转为灰度图
        self.bImg : Image = oimg.point(lambda v : 0 if v == (0, 0, 0) else 255) # 二值化图片

    def calcSign(self):
        srcImg = self.srcImg
        w, h = srcImg.size
        y = h // 2
        gn, rn = 0, 0
        pixs = srcImg.load()
        for x in range(w):
            r, g, b = pixs[x, y]
            if r > g * 2 and r > b * 2:
                gn += 1
            elif g > r * 2 and g > b * 2:
                rn += 1
            if gn >= 5 or rn >= 5:
                break
        return gn > rn
    
    def expand(self):
        w, h = self.bImg.size
        SPACE_W = 5
        dw = 30
        items = self.splitVertical()
        for it in items:
            dw += it[1] - it[0] + SPACE_W
        destImg = Image.new('RGB', (dw, h), 0)

        destPixs = destImg.load()
        srcPixs = self.bImg.load()
        sdx = 5
        for it in items:
            sx, ex = it
            sdx += SPACE_W
            for x in range(sx, ex):
                sdx += 1
                for y in range(h):
                    destPixs[sdx, y] = srcPixs[x, y]
        #destImg.save('D:/d.bmp')
        return destImg

    def isVerLineEmpty(self, x):
        pixs = self.bImg.load()
        for y in range(self.bImg.height):
            color = pixs[x, y]
            if color != 0:
                return False
        return True

    # return [startX, endX)
    def splitVerticalOne(self, startX):
        sx = ex = -1
        for x in range(startX, self.bImg.width):
            if not self.isVerLineEmpty(x):
                sx = x
                break
        for x in range(sx, self.bImg.width):
            if self.isVerLineEmpty(x):
                ex = x
                break
        return (sx, ex)

    def splitVertical(self):
        items = []
        sx = ex = 0
        while True:
            sx, ex = self.splitVerticalOne(ex)
            if sx < 0 or ex < 0:
                break
            items.append((sx, ex))
        return items

class ThsOcrUtils:
    def __init__(self) -> None:
        self.titleHwnds = set()
        self.ocr = None
        self.WB_WIN_HEIGHT = 28

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
        #bmpinfo = saveBitMap.GetInfo()
        #imgSize = (bmpinfo['bmWidth'], bmpinfo['bmHeight'])
        bits = saveBitMap.GetBitmapBits(True)
        imgFull = Image.frombuffer('RGB',srcSize, bits, 'raw', 'BGRX', 0, 1)
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, dc)
        #imgFull.save('D:/full.bmp')
        #img_PIL.show()

        WB_TXT_WIDTH = 35
        wbImg = imgFull.crop((WB_TXT_WIDTH, srcSize[1] - self.WB_WIN_HEIGHT + 1, int(srcSize[0] - 70), srcSize[1]))
        bi = BitImage()
        sign = bi.calcSign(wbImg)
        wbImg = bi.expand(wbImg)
        #wbImg.save('D:/a.bmp')
        return imgFull, sign, wbImg
    
    def parseText(self, result, wbResult):
        if not result or not wbResult:
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
        # 委比
        ms = map(lambda x: x[1], wbResult)
        wsstrs = ''.join(ms).replace(' ', '')
        cc = re.compile('^([+-]?\\d+[.]*\\d*)%\s*([+-]?\\d+)')
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
            objs = self.dump(hwnd)
            if not objs:
                return None
            img, sign, wbImg = objs
            if not img:
                return None
            bmpBytes = io.BytesIO()
            img.save(bmpBytes, format = 'bmp')
            bits = bmpBytes.getvalue()
            result = self.ocr.readtext(bits)

            bmpBytes = io.BytesIO()
            wbImg.save(bmpBytes, format = 'bmp')
            wbImg.save('D:/wb.bmp')
            bits = bmpBytes.getvalue()
            wbResult = self.ocr.readtext(bits)
            rs = self.parseText(result, wbResult)
            if (not rs) or ('wb' not in rs) or ('diff' not in rs):
                return None
            #self.parseNumSign(rs, img, 'price')
            #self.parseNumSign(rs, img, 'wb')
            rs['wb_sign'] = sign
            rs['wb'] = abs(rs['wb']) if sign else -abs(rs['wb'])
            rs['diff'] = abs(rs['diff']) if sign else -abs(rs['diff'])
            self.calcBS(rs)
            return rs
        except Exception as e:
            #print('ths_ocr.runOcr Error: ', e)
            traceback.print_exc()
            pass
        return None

if __name__ == '__main__':
    #ocr = easyocr.Reader(['ch_sim'], download_enabled = True)
    #xt = ocr.readtext_batched('D:/a.png')
    #print(txt)
    ths = ths_win.ThsWindow()
    ths.init()
    result = ths.runOnceOcr()
    print('result = ', result)