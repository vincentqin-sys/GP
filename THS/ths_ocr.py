import win32gui, win32ui, win32con, re, io, traceback, sys, datetime, time
from PIL import Image
import easyocr

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from THS import ths_win, number_ocr

#委比
class ThsWbOcrUtils(number_ocr.DumpWindowUtils):
    def __init__(self) -> None:
        self.titleHwnds = set()
        self.wbOcr = number_ocr.NumberOCR('wb', '+-.%0123456789')
        self.ocr = easyocr.Reader(['en'], download_enabled = True ) # ch_sim  en

    # wb = 委比 28.45
    # diff = 委差
    # price = 当前成交价
    def calcBS(self, rs):
        if (not rs) or ('wb' not in rs) or ('diff' not in rs):
            return
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

    def dump_InHomePage(self, hwnd):
        if (not hwnd) or (not win32gui.IsWindow(hwnd)) or (not win32gui.IsWindowVisible(hwnd)):
            return None
        rc = win32gui.GetWindowRect(hwnd)
        w, h = rc[2] - rc[0], rc[3] - rc[1]
        WB_WIN_HEIGHT = 28
        srcSize = w, h + WB_WIN_HEIGHT

        imgFull = self.dumpImg(hwnd, (0, 0, *srcSize))
        LEFT_PADDING = 20
        codeImg = imgFull.crop((LEFT_PADDING, 2, w - LEFT_PADDING, h // 2))
        priceImg = imgFull.crop((LEFT_PADDING, h // 2, w - LEFT_PADDING, h - 1))
        #priceImg.save('D:/price.bmp')
        #codeImg.save('D:/code.bmp')
        #img_PIL.show()

        WB_TXT_WIDTH = 35
        r = max(srcSize[0] - 70, w * 0.6)
        wbImg = imgFull.crop((WB_TXT_WIDTH, srcSize[1] - WB_WIN_HEIGHT + 1, int(r), srcSize[1]))
        #sign = bi.calcSign(wbImg)
        #wbImg = bi.expand(wbImg)
        #wbImg.save('D:/a.bmp')
        return codeImg, priceImg, wbImg
    
    def parseCodeName(self, img, rs):
        bmpBytes = io.BytesIO()
        img.save(bmpBytes, format = 'bmp')
        bits = bmpBytes.getvalue()
        result = self.ocr.readtext(bits, allowlist = '0123456789')
        if not result:
            return False
        code = result[0][1]
        if len(code) < 6:
            return False
        rs['code'] = code[-6 : ]
        rs['name'] = ''
        if rs['code'][0 : 2] not in ('00', '30', '60', '68', '88'):
            return False
        return True
    
    def parsePrice(self, img : Image, rs):
        eimg = number_ocr.EImage(img)
        items = eimg.split()
        if not items:
            return False
        maxHeight, sn = 0, 0
        first = items[0]
        rect = [first[0], 0, 0, img.height]
        for it in items:
            h = it[3] - it[1]
            if maxHeight < h:
                maxHeight = h
            if maxHeight - h >= 4:
                sn += 1
            if sn > 1:
                rect[2] = it[0]
                break
        W = rect[2] - rect[0]
        if W <= 0:
            return False
        priceImg = img.crop(tuple(rect))
        bmpBytes = io.BytesIO()
        priceImg.save(bmpBytes, format = 'bmp')
        bits = bmpBytes.getvalue()
        result = self.ocr.readtext(bits, allowlist = '0123456789.')
        if not result:
            return False
        price = ''
        for r in result:
            price += r[1]
        if len(price) < 3:
            return False
        if '.' not in price:
            price = price[0 : -2] + '.' + price[-2 : ]
        rs['price'] = float(price)
        
        # zhang die & zhang fu
        rect[0] = rect[2]
        rect[2] = img.width
        zdzfImg = img.crop(tuple(rect))
        result2 = self.wbOcr.match(zdzfImg)
        if not result2:
            return False
        ma = re.match(r'([-+]\d+\.\d{2})([-+]\d+\.\d{2})%', result2)
        if not ma:
            return False
        rs['zd'] = float(ma.group(1))
        rs['zf'] = float(ma.group(2))
        return True

    def parseWeiBi(self, wbImg, rs):
        wsstrs = self.wbOcr.match(wbImg)
        if not wsstrs:
            return False
        cc = re.compile('^([+-]?\\d+[.]*\\d*)%\s*([+-]?\\d+)')
        ma = cc.match(wsstrs)
        if not ma:
            return False
        rs['wb'] = float(ma.group(1))
        rs['diff'] = int(ma.group(2))
        return True
    
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

    def runOcr_InHomePage(self, thsMainWin):
        rs = {}
        try:
            hwnd = self.getCurStockTitleHwnd(thsMainWin)
            imgs = self.dump_InHomePage(hwnd)
            if not imgs:
                return None
            codeImg, priceImg, wbImg = imgs
            if not self.parseCodeName(codeImg, rs):
                return None
            if not self.parsePrice(priceImg, rs):
                return rs
            if not self.parseWeiBi(wbImg, rs):
                return rs
            self.calcBS(rs)
            return rs
        except Exception as e:
            traceback.print_exc()
            print('ths_ocr:', rs)
        return rs

# 涨速排名
class ThsZhangShuOcrUtils(number_ocr.DumpWindowUtils):
    def __init__(self) -> None:
        super().__init__()
        self.ocr = easyocr.Reader(['en'], download_enabled = True) # ch_sim

    def dump(self, hwnd):
        if (not hwnd) or (not win32gui.IsWindow(hwnd)) or (not win32gui.IsWindowVisible(hwnd)):
            return None
        rc = win32gui.GetWindowRect(hwnd)
        w, h = rc[2] - rc[0], rc[3] - rc[1]
        if w < 500 or h < 200:
            return None
        sx, sy = 250, 50
        ex, ey = 400, h // 2
        imgFull = self.dumpImg(hwnd, (sx, sy, ex, ey))
        #imgFull.save('D:/a.bmp')
        #img_PIL.show()

        #PRICE_LEFT_RIGHT = 30
        #priceImg = imgFull.crop((PRICE_LEFT_RIGHT,  h // 2, w - PRICE_LEFT_RIGHT, h - 1))
        #priceImg.save('D:/price.bmp')

        #WB_TXT_WIDTH = 35
        #r = max(srcSize[0] - 70, w * 0.6)
        #wbImg = imgFull.crop((WB_TXT_WIDTH, srcSize[1] - WB_WIN_HEIGHT + 1, int(r), srcSize[1]))
        #wbImg.save('D:/a.bmp')
        return imgFull
    
    def runOcr(self, thsMainWnd):
        img = self.dump(thsMainWnd)
        if not img:
            return
        #img.save('D:/a.bmp')
        eimg = number_ocr.BaseEImage(img)
        sx = eimg.horSearchBoxColor(0, eimg.bImg.height // 2, 1, 60, 255)
        if sx < 0:
            return
        destEx = -1
        for y in range(5, img.height, 10):
            ex = eimg.horSearchBoxColor(sx + 40, y, 3, 60, 0)
            if ex >= 0:
                destEx = ex
                break
        if destEx < 0:
            return
        dstImg = img.crop((sx + 2, 0, destEx + 3, img.height))
        #dstImg.save('D:/b.bmp')
        bits = self.imgToBmpBytes(dstImg)
        rs = self.ocr.readtext(bits, allowlist ='0123456789')
        arr = []
        now = datetime.datetime.now()
        day = now.year * 10000 + now.month * 100 + now.day
        minuts = now.hour * 100 + now.minute
        for r in rs:
            #print(r)
            if r[2] > 0.7 and len(r[1]) == 6:
                arr.append({'code' : r[1], 'day' : day, 'minuts' : minuts})
        return arr

def test_wb_main1():
    ths = ths_win.ThsWindow()
    ths.init()
    wb = ThsWbOcrUtils()
    while True:
        rs = wb.runOcr_InHomePage(ths.mainHwnd)
        print(rs)
        #break
        time.sleep(3)

def test_zs_main2():
    thsWin = ths_win.ThsWindow()
    thsWin.init()
    thsWin.showMax()
    zs = ThsZhangShuOcrUtils()
    dst = {}
    f = open('D:/zs.txt', 'a')
    while True:
        rs = zs.runOcr(thsWin.mainHwnd)
        for r in rs:
            if r['code'] not in dst:
                dst[r['code']] = r
                f.write(f'{r["day"]} {r["minuts"]} {r["code"]} \n')
        f.flush()
        time.sleep(30)

if __name__ == '__main__':
    test_wb_main1()
    #img = Image.open('D:/a.png')
    #eimg = number_ocr.EImage(img)
    #dimg = eimg.expand()
    #dimg.save('D:/b.bmp')
    pass        