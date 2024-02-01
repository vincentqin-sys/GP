import re, peewee as pw
import time, os, platform, sys
from PIL import Image as PIL_Image
import win32gui, win32con , win32api, win32ui # pip install pywin32
import requests, json, hashlib, random, easyocr
import pyautogui
import orm
from download import henxin

hx = henxin.HexinUrl()
ocr = easyocr.Reader(['ch_sim','en'])

TMP_FILE = 'D:/_kpl_.bmp'
KPL_OCR_FILE = 'D:/kpl-ocr.txt'

# 开盘啦截图
class KPL_Image:
    startY = -1

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

    def splitRows(self, MIN_ROW_HEIGHT = 50):
        rs = []
        startY = self.getRowOfColors(140, 160, 0, self.height, [0xf3f3f3, 0xeeeeee, 0xffffff])
        if startY < 0:
            startY = self.getRowOfColors(140, 160, 0, self.height, [0xf3f3f3, 0xf9f9f9, 0xffffff])
        if startY > 0:
            KPL_Image.startY = startY
        if startY < 0:
            startY = KPL_Image.startY
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
            if rowRect[3] - rowRect[1] >= MIN_ROW_HEIGHT:
                self.rowsRect.append(rowRect)
                #print(rowRect, rowRect[3] - rowRect[1])
            y += 1

    def checkFinish(self):
        if not self.rowsRect:
            return False
        lastRect = self.rowsRect[-1]
        lastY = lastRect[3] + 5
        if self.height - lastY < 35:
            return False
        white = self.rectIsColor((5, lastY, 140, self.height - 5), 0xffffff)
        return white
    
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

    def rectIsColor(self, rect, color):
        for x in range(rect[0], rect[2], 1):
            for y in range(rect[1], rect[3], 1):
                if self.getPixel(x, y) != color:
                    return False
        return True
    
    def rectExistsColor(self, rect, color):
        for x in range(rect[0], rect[2], 1):
            for y in range(rect[1], rect[3], 1):
                if self.getPixel(x, y) == color:
                    return True
        return False

    # :return (sx, sy, ex, ey), not find return None
    def findRectIsColor(self, srcRect, size, color):
        w, h = size
        for x in range(srcRect[0], srcRect[2]- w, 1):
            for y in range(srcRect[1], srcRect[3] - h, 1):
                if self.rectIsColor((x, y, x + w, y + h), color):
                    return (x, y, x + w, y + h)
        return None
    
    #横向优先查找
    def findRectNotExistsColor(self, srcRect, size, color):
        w, h = size
        for x in range(srcRect[0], srcRect[2]- w, 1):
            for y in range(srcRect[1], srcRect[3] - h, 1):
                if not self.rectExistsColor((x, y, x + w, y + h), color):
                    return (x, y, x + w, y + h)
        return None
    
    #竖向优先查找
    def findRectNotExistsColor2(self, srcRect, size, color):
        w, h = size
        for y in range(srcRect[1], srcRect[3] - h, 1):
            for x in range(srcRect[0], srcRect[2]- w, 1):
                if not self.rectExistsColor((x, y, x + w, y + h), color):
                    return (x, y, x + w, y + h)
        return None
        
    
    @staticmethod
    def dump(hwnd):
        dc = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(dc)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        rect = win32gui.GetClientRect(hwnd)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)
        srcSize = (w, h)
        srcPos = (0, 0)
        saveDC.BitBlt((0, 0), srcSize, mfcDC, srcPos, win32con.SRCCOPY)
        bmpinfo = saveBitMap.GetInfo()
        bits = saveBitMap.GetBitmapBits(True)
        img_PIL = PIL_Image.frombuffer('RGB',(w, h), bits, 'raw', 'BGRX', 0, 1) # bmpinfo['bmWidth']
        # destory
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, dc)
        return img_PIL

class KPL_RowImage(KPL_Image):
    # 股票名称、涨停时间、状态、涨停原因
    COLS_INFO = [(0, 150), (140, 240), (270, 380), (400, 515)]
    COL_NAME = COLS_INFO[0]

    def __init__(self, imgPIL: PIL_Image):
        super().__init__(imgPIL)
        self.model = {}
        self.nameRect = None
        self.codeRect = None

    def isLastEmptyRow(self):
        # last row may be white name
        white = self.rectIsColor((5, 5, self.COL_NAME[1], self.height - 5), 0xffffff)
        return white
    
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
        self.nameRect = [self.COL_NAME[0], 0, self.COL_NAME[1], y]
        self.codeRect = [self.COL_NAME[0], y + 1, self.COL_NAME[1], self.height]
        nameItemsRect = self.splitVertical(self.nameRect)
        codeItemRect = self.splitVertical(self.codeRect)
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

def saveToDB(day, code, name, ztTime, status, ztReason, tag):
    count = orm.KPL_ZT.select(pw.fn.count(orm.KPL_ZT.code)).where(orm.KPL_ZT.code == code, orm.KPL_ZT.day == day)
    #print(count.sql())
    count = count.scalar()
    if not count:
        orm.KPL_ZT.create(name=name, code=code, tag=tag, ztTime=ztTime, status=status, ztReason=ztReason, day=day)
        print('Save success: ', day, name, code)
    else:
        print('重复项：', day, code, name, ztTime, status, ztReason, tag)

class OCRUtil:
    def __init__(self):
        self.kimg = None
        self.curDay = ''
        self.readHeadLineY = -1
        self.leftArrow = None
        self.rightArrow = None
        self.models = []

    def updateImage(self, pilImage):
        self.kimg = KPL_Image(pilImage)
        self.calcReadHeadLineY()
        self.calcLeftRightArrow()
        self.calcCurrentDay()
        self.kimg.splitRows()
        finish = False
        for r in self.kimg.rowsRect:
            nimg = self.kimg.copyImage(r)
            rowImg = KPL_RowImage(nimg)
            if rowImg.isLastEmptyRow():
                finish = True
                break
            model = self.parseRow(rowImg)
            model['day'] = self.curDay
            self.addModel(model)
        self.compareModels()
        if not finish:
            finish = self.kimg.checkFinish()
        return finish

    def compareModels(self):
        for model in self.models:
            if '_success' not in model:
                rs = self.checkModel(model)
                model['_success'] = rs
        for i in range(0, len(self.models) - 1):
            for j in range(i + 1, len(self.models), 1):
                if self.isSameModel(self.models[i], self.models[j]):
                    self.models[j]['_exists'] = True
        for i in range(len(self.models) - 1, -1, -1):
            if '_exists' in self.models[i]:
                self.models.pop(i)

    def writeModels(self, file):
        def fmtName(name):
            apd = 0
            for n in name:
                apd = apd + (1 if ord(n) < 255 else 2)
            return name + ' ' * (8 - apd)
        for model in self.models:
            info = f"{model['day']}\t{fmtName(model['name'])}\t{model['code']}\t{model['ztTime']}\t{model['status']}\t{model['ztReason']}"
            print(info)
            if '新上市' in model['status']:
                continue
            if file:
                file.write(info + '\n')
            if not model['_success']:
                ex = ''
                if '_exception' in model: ex = model['_exception']
                print('\tMaybe error ' + ex)
                if file:
                    file.write( '\tMaybe error'  + ex + '\n')
            if file:
                file.flush()
        print('sum =', len(self.models))
        if file:
            file.flush()
    
    def clearModels(self):
        self.models = []

    def printeModels(self):
        self.writeModels(None)

    def isSameModel(self, model1, model2):
        return (model1['name'] == model2['name']) and (model1['code'] == model2['code']) and (model1['day'] == model2['day'])

    def addModel(self, model):
        for m in self.models:
            if self.isSameModel(model, m):
                return
        self.models.append(model)

    def parseRow(self, img : KPL_RowImage):
        img.parse()
        codePilImg = img.copyImage(img.codeRect)
        code = self.parseCodeRect(codePilImg)
        img.fillBox(img.codeRect, 0xffffff)
        model = self.parseRowImage(img)
        model['code'] = code
        print('[OCRUtil.parseRow]', model)
        return model
    
    def parseCodeRect(self, pilImg):
        pilImg.save(TMP_FILE)
        result = ocr.readtext(TMP_FILE)
        if len(result) < 1:
            raise Exception('[parseCodeRect] fail :', result)
        return result[0][1][0 : 6]

    def parseRowImage(self, img):
        #img.imgPIL.show()
        img.imgPIL.save(TMP_FILE)
        result = ocr.readtext(TMP_FILE)
        if len(result) < 4:
            raise Exception('[parseRow] fail :', result)
        img.model['name'] = result[0][1]
        img.model['ztTime'] = result[1][1]
        img.model['ztTime'] = img.model['ztTime'].replace('.', ':')
        img.model['status'] = result[2][1]
        rz = result[3][1]
        if (rz[-1] == '1' or rz[-1] == '/') and (')' not in rz):
            rz = rz[0 : -1] + ')'
        rz = rz.replace('」', ')')
        rz = rz.replace('}', ')')
        rz = rz.replace(']', ')')
        rz = rz.replace('[', '(')
        rz = rz.replace('{', '(')
        rz = rz.replace('霎', '零')
        rz = rz.replace('井', '并')
        rz = rz.replace('娈', '变')
        if '(' not in rz and rz != '无':
            for i in range(len(rz) - 1, -1, -1):
                if rz[i] != ')' and  not (rz[i] >= '0' and rz[i] <= '9'):
                    if rz == 0:
                        rz = rz + '()'
                    else:
                        rz = rz[0 : i + 1] + '(' + rz[i + 1 : ]
                    break
        if rz != '无' and rz[-1] != ')':
            rz += ')'
        img.model['ztReason'] = rz
        tag = ''
        if 'R' in img.model:
            tag += '(融)'
        if 'HF' in img.model:
            tag += '回封'
        img.model['tag'] = tag
        return img.model

    def checkModel(self, model):
        mc = model['code']
        obj = orm.THS_Newest.get_or_none(orm.THS_Newest.code == mc)
        if obj and obj.name == model['name']:
            return True
        obj = orm.THS_Newest.get_or_none(orm.THS_Newest.name == model['name'])
        if obj:
            flag = True
            for i, c in enumerate(obj.code):
                f = (i >= len(mc)) or (c == mc[i]) or (c == '1' and mc[i] == '7') or (c == '7' and mc[i] == '1') or (c == '8' and mc[i] == '3') or (c == '3' and mc[i] == '8')
                flag = flag and f
            if flag:
                model['code'] = obj.code # use sugguest code
                return True
            model['_exception'] = ' Maybe is ' + obj.code + '? '
            return False
        if len(mc) != 6:
            return False
        try:
            obj = hx.loadUrlData(hx.getTodayKLineUrl(mc))
            name = obj['name']
        except Exception as e:
            model['_exception'] = ' Net check ' + str(e)
            return False
        if model['name'] == name:
            return True
        if model['name'].replace('酉', '西') == name:
            model['name'] = name
            return True
        if model['name'].replace('曰', '日') == name:
            model['name'] = name
            return True
        if model['name'].replace('壬', '王') == name:
            model['name'] = name
            return True
        if model['name'].replace('娈', '变') == name:
            model['name'] = name
            return True
        if model['name'].replace('夭', '天') == name:
            model['name'] = name
            return True
        model['_exception'] = ' Maybe is ' + name + '? '
        return False

    def calcReadHeadLineY(self):
        #color = self.kimg.getPixel(self.kimg.width //2, 80)
        #print(f'{color:x}')
        sy = self.kimg.getRowOfColors(self.kimg.width // 2, self.kimg.width // 2 + 100, 1, 100, [0xffffff])
        if sy < 0:
            raise Exception('[calcReadHeadLineY] fail not find current day line')
        self.readHeadLineY = sy + 3

    def calcCurrentDay(self):
        sy = self.readHeadLineY
        sx = self.leftArrow[2] + 10
        ey = self.kimg.getRowOfColors(sx, sx + 50, sy, sy + 100, [0xf8f8f8])
        if ey < 0:
            ey = sy + 75
        ex = self.rightArrow[0] - 10 if self.rightArrow else self.kimg.width
        rect = [sx, sy, ex, ey]
        upLineRect = self.kimg.findRectNotExistsColor2(rect, (80, 1), 0xffffff)
        rect2= [upLineRect[0], upLineRect[1] + 10, ex, ey]
        downLineRect = self.kimg.findRectNotExistsColor2(rect2, (80, 1), 0xffffff)
        rect = [upLineRect[0] + 2, upLineRect[1] + 2, ex, downLineRect[3] - 2]
        rightLineRect = self.kimg.findRectNotExistsColor2(rect, (15, 1), 0xffffff)
        rect[2] = rightLineRect[0] - 3
        dimg = self.kimg.copyImage(rect)
        #dimg.show()
        dimg.save(TMP_FILE)
        rs = ocr.readtext(TMP_FILE)
        for r in rs:
            txt = r[1]
            if len(txt) == 10:
                self.curDay = txt
                print('[OCRUtil.calcCurrentDay] curDay=', txt)
                return
        raise Exception('[OCRUtil.calcCurrentDay] not find current day')

    def calcLeftRightArrow(self):
        sy = self.readHeadLineY
        sx = self.kimg.width // 2
        rect = [sx, sy, self.kimg.width, sy + 100]
        self.leftArrow = self.kimg.findRectIsColor(rect, (10, 10), 0xDADEE5)
        if not self.leftArrow:
            raise Exception('[calcLeftRightArrow] not find leftArrow of day')
        rect[0] = self.leftArrow[0] + 50
        self.rightArrow = self.kimg.findRectIsColor(rect, (10, 10), 0xDADEE5)
        #self.kimg.fillBox(self.leftArrow, 0xff0000)
        #self.kimg.fillBox(self.rightArrow, 0xff0000)
        #self.kimg.imgPIL.show()

xiaoWnds = {}
def findXiaoYaoWnd():
    xiaoYaoWnd = win32gui.FindWindow('Qt5QWindowIcon', '逍遥模拟器')
    if not xiaoYaoWnd:
        print('Not find 逍遥模拟器')
        return None
    print(f'逍遥模拟器 top hwnd=0x{xiaoYaoWnd :x}')
    xiaoWnds['topWnd'] = xiaoYaoWnd
    hwnd = win32gui.FindWindowEx(xiaoYaoWnd, None, 'Qt5QWindowIcon', 'MainWindowWindow')
    xiaoWnds['mainWnd'] = hwnd
    hwnd = win32gui.FindWindowEx(hwnd, None, 'Qt5QWindowIcon', 'CenterWidgetWindow')
    xiaoWnds['centerWnd'] = hwnd
    hwnd = win32gui.FindWindowEx(hwnd, None, 'Qt5QWindowIcon', 'RenderWindowWindow')
    xiaoWnds['renderWnd'] = hwnd
    hwnd = win32gui.FindWindowEx(hwnd, None, 'subWin', 'sub')
    xiaoWnds['subWin'] = hwnd
    hwnd = win32gui.FindWindowEx(hwnd, None, 'subWin', 'sub')
    print(f'逍遥模拟器 sub hwnd=0x{hwnd :x}')
    xiaoWnds['subWin_2'] = hwnd
    return hwnd

def main_loadFile():
    file = open(KPL_OCR_FILE, encoding='gbk')
    while True:
        line = file.readline().strip()
        if not line:
            break
        its = line.split('\t')
        for i in range(len(its)): its[i] = its[i].strip()
        day, name, code, ztTime, status, ztReason, *_ = its
        saveToDB(day, code, name, ztTime, status, ztReason, '')

def runOpt(opt, util, hwnd):
    if opt == 'r':
        util = OCRUtil()
        pilImage = KPL_Image.dump(hwnd)
        util.updateImage(pilImage)
        util.printeModels()
        print('restart....end')
    elif opt == 'n':
        pilImage = KPL_Image.dump(hwnd)
        finish = util.updateImage(pilImage)
        util.printeModels()
        print('next...end')
        finish = 'Finish' if finish else False
        return finish
    elif opt == 's':
        file = open(KPL_OCR_FILE, 'a')
        util.writeModels(file)
        util.clearModels()
        file.close()
        print('save success')
        notepad = r'C:\Program Files\Notepad++\notepad++.exe'
        win32api.ShellExecute(None, 'open', notepad, KPL_OCR_FILE, None, win32con.SW_SHOW)
    elif opt == 'so':
        file = open(KPL_OCR_FILE, 'a')
        util.writeModels(file)
        util.clearModels()
        file.close()
        print('save success')
    elif opt == 'l':
        main_loadFile()
    elif opt == 'o':
        notepad = r'C:\Program Files\Notepad++\notepad++.exe'
        win32api.ShellExecute(None, 'open', notepad, KPL_OCR_FILE, None, win32con.SW_SHOW)
        pass
    elif opt == 'h':
        hot_main(hwnd, False)
    return True

def main():
    #txt = ocr.readtext(TMP_FILE)
    #print(txt)
    #return
    hwnd = findXiaoYaoWnd() #0x1120610 # 开盘拉窗口
    print('定位到[市场情绪->股票列表->涨停原因排序] ')
    print(f'开盘拉窗口 hwnd=0x{hwnd :x}')
    tip = 'select options: \n\tr = restart  \n\tn = next page down  \n\ts = save to file\n\tl = load file, save to database\n\to = use notepad++ open data file\n\th = load hot[定位到[市场情绪->数据分析]'
    print(tip)
    util = OCRUtil()
    while True:
        opt = input('input select: ').strip()
        runOpt(opt, util, hwnd)

def clickLeftArrow(hwnd, rect):
    win32gui.SetForegroundWindow(xiaoWnds['topWnd'])
    time.sleep(0.5)
    rr = win32gui.GetWindowRect(hwnd)
    x = (rect[0] + rect[2]) // 2 + rr[0]
    y = (rect[1] + rect[3]) // 2 + rr[1]
    pyautogui.click(x, y)

def nextPage(hwnd):
    win32gui.SetForegroundWindow(xiaoWnds['topWnd'])
    rr = win32gui.GetWindowRect(hwnd)
    time.sleep(0.5)
    rect = win32gui.GetClientRect(hwnd)
    x = rect[2] // 2 + rr[0]
    y = rect[3] - 40 + rr[1]
    lastY = KPL_Image.startY + 50 + rr[1]
    lparam = (y << 16) | x
    pyautogui.moveTo(x, y)
    time.sleep(1)
    pyautogui.dragTo(x, lastY, duration=2)

def auto_main():
    hwnd = findXiaoYaoWnd() #0x1120610 # 开盘拉窗口
    print('定位到[市场情绪->股票列表->涨停原因排序] ')
    print(f'开盘拉窗口 hwnd=0x{hwnd :x}')
    util = OCRUtil()
    while True:
        tg = runOpt('n', util, hwnd)
        if tg == 'Finish':
            runOpt('so', util, hwnd)
            clickLeftArrow(hwnd, util.leftArrow)
            time.sleep(3)
        else:
            time.sleep(3)
            nextPage(hwnd)
            time.sleep(3)

def hot_main(hwnd, loop):
    print('定位到[市场情绪->数据分析] ')
    hotRect = [415, 217, 510, 264]
    leftArrowRect = [272, 114, 272, 114]
    dayRect = [295, 103, 384, 126]
    time.sleep(2)
    while True:
        kimg = KPL_Image(KPL_Image.dump(hwnd))
        dayImg = kimg.copyImage(dayRect)
        dayImg.save(TMP_FILE)
        result = ocr.readtext(TMP_FILE)
        curDay = result[0][1]
        hotImg = kimg.copyImage(hotRect)
        hotImg.save(TMP_FILE)
        result = ocr.readtext(TMP_FILE)
        hotVal = result[0][1]
        print(curDay, hotVal, sep='\t')
        # check day
        if not re.match(r'\d{4}-\d{2}-\d{2}', curDay):
            print('\terror day')
            break
        save_KPL_SCQX(curDay, hotVal)
        if not loop:
            break
        clickLeftArrow(hwnd, leftArrowRect)
        time.sleep(3)

def save_KPL_SCQX(day, zhqd):
    obj = orm.KPL_SCQX.get_or_none(orm.KPL_SCQX.day == day)
    if obj:
        obj.zhqd = int(zhqd)
        obj.save()
    else:
        orm.KPL_SCQX.create(day = day, zhqd = zhqd)

if __name__ == '__main__':
    main()