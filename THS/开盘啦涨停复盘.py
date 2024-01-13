import re, peewee as pw
import time, os, platform, sys
from PIL import Image as PIL_Image
import win32gui, win32con , win32api, win32ui # pip install pywin32
import requests, json, hashlib, random, easyocr
import orm
from download import henxin

hx = henxin.HexinUrl()
ocr = easyocr.Reader(['ch_sim','en'])

TMP_FILE = 'D:/_kpl_.bmp'

# 开盘啦截图
class KPL_Image:
    def __init__(self, imgPIL):
        self.imgPIL : PIL_Image = imgPIL
        self.pixs = imgPIL.load()
        #self.pixs = list(self.imgPIL.getdata())
        self.rowsRect = [] # array of (left, top, right, bottom)
        self.width = self.imgPIL.width
        self.height = self.imgPIL.height

    def getPixel(self, x, y):
        #pos = y * self.imgPIL.width + x
        #pix = self.pixs[pos]
        pix = self.pixs[x, y]
        v = (pix[0] << 16) | (pix[1] << 8) | pix[2]
        return v

    def setPixel(self, x, y, color):
        r, g, b = (color >> 16) & 0xff, (color >> 8) & 0xff, color & 0xff
        self.pixs[x, y] = (r, g, b)

    def drawBox(self, rect, color):
        for x in range(rect[0], rect[2]):
            self.setPixel(x, rect[1], color)
        for x in range(rect[0], rect[2]):
            self.setPixel(x, rect[3] - 1, color)
        for y in range(rect[1], rect[3]):
            self.setPixel(rect[0], y, color)
        for y in range(rect[1], rect[3]):
            self.setPixel(rect[2] - 1, y, color)

    def fillBox(self, rect, color):
        for x in range(rect[0], rect[2]):
            for y in range(rect[1], rect[3]):
                self.setPixel(x, y, color)

    # colors = []
    # return y, or -1
    def getRowOfColors(self, sx, ex, sy, ey, colors):
        ey = min(ey, self.height) - len(colors)
        ey = max(ey, sy)
        for i in range(sy, ey):
            rc = False
            for j, color in enumerate(colors):
                rc = self.rowColorIs(sx, ex, i + j, color)
                if not rc:
                    break
            if rc:
                return i
        return -1

    # colors = []
    # return x, or -1
    def getColOfColors(self, sx, ex, sy, ey, colors):
        ex = min(ex, self.width) - len(colors)
        ex = max(sx, ex)
        for i in range(sx, ex):
            rc = False
            for j, color in enumerate(colors):
                rc = self.colColorIs(sy, ey, i + j, color)
                if not rc:
                    break
            if rc:
                return i
        return -1

    def rowColorIs(self, sx, ex, y, color):
        for x in range(sx, min(ex, self.imgPIL.width)):
            if self.getPixel(x, y) != color:
                return False
        return True
    
    # [sy, ey)
    def colColorIs(self, sy, ey, x, color):
        for y in range(sy, min(ey, self.imgPIL.height)):
            ncolor = self.getPixel(x, y)
            if ncolor != color:
                return False
        return True

    def splitRows(self, ROW_HEIGHT = 55):
        rs = []
        startY = self.getRowOfColors(0, 30, 0, self.height, [0xf3f3f3, 0xeeeeee, 0xffffff])
        if startY < 0:
            raise Exception('[KPL_Image.splitRows] startY=', startY)
        startY += 2
        y = startY
        while y < self.height:
            pix0 = self.getPixel(0, y)
            if pix0 == 0xffffff:
                y += 1
                continue
            rowRect = [0, startY, self.width, y]
            startY = y + 1
            if rowRect[3] - rowRect[1] >= ROW_HEIGHT:
                self.rowsRect.append(rowRect)
                #print(rowRect, rowRect[3] - rowRect[1])
            y += 1

    def copyImage(self, rect):
        img = self.imgPIL.crop(rect)
        return img

    # return 0 ~ 100
    # img1, img2 is Image object
    def similar(self, rect, img2, rect2):
        img1 = self
        sx1, sy1, ex1, ey1 = rect
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
            sval = self.similar(rc, img, rect)
            if sval >= similarVal:
                return idx
        return -1
        
    @staticmethod
    def dump(hwnd):
        dc = win32gui.GetWindowDC(hwnd)
        #mdc = win.CreateCompatibleDC(dc)
        mfcDC = win32gui.CreateDCFromHandle(dc)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32gui.CreateBitmap()
        rect = win32gui.GetClientRect(hwnd)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)
        srcSize = (w, h)
        srcPos = (0, 0)
        saveDC.BitBlt((0, 0), srcSize, mfcDC, srcPos, win32con.SRCCOPY)
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        img_PIL = PIL_Image.frombuffer('RGB',(w, h), bmpstr, 'raw', 'BGRX', 0, 1) # bmpinfo['bmWidth']
        # destory
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, dc)
        return KPL_Image(img_PIL)

class KPL_RowImage(KPL_Image):
    # 股票名称、涨停时间、状态、涨停原因
    COLS_INFO = [(0, 150), (140, 240), (270, 380), (400, 515)]
    COL_NAME = COLS_INFO[0]

    def __init__(self, imgPIL: PIL_Image):
        super().__init__(imgPIL)
        self.model = {}

    def parse(self):
        self.splitColName()

    def skipRowSpace(self, rect, sy, down):
        while sy < rect[3] if down else sy >= rect[1]:
            if not self.rowColorIs(rect[0], rect[2], sy, 0xffffff):
                return sy
            sy += 1 if down else -1
        return -1

    def skipColSpace(self, rect, sx):
        while sx < rect[2]:
            if not self.colColorIs(rect[1], rect[3], sx, 0xffffff):
                return sx
            sx += 1
        return -1

    def getMaxColorRate(self, rect, x, y):
        w, h = rect[2] - rect[0], rect[3] - rect[1]
        if w <= 2 or h <= 2:
            return 0
        color = self.getPixel(x, y)
        r, g, b = (color >> 16) & 0xff, (color >> 8) & 0xff, color & 0xff
        if r == 0 or g == 0 or b == 0:
            return 0
        br = max(r / g, r / b)
        return br

    def parseTag(self, rect):
        w, h = rect[2] - rect[0], rect[3] - rect[1]
        br1 = self.getMaxColorRate(rect, rect[0], rect[1] + h // 2)
        br2 = self.getMaxColorRate(rect, rect[2] - 1, rect[1] + h // 2)
        br3 = self.getMaxColorRate(rect, rect[0] + w // 2, rect[1])
        br4 = self.getMaxColorRate(rect, rect[0] + w // 2, rect[3] - 1)
        br = max(br1, br2, br3, br4)
        if br < 2:
            return
        self.fillBox(rect, 0xffffff)
        if br > 3.5:
            if (w >= h - 1 and w <= h + 1):
                self.model['R'] = True
                self.fillBox(rect, 0xffffff)
            else:
                self.model['HF'] = True
                self.fillBox(rect, 0xffffff)

    def splitColName(self):
        y = 20
        while y < self.height:
            if self.rowColorIs(*self.COL_NAME, y, 0xffffff):
                break
            y += 1
        nameRect = [self.COL_NAME[0], 0, self.COL_NAME[1], y]
        codeRect = [self.COL_NAME[0], y + 1, self.COL_NAME[1], self.height]
        nameItemsRect = self.splitVertical(nameRect)
        codeItemRect = self.splitVertical(codeRect)
        for i in range(0, len(nameItemsRect)):
            self.parseTag(nameItemsRect[i])
        #for i in range(0, len(codeItemRect)):
        #    self.parseTag(codeItemRect[i])
        

    def splitVertical(self, rect):
        items = []
        x = rect[0]
        while x < rect[2]:
            x = self.skipColSpace(rect, x)
            if x < 0:
                break
            bx = x
            while not self.colColorIs(rect[1], rect[3], x, 0xffffff):
                x += 1
            ex = x
            if bx == ex:
                continue
            itrect = [bx, rect[1], ex, rect[3]]
            self.trimHorizontal(itrect)
            items.append(itrect)
        return items

    def trimHorizontal(self, rect):
        y = self.skipRowSpace(rect, rect[1], True)
        if y >= 0:
            rect[1] = y
        y = self.skipRowSpace(rect, rect[3] - 1, False)
        if y >= 0:
            rect[3] = y + 1
    
    def caclColorNumber(self, rect, color):
        sx, sy, ex, ey = rect
        nb = 0
        for x in range(sx, ex):
            for y in range(sy, ey):
                if self.getPixel(x, y) == color:
                    nb += 1
        return nb

def format(day, txt):
    lines = txt.splitlines()
    codeNum = 0
    rs = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        if len(line) == 5:
            break
        m = re.match('(.*?)\s*(\d+)\s*(.*)', line)
        name, code, tag = m.groups()
        rs.append([name, code, tag])
        codeNum += 1

    lines = lines[i : ]
    if len(lines) % codeNum != 0:
        raise Exception('error')
    times = lines[0 : codeNum]
    status = lines[codeNum : codeNum * 2]
    reason = lines[codeNum * 2: codeNum * 3]
    for i, r in enumerate(rs):
        r.append(times[i])
        r.append(status[i])
        r.append(reason[i])
        r.append(day)
        print(r)
    return rs

def save(day, code, name, ztTime, status, ztReason, tag):
    count = orm.THS_ZT_FuPan.select(pw.fn.count(orm.THS_ZT_FuPan.code)).where(orm.THS_ZT_FuPan.code == code, orm.THS_ZT_FuPan.day == day)
    #print(count.sql())
    count = count.scalar()
    if not count:
        orm.THS_ZT_FuPan.create(name=name, code=code, tag=tag, ztTime=ztTime, status=status, ztReason=ztReason, day=day)
    else:
        print('重复项：', day, code, name, ztTime, status, ztReason, tag)

def parseRow(img):
    img.parse()
    #img.imgPIL.show()
    img.imgPIL.save(TMP_FILE)
    result = ocr.readtext(TMP_FILE)
    if len(result) >= 5:
        img.model['name'] = result[0][1]
        img.model['ztTime'] = result[1][1]
        img.model['status'] = result[2][1]
        rz = result[3][1]
        if (rz[-1] == '1') and (')' not in rz):
            rz = rz[0 : -1] + ')'
        img.model['ztReason'] = rz
        img.model['code'] = result[4][1][0 : 6]
        tag = ''
        if 'R' in img.model:
            tag += '(融)'
        if 'HF' in img.model:
            tag += '回封'
        img.model['tag'] = tag
    return img.model

def checkModel(model):
    mc = model['code']
    if len(mc) != 6:
        return False
    obj = orm.THS_Newest.get_or_none(orm.THS_Newest.code == mc)
    if obj and obj.name == model['name']:
        return True
    *_, name = hx.loadUrlData(hx.getTodayKLineUrl(mc))
    if model['name'] == name:
        return True
    obj = orm.THS_Newest.get_or_none(orm.THS_Newest.name == model['name'])
    if not obj:
        return False
    # check code 
    flag = True
    for i, c in enumerate(obj.code):
        f = (c == mc[i]) or (c == '1' and mc[i] == '7') or (c == '7' and mc[i] == '1')
        flag = flag and f
    
    if flag:
        model['code'] = obj.code # use sugguest code
        return True
    return False

def getCurrentDay(img):
    kimg = KPL_Image(img)
    sy = kimg.getRowOfColors(kimg.width // 2, kimg.width // 2 + 100, 1, 100, [0xe93030, 0xf17777, 0xffffff])
    if sy < 0:
        raise Exception('[getCurrentDay] fail not find current day line')
    sy += 3
    sx = kimg.width // 2
    ey = kimg.getRowOfColors(sx, sx + 50, sy, sy + 100, [0xf8f8f8])
    if ey < 0:
        ey = sy + 100
    rect = [sx, sy, kimg.width, ey]
    dimg = kimg.copyImage(rect)
    #dimg.show()
    dimg.save(TMP_FILE)
    rs = ocr.readtext(TMP_FILE)
    for r in rs:
        txt = r[1]
        if len(txt) == 10:
            return txt
    raise Exception('[getCurrentDay] not find current day')

def main():    
    path = r'C:\Users\Administrator\Desktop\b.png'
    pimg = PIL_Image.open(path)
    curDay = getCurrentDay(pimg)
    print('curDay=', curDay)
    img = KPL_Image(pimg)
    img.splitRows()
    for r in img.rowsRect:
        nimg = img.copyImage(r)
        it = KPL_RowImage(nimg)
        model = parseRow(it)
        model['day'] = curDay
        rs = checkModel(model)
        #save(**model)
        info = f"{model['day']}\t{model['name']}\t{model['code']}\t{model['ztTime']}\t{model['status']}\t{model['ztReason']}\t{model['tag']}"
        print(info)
        if not rs:
            print('\tMay be error')
        
if __name__ == '__main__':
    main()