import time, os, platform
from PIL import Image
import win32gui as win, win32con , win32api, win32ui # pip install pywin32

class EImage:
    def __init__(self, oimg : Image):
        oimg = oimg.convert('L') # 转为灰度图
        self.imgPIL : Image = oimg.point(lambda v : 0 if v == 0 else 255) # 二值化图片
        self.pixs = list(self.imgPIL.getdata())
        self.itemsRect = [] # array of (left, top, right, bottom)
        self.split()

    def getPixel(self, x, y):
        pos = y * self.imgPIL.width + x
        return self.pixs[pos]

    def rowColorIs(self, sx, ex, y, color):
        for x in range(sx, min(ex, self.imgPIL.width)):
            if self.getPixel(x, y) != color:
                return False
        return True
    
    def colColorIs(self, x, color):
        for y in range(self.imgPIL.height):
            ncolor = self.getPixel(x, y)
            if ncolor != color:
                return False
        return True

    # return [startX, endX)
    def splitVerticalOne(self, startX):
        sx = ex = -1
        for x in range(startX, self.imgPIL.width):
            if not self.colColorIs(x, 0):
                sx = x
                break
        for x in range(sx, self.imgPIL.width):
            if self.colColorIs(x, 0):
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
    
    def splitHorizontalOne(self, sx, ex):
        sy = ey = -1
        for y in range(self.imgPIL.height):
            if not self.rowColorIs(sx, ex, y, 0):
                sy = y
                break
        for y in range(sy, self.imgPIL.height):
            if self.rowColorIs(sx, ex, y, 0):
                ey = y
                break
        return (sy, ey)
    
    def caclColorNumber(self, rect, color):
        sx, sy, ex, ey = rect
        nb = 0
        for x in range(sx, ex):
            for y in range(sy, ey):
                if self.getPixel(x, y) == color:
                    nb += 1
        return nb

    def split(self):
        items = self.splitVertical()
        rs = []
        for sx, ex in items:
            sy, ey = self.splitHorizontalOne(sx, ex)
            rect = (sx, sy, ex, ey)
            rs.append(rect)
        self.itemsRect = rs
        #for it in rs:
        #    sx, sy, ex, ey = it[0]
        #    print(ex - sx, ey - sy, '|', it[1], it[2])

    # return 0 ~ 100
    # img1, img2 is EImage object
    @staticmethod
    def similar(img1, rect1, img2, rect2):
        sx1, sy1, ex1, ey1 = rect1
        sx2, sy2, ex2, ey2 = rect2
        tW, tH = ex1 - sx1, ey1 - sy1
        oW, oH = ex2 - sx2, ey2 - sy2
        if tW != oW or tH != oH:
            return 0 # size not equal
        matchNum = 0
        for x in range(tW):
            for y in range(tH):
                if img1.getPixel(x + sx1, y + sy1) == img2.getPixel(x + sx2, y + sy2):
                    matchNum += 1
        val = matchNum * 100 / (tW * tH)
        return val

    # :param img is EImage object
    # :return an index, not find return -1
    def findSameAs(self, img, rect, similarVal = 100):
        for idx, rc in enumerate(self.itemsRect):
            sval = EImage.similar(self, rc, img, rect)
            if sval >= similarVal:
                return idx
        return -1
        

class NumberOCR:
    def __init__(self):
        key = platform.node()
        self.templateImg = EImage(Image.open(f'ocr-template-{key}.bmp'))
        self.templateDigit = '0123456789'

    def _matchOne(self, oimg : EImage, oRect):
        MIN_SIMILAR_VAL = 95
        idx = self.templateImg.findSameAs(oimg, oRect, MIN_SIMILAR_VAL)
        if idx >= 0:
            return self.templateDigit[idx]
        return '#'

    def match(self, oimg : Image):
        rimg = EImage(oimg)
        rs = ''
        for rect in rimg.itemsRect:
            rs += self._matchOne(rimg, rect)
        return ''.join(rs)

class BuildTemplateImage:
    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.destImg = EImage(Image.new('1', size=(200, 20)))

    def copy(self, eimg : EImage, rect):
        targetImg : Image = self.destImg.imgPIL
        box = eimg.imgPIL.crop(rect)
        #box.show()
        dx = dy = 4
        if len(self.destImg.itemsRect) > 0:
            lastItem = self.destImg.itemsRect[-1]
            dx += lastItem[2]
        targetImg.paste(box, (dx, dy))
        self.destImg = EImage(targetImg)
        targetImg.show()
        pass

    def dump(self):
        if not win.IsWindowVisible(self.hwnd):
            return None
        dc = win.GetWindowDC(self.hwnd)
        #mdc = win.CreateCompatibleDC(dc)
        mfcDC = win32ui.CreateDCFromHandle(dc)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, 50, 20) # image size 50 x 20
        saveDC.SelectObject(saveBitMap)

        srcSize = (30, 17)
        srcPos = (14, 38)
        saveDC.BitBlt((0, 0), srcSize, mfcDC, srcPos, win32con.SRCCOPY)
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        img_PIL = Image.frombuffer('RGB',(bmpinfo['bmWidth'], 17), bmpstr, 'raw', 'BGRX', 0, 1)
        #img_PIL.show()
        #print(img_PIL.getcolors(), img_PIL.mode)
        eimg = EImage(img_PIL)
        for rect in eimg.itemsRect:
            sv = self.destImg.findSameAs(eimg, rect, 100)
            if sv < 0:
                self.copy(eimg, rect)

        # destory
        win.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win.ReleaseDC(self.hwnd, dc)

    def saveTemplate(self):
        while True:
            self.dump()
            time.sleep(0.5)
            if len(self.destImg.itemsRect) >= 10:
                break
        self.destImg.imgPIL.save(f'[c] ocr-template-{platform.node()}.bmp')
    
if __name__ == '__main__':
    print(platform.node())
    # 同花顺分析图中的日期窗口
    THS_SELECT_DAY_HWND = 0X1109C
    dtm = BuildTemplateImage(THS_SELECT_DAY_HWND)
    dtm.saveTemplate()