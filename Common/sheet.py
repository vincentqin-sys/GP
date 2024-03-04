import os, sys, re, time, json
import win32gui, win32con
import requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Download import henxin
from Common import base_win, dialog

tasks = base_win.Thread()
tasks.start()

class Cell:
    ATTRS = ('text', 'color', 'bgColor') # 序列化属性
    def __init__(self, sheetWindow):
        self.sheetWindow = sheetWindow
        self.text = None
        self.isFormula = False
        self.hasError = False
        self.error = None
        self.formulaName = None
        self.formulaParams = None
        self.draw = None # function
        self.formulaData = None # formula exec result

    def getText(self):
        return self.text

    def setText(self, txt):
        self.isFormula = False
        if txt == None:
            txt = ''
        elif isinstance(txt, str):
            self.text = txt
        else:
            self.text = str(txt)
        self.loadFormula(self.text)

    # set or del(attrVal is None) attr
    def setAttr(self, attrName, attrVal):
        if attrName == 'text':
            self.setText('' if attrVal == None else attrVal)
            return
        if attrVal == None:
            if hasattr(self, attrName): delattr(self, attrName)
        else:
            setattr(self, attrName, attrVal)

    def loadFormula(self, txt):
        if not txt:
            self.isFormula = False
            self.hasError = False
            return
        if not re.match(r'^\s*=', txt):
            return
        self.isFormula = True
        self.hasError = False
        match = re.match(r'^\s*=\s*(\w+)\s*[(](.*?)[)]\s*$', txt)
        if not match:
            self.hasError = True
            return
        func = match.group(1)
        params = match.group(2).strip()
        if not params:
            params = []
        else:
            params = [p.strip() for p in params.split(',')]
        self.formulaName = func
        self.formulaParams = params
        self.runFormula(func, params)

    def runFormula(self, func, params):
        if func == 'load_GP':
            if len(params) >= 1 and re.match(r'^\d{6}$', params[0]):
                self.draw = self.draw_loadGP
                tasks.addTask(time.time(), self.load_GP, (params[0], ))
            else:
                self.hasError = True
                self.error = 'Param error, except 1 param witch code'

    def load_GP(self, code):
        try:
            hx = henxin.HexinUrl()
            url = hx.getFenShiUrl(code)
            obj = hx.loadUrlData(url)
            rd = obj['data'].split(';')
            if len(rd) > 0:
                its = rd[-1].split(',')
                close = float(its[1])
                pre = float(obj.get('pre', 0))
                zf = (close - pre) / pre * 100 if pre > 0 else 0
                obj['zf'] = zf
            self.formulaData = obj
            self.sheetWindow.invalidWindow()
        except Exception as e:
            print('Exception [sheet.load_GP] ', e)
            self.hasError = True
            self.error = str(e)

    def draw_loadGP(self, hdc, row, col, x, y, cw, ch, mw, mh):
        drawer : base_win.Drawer = self.sheetWindow.drawer
        if not self.formulaData:
            drawer.drawText(hdc, 'Loading...', (x + 3, y, x + max(cw, mw), y + ch), 0x333333, win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
            return
        zf = self.formulaData.get('zf', 0)
        if zf > 0: color = 0x2222ff
        elif zf == 0: color = 0x333333
        else: color = 0x22ff22
        drawer.drawText(hdc, f'{zf :+.02f}%', (x + 3, y, x + max(cw, mw), y + ch), color, win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

    def __repr__(self) -> str:
        return self.text

class CellEditor(base_win.Editor):
    def __init__(self) -> None:
        super().__init__()
        self.maxWidth = 0
        self.row = 0
        self.col = 0
        self.inEdit = False

    def adjustSize(self):
        hdc = win32gui.GetDC(self.hwnd)
        self.drawer.use(hdc, self.drawer.getFont(fontSize=self.css['fontSize']))
        W, H = self.getClientSize()
        tw, *_ = win32gui.GetTextExtentPoint32(hdc, self.text)
        tw += self.paddingX * 2
        win32gui.ReleaseDC(self.hwnd, hdc)
        if tw > W and tw < self.maxWidth:
            tw = min(tw, self.maxWidth)
            win32gui.SetWindowPos(self.hwnd, 0, 0, 0, tw, H, win32con.SWP_NOMOVE | win32con.SWP_NOZORDER)

    def onChar(self, key):
        if key < 32:
            return
        ch = chr(key)
        if not self.text:
            self.text = ch
        else:
            self.text = self.text[0 : self.insertPos] + ch + self.text[self.insertPos : ]
        self.insertPos += 1
        self.adjustSize()
        self.makePosVisible(self.insertPos)

class SheetModel:
    def __init__(self, sheetWindow) -> None:
        self.sheetWindow = sheetWindow
        self.data = {} # cell data, an dict object { (row, col) : Cell, ...}
        self.colStyle = {} # column view style { col: {width: xx} }
        self.rowStyle = {} # row view style {row : {height: xx}}

    # cell = any python object(to str)
    def setCellText(self, row, col, text):
        if row < 0 or col < 0:
            return
        key = (row << 8) | col
        cd = self.data.get(key, None)
        if not cd:
            cd = self.data[key] = Cell(self.sheetWindow)
        cd.setText(text)
    
    def addCell(self, row, col):
        key = (row << 8) | col
        if key not in self.data:
            self.data[key] = Cell(self.sheetWindow)
            return self.data[key]
        return None
    
    def delCell(self, row, col):
        if row < 0 and col < 0:
            self.data.clear()
        elif row < 0: # del column mode
            ks = []
            for k in self.data:
                r, c = (k >> 8) & 0xffffff, k & 0xff
                if c == col:
                    ks.append(k)
            for k in ks:
                del self.data[k]
        elif col < 0:  # del row mode
            ks = []
            for k in self.data:
                r, c = (k >> 8) & 0xffffff, k & 0xff
                if r == row:
                    ks.append(k)
            for k in ks:
                del self.data[k]
        else: # delete cell mode
            k = (row << 8) | col
            if k in self.data:
                del self.data[k]

    def getCell(self, row, col):
        key = (row << 8) | col
        #key = (row, col)
        return self.data.get(key, None)

    def insertRow(self, rowIdx, insertNum = 1):
        if rowIdx < 0 or insertNum <= 0:
            return
        keys = []
        for k in self.data:
            r = (k >> 8) & 0xffffff
            if r >= rowIdx:
                keys.append(k)
        keys.sort(key = lambda d : (d >> 8) & 0xffffff, reverse=True)
        for k in keys:
            r, c = (k >> 8) & 0xffffff, k & 0xff
            r += insertNum
            self.data[(r << 8) | c] = self.data[k]
            del self.data[k]

    def insertColumn(self, colIdx, insertNum = 1):
        if colIdx < 0 or insertNum <= 0:
            return
        keys = []
        for k in self.data:
            r, c = (k >> 8) & 0xffffff, k & 0xff
            if c >= colIdx:
                keys.append(k)
        keys.sort(key = lambda d : d & 0xff, reverse=True)
        for k in keys:
            r, c = (k >> 8) & 0xffffff, k & 0xff
            c += insertNum
            self.data[(r << 8) | c] = self.data[k]
            del self.data[k]

    def delRow(self, rowIdx, delNum = 1):
        if rowIdx < 0 or delNum <= 0:
            return
        keys = []
        for k in self.data:
            r, c = (k >> 8) & 0xffffff, k & 0xff
            if r >= rowIdx:
                keys.append(k)
        keys.sort(key = lambda d : (d >> 8) & 0xffffff)
        for k in keys:
            r, c = (k >> 8) & 0xffffff, k & 0xff
            if r >= rowIdx and r < rowIdx + delNum:
                del self.data[k]
            else:
                r -= delNum
                self.data[(r << 8) | c] = self.data[k]
                del self.data[k]

    def delColumn(self, colIdx, delNum = 1):
        if colIdx < 0 or delNum <= 0:
            return
        keys = []
        for k in self.data:
            r, c = (k >> 8) & 0xffffff, k & 0xff
            if c >= colIdx:
                keys.append(k)
        keys.sort(key = lambda d : d & 0xff)
        for k in keys:
            r, c = (k >> 8) & 0xffffff, k & 0xff
            if c >= colIdx and c < colIdx + delNum:
                del self.data[k]
            else:
                c -= delNum
                self.data[(r << 8) | c] = self.data[k]
                del self.data[k]

    # range = (left, top) or (left, top, right, bottom), contains right, bottom cell
    def clearRange(self, _range):
        if not _range:
            return
        if len(_range) == 2:
            self.delCell(_range[0], _range[1])
            return
        # range is 4
        sr, er = min(_range[0], _range[2]), max(_range[0], _range[2])
        sc, ec = min(_range[1], _range[3]), max(_range[1], _range[3])
        for r in range(sr, er + 1):
            for c in range(sc, ec + 1):
                self.delCell(r, c)

    # return (row-num, col-num)
    def getMaxRowColNum(self):
        mr, mc = -1, -1
        for k in self.data:
            r, c = (k >> 8) & 0xffffff, k & 0xff
            mr = max(r, mr)
            mc = max(c, mc)
        return mr + 1, mc + 1

    def getColumnStyle(self, col):
        return self.colStyle.get(col, None)
    
    def getRowStyle(self, row):
        return self.rowStyle.get(row, None)

    def unserialize(self, srcData):
        self.data = {}
        self.colStyle = {}
        self.rowStyle = {}
        if not srcData:
            return
        js = json.loads(srcData)
        rcData = js['data']
        for k in rcData:
            cell = rcData[k]
            sdata = Cell(self.sheetWindow)
            self.data[int(k)] = sdata
            for cc in cell:
                if cc == 'text': sdata.setText(cell[cc])
                else: setattr(sdata, cc, cell[cc])
        cs = js['colStyle']
        for k in cs:
            self.colStyle[int(k)] = cs[k]
        rs = js['rowStyle']
        for k in rs:
            self.rowStyle[int(k)] = rs[k]

    def serialize(self):
        data = {}
        for k in self.data:
            cell = self.data[k]
            data[k] = {}
            for m in Cell.ATTRS:
                if hasattr(cell, m): data[k][m] = getattr(cell, m)
        rs = {'rowStyle': self.rowStyle, 'colStyle': self.colStyle, 'data': data}
        val = json.dumps(rs, ensure_ascii = False)
        return val
        
    def print(self):
        for k in self.data:
            r, c = (k >> 8) & 0xffffff, k & 0xff
            print((r, c), '=', self.data[k].getText())

# Listeners can be: 'Save'
class SheetWindow(base_win.BaseWindow):
    COLUMN_HEADER_HEIGHT = 30 # 列头高
    ROW_HEADER_WIDTH = 40 # 行头宽
    DEFAULT_ROW_HEIGHT = 25 # 行高
    DEFAULT_COL_WIDTH = 80 # 列宽

    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0xf3f3f3
        self.css['textColor'] = 0x333333
        self.model = SheetModel(self)
        self.startRow = 0
        self.startCol = 0
        self.selRange = None # (startRow, startCol, endRow?, endCol?)
        self.editer = CellEditor()
        self.editer.css['bgColor'] = 0xffd3ff
        self.editer.css['borderColor'] = self.css['bgColor']
        self.editer.addListener(self.onPressEnter, None)

    def colIdxToChar(self, col):
        if col < 0:
            return ''
        if col < 26:
            return chr(ord('A') + col)
        p = chr(ord('A') + col // 26)
        e = chr(ord('A') + col % 26)
        return p + e

    def drawGridLines(self, hdc):
        sdc = win32gui.SaveDC(hdc)
        W, H = self.getClientSize()
        headerBgColor = 0xcccccc
        lineColor = 0xaaaaaa
        self.drawer.fillRect(hdc, (0, 0, W, self.COLUMN_HEADER_HEIGHT), headerBgColor)
        self.drawer.fillRect(hdc, (0, 0, self.ROW_HEADER_WIDTH, H), headerBgColor)
        # draw column headers
        sx = self.ROW_HEADER_WIDTH
        col = self.startCol
        self.drawer.use(hdc, self.drawer.getFont(fontSize = 16, weight = 800))
        while sx < W:
            cw = self.getColumnWidth(col)
            self.drawer.drawLine(hdc, sx, 0, sx, H, lineColor)
            self.drawer.drawText(hdc, self.colIdxToChar(col), (sx, 0, sx + cw, self.COLUMN_HEADER_HEIGHT), 0x303030, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
            sx += cw
            col += 1
        # draw row headers
        sy = self.COLUMN_HEADER_HEIGHT
        row = self.startRow
        while sy < H:
            ch = self.getRowHeight(row)
            self.drawer.drawLine(hdc, 0, sy, W, sy, lineColor)
            self.drawer.drawText(hdc, f'{row + 1}', (0, sy, self.ROW_HEADER_WIDTH, sy + ch), 0x303030, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
            sy += ch
            row += 1
        win32gui.RestoreDC(hdc, sdc)
    
    def getColumnWidth(self, col):
        st = self.model.getColumnStyle(col)
        if st and 'width' in st:
            return st['width']
        return self.DEFAULT_COL_WIDTH

    def getRowHeight(self, row):
        st = self.model.getRowStyle(row)
        if st and 'height' in st:
            return st['height']
        return self.DEFAULT_ROW_HEIGHT

    def getRowHeight(self, row):
        if row < 0:
            return 0
        rs = self.model.rowStyle.get(row, None)
        if rs == None or 'height' not in rs:
            return self.DEFAULT_ROW_HEIGHT
        return rs['height']

    def setRowHeight(self, row, height):
        if row < 0 or height < 0:
            return
        rs = self.model.rowStyle.get(row, None)
        if rs == None:
            rs = self.model.rowStyle[row] = {}
        rs['height'] = height
    
    def getColWidth(self, col):
        if col < 0:
            return 0
        rs = self.model.colStyle.get(col, None)
        if rs == None or 'width' not in rs:
            return self.DEFAULT_COL_WIDTH
        return rs['width']
    
    def setColWidth(self, col, width):
        if col < 0 or width < 0:
            return
        rs = self.model.colStyle.get(col, None)
        if rs == None:
            rs = self.model.colStyle[col] = {}
        rs['width'] = width

    # set attr , or delete attr (attrVal is None)
    def setCellAttr(self, row, col, attrName, attrVal):
        cell = self.model.getCell(row, col)
        if attrVal == None:
            if cell and hasattr(cell, attrName):
                delattr(cell, attrName)
            return
        if not cell:
            cell = self.model.addCell(row, col)
        cell.setAttr(attrName, attrVal)

    def setCellColor(self, row, col, color):
        self.setCellAttr(row, col, 'color', color)

    def setCellBgColor(self, row, col, color):
        self.setCellAttr(row, col, 'bgColor', color)

    def clearCellFormat(self, row, col):
        cell = self.model.getCell(row, col)
        if not cell:
            return
        cell.setAttr('color', None)
        cell.setAttr('bgColor', None)
    
    def clearRangeCellFormat(self, range_):
        self.setRangeCellAttr(range_, 'color', None)
        self.setRangeCellAttr(range_, 'bgColor', None)
    
    # return (left, top, right, bottom)
    def formatRange(self, range_):
        if not range_:
            return None
        if len(self.selRange) == 2:
            sr, sc = self.selRange
            er = sr
            ec = sc
        else:
            sr, sc, er, ec = self.selRange
        sc, ec = min(sc, ec), max(sc, ec)
        sr, er = min(sr, er), max(sr, er)
        return (sr, sc, er, ec)
    
    # param range_ is (left, top) or (left, top, right, bottom)
    # attrVal is None : clear this attr
    def setRangeCellAttr(self, range_, attrName, attrVal):
        range_ = self.formatRange(range_)
        if not range_:
            return
        sr, sc, er, ec = range_
        for k in self.model.data:
            r, c = (k >> 8) & 0xffffff, k & 0xff
            if sr < 0: # column mode
                if c >= sc and c <= ec:
                    self.setCellAttr(r, c, attrName, attrVal)
            elif sc < 0: # row mode
                if r >= sr and r <= er:
                    self.setCellAttr(r, c, attrName, attrVal)
        if sr >= 0 and sc >= 0: # cell mode
            for r in range(sr, er + 1):
                for c in range(sc, ec + 1):
                    self.setCellAttr(r, c, attrName, attrVal)

    # -1 is on headers
    def getRowAtY(self, y):
        if y < self.COLUMN_HEADER_HEIGHT:
            return -1
        y -= self.COLUMN_HEADER_HEIGHT
        row = self.startRow
        while y >= 0:
            ch = self.getRowHeight(row)
            if y < ch:
                return row
            row += 1
            y -= ch
        return -2
    
    # -1 is on headers
    def getColAtX(self, x):
        if x < self.ROW_HEADER_WIDTH:
            return -1
        x -= self.ROW_HEADER_WIDTH
        col = self.startCol
        while x >= 0:
            cw = self.getColumnWidth(col)
            if x < cw:
                return col
            col += 1
            x -= cw
        return -2

    def getXOfCol(self, col):
        if col == -1:
            return 0
        if col < -1 or col < self.startCol:
            return -1
        sx = self.ROW_HEADER_WIDTH
        for i in range(self.startCol, col):
            sx += self.getColumnWidth(i)
        return sx

    def getYOfRow(self, row):
        if row == -1:
            return 0
        if row < -1 or row < self.startRow:
            return -1
        sy = self.COLUMN_HEADER_HEIGHT
        for i in range(self.startRow, row):
            sy += self.getRowHeight(i)
        return sy
    
    def getLastVisibleRow(self):
        W, H = self.getClientSize()
        sy = self.COLUMN_HEADER_HEIGHT
        row = self.startRow
        while sy < H:
            ch = self.getRowHeight(row)
            sy += ch
            if sy >= H:
                return row
            row += 1
        return row
    
    def getLastVisibleCol(self):
        W, H = self.getClientSize()
        sx = self.ROW_HEADER_WIDTH
        col = self.startCol
        while sx < W:
            cw = self.getColumnWidth(col)
            sx += cw
            if sx >= W:
                return col
            col += 1
        return col
    
    def isCellInSelRange(self, row, col):
        if row < 0 or col < 0 or not self.selRange:
            return False
        sr, sc, er, ec = self.formatRange(self.selRange)
        if sr >= 0:
            if row < sr or row > er:
                return False
        if sc >= 0:
            if col < sc or col > ec:
                return False
        return True

    def getSelRangeRect(self):
        if not self.selRange:
            return None
        if self.selRange[0] < -1 or self.selRange[1] < -1:
            return None
        sr, sc, er, ec = self.formatRange(self.selRange)
        W, H = self.getClientSize()
        sx = self.getXOfCol(sc)
        ex = self.getXOfCol(ec + 1)
        sy = self.getYOfRow(sr)
        ey = self.getYOfRow(er + 1)
        
        if sr == -1: # col select mode
            rc = [sx, self.COLUMN_HEADER_HEIGHT, ex, H]
        elif sc == -1: # row select mode
            rc = [self.ROW_HEADER_WIDTH, sy, W, ey]
        else: # cell select mode
            rc = [sx, sy, ex, ey]
        if ex < 0 or ey < 0:
            return None
        rc[0] = max(rc[0], 0)
        rc[1] = max(rc[1], 0)
        return rc

    def drawSelRange(self, hdc):
        rc = self.getSelRangeRect()
        if not rc:
            return
        #win32gui.SetROP2(hdc, win32con.R2_MERGEPEN)
        self.drawer.fillRect(hdc, rc, 0xffdddd)
        #win32gui.SetROP2(hdc, win32con.R2_COPYPEN)

    def drawCell(self, hdc, row, col, x, y, cw, ch, mw, mh):
        cell = self.model.getCell(row, col)
        if not cell:
            return
        if cell.hasError:
            self.drawer.drawText(hdc, cell.error, (x + 3, y, mw, y + ch), 0x3333cc, win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
            return
        if cell.draw:
            cell.draw(hdc, row, col, x, y, cw, ch, mw, mh)
            return
        color = self.css['textColor']
        if hasattr(cell, 'color'):
            color = cell.color
        if hasattr(cell, 'bgColor') and not self.isCellInSelRange(row, col):
            self.drawer.fillRect(hdc, (x + 1, y + 1, x + cw, y + ch), cell.bgColor)
        self.drawer.drawText(hdc, cell.text, (x + 3, y, mw, y + ch), color, win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

    def drawGrid(self, hdc):
        if not self.model:
            return
        W, H = self.getClientSize()
        mc = self.getLastVisibleCol() + 1
        mr = self.getLastVisibleRow() + 1
        sy = self.COLUMN_HEADER_HEIGHT
        for r in range(self.startRow, mr):
            sx = self.ROW_HEADER_WIDTH
            rh = self.getRowHeight(r)
            for c in range(self.startCol, mc):
                cw = self.getColumnWidth(c)
                self.drawCell(hdc, r, c, sx, sy, cw, rh, W, H)
                sx += cw
            sy += rh

    def onDraw(self, hdc):
        self.drawSelRange(hdc)
        self.drawGridLines(hdc)
        self.drawGrid(hdc)
    
    # return True: selRange changed, False un-changed
    def setEndSelRange(self, row, col):
        if not self.selRange:
            return False
        rg = self.selRange
        if rg[0] <= -1 and rg[1] <= -1:
            return False
        if row < -1 or col < -1:
            return False
        if row == -1 and col == -1:
            return False
        # col select mode
        if rg[0] < 0:
            lc = rg[3] if len(rg) == 4 else -2
            if lc != col:
                self.selRange = (rg[0], rg[1], rg[0], col)
                return True
            return False
        # row select mode
        if rg[1] < 0:
            lr = rg[2] if len(rg) == 4 else -2
            if lr != row:
                self.selRange = (rg[0], rg[1], row, rg[1])
                return True
            return False
        # cell select mode
        if row >= 0 and col >= 0:
            lr = rg[2] if len(rg) == 4 else -2
            lc = rg[3] if len(rg) == 4 else -2
            if lr != row or lc != col:
                self.selRange = (rg[0], rg[1], row, col)
                return True
        return False

    def scrollUpDown(self, delta):
        if delta < 0:
            self.startRow += abs(delta) * 5
            self.invalidWindow()
            return
        sr = self.startRow
        self.startRow = max(0, sr - delta * 5)
        if sr != self.startRow:
            self.invalidWindow()

    def beginEdit(self, row, col):
        if row < 0 or col < 0:
            return
        self.editer.inEdit = True
        self.editer.row = row
        self.editer.col = col
        sx = self.getXOfCol(col) + 1
        sy = self.getYOfRow(row) + 1
        cw = self.getColumnWidth(col) - 2
        ch = self.getRowHeight(row) - 2
        if not self.editer.hwnd:
            self.editer.createWindow(self.hwnd, (0, 0, 1, 1))
        win32gui.SetWindowPos(self.editer.hwnd, 0, sx, sy, cw, ch, win32con.SWP_NOZORDER)
        val = self.model.getCell(row, col)
        txt = ''
        if val: txt = val.getText()
        self.editer.setText(txt)
        W, H = self.getClientSize()
        self.editer.maxWidth = W - sx
        self.editer.adjustSize()
        win32gui.ShowWindow(self.editer.hwnd, win32con.SW_SHOW)
        win32gui.SetFocus(self.editer.hwnd)

    def endEdit(self):
        if not self.editer.inEdit:
            return
        self.editer.inEdit = False
        win32gui.ShowWindow(self.editer.hwnd, win32con.SW_HIDE)
        txt = self.editer.text
        cell = self.model.getCell(self.editer.row, self.editer.col)
        if not txt and not cell:
            pass
        else:
            self.model.setCellText(self.editer.row, self.editer.col, txt)
        win32gui.SetFocus(self.hwnd)

    def onPressEnter(self, evtName, evtInfo, args):
        self.endEdit()

    def onContextMenu(self, row, col):
        x, y = win32gui.GetCursorPos()
        model = [{'title': '插入行', 'enable': row >= 0, 'name': 'InsertRow', 'pos': row},
                 {'title': '插入列', 'enable': col >= 0, 'name': 'InsertCol', 'pos': col},
                 {'title': 'LINE'},
                 {'title': '删除行', 'enable': row >= 0, 'name': 'DelRow', 'pos': row},
                 {'title': '删除列', 'enable': col >= 0, 'name': 'DelCol', 'pos': col},
                 {'title': 'LINE'},
                 {'title': '设置行高', 'enable': row >= 0 and col < 0, 'name': 'SetRowHeight', 'pos': row},
                 {'title': '设置列宽', 'enable': col >= 0 and row < 0, 'name': 'SetColWidth', 'pos': col},
                 {'title': '设置颜色', 'enable': col >= 0 and row >= 0, 'name': 'SetColor', 'range': self.selRange, 'x': x, 'y': y},
                 {'title': '设置背景色', 'enable': col >= 0 and row >= 0, 'name': 'SetBgColor', 'range': self.selRange, 'x': x, 'y': y},
                 {'title': '清除格式', 'enable': col >= 0 and row >= 0, 'name': 'ClearFormat', 'range': self.selRange, 'x': x, 'y': y},
                 {'title': 'LINE'},
                 {'title': '保存', 'name': 'Save'},
                 ]

        menu = base_win.PopupMenuHelper.create(self.hwnd, model, self.onContextMenuItemSelect)
        menu.show(x, y)

    def onContextMenuItemSelect(self, evtName, evtInfo, args):
        #print('menu select: ', evtName, evtInfo)
        pos = int(evtInfo.get('pos', 0))
        if evtInfo['name'] == 'InsertRow':
            self.model.insertRow(pos)
        elif evtInfo['name'] == 'InsertCol':
            self.model.insertColumn(pos)
        elif evtInfo['name'] == 'DelRow':
            self.model.delRow(pos)
        elif evtInfo['name'] == 'DelCol':
            self.model.delColumn(pos)
        elif evtInfo['name'] == 'SetRowHeight':
            dlg = dialog.InputDialog()
            dlg.createWindow(self.hwnd, (0, 0, 200, 70))
            win32gui.SetWindowText(dlg.hwnd, f'设置行高（第{pos + 1}行）')
            dlg.setText(self.getRowHeight(pos))
            def callback_1(evtName, evtInfo, row):
                txt = dlg.getText().strip()
                if re.match(r'^\d+$', txt):
                    self.setRowHeight(pos, int(txt))
                self.invalidWindow()
            dlg.addListener(callback_1, pos)
            dlg.selectAll()
            dlg.showCenter()
        elif evtInfo['name'] == 'SetColWidth':
            dlg = dialog.InputDialog()
            dlg.createWindow(self.hwnd, (0, 0, 200, 70))
            win32gui.SetWindowText(dlg.hwnd, f'设置列宽（第{self.colIdxToChar(pos)}列）')
            dlg.setText(self.getColWidth(pos))
            def callback_2(evtName, evtInfo, col):
                txt = dlg.getText().strip()
                if re.match(r'^\d+$', txt):
                    self.setColWidth(col, int(txt))
                self.invalidWindow()
            dlg.addListener(callback_2, pos)
            dlg.selectAll()
            dlg.showCenter()
        elif evtInfo['name'] == 'SetColor':
            dlg = dialog.PopupColorWindow()
            dlg.createWindow(self.hwnd)
            def callback_3(evtName, evtInfo, args):
                _range = args
                self.setRangeCellAttr(_range, 'color', evtInfo)
                self.invalidWindow()
            dlg.addListener(callback_3, evtInfo['range'])
            dlg.show(evtInfo['x'], evtInfo['y'])
        elif evtInfo['name'] == 'SetBgColor':
            dlg = dialog.PopupColorWindow()
            dlg.createWindow(self.hwnd)
            def callback_4(evtName, evtInfo, args):
                _range = args
                self.setRangeCellAttr(_range, 'bgColor', evtInfo)
                self.invalidWindow()
            dlg.addListener(callback_4, evtInfo['range'])
            dlg.show(evtInfo['x'], evtInfo['y'])
        elif evtInfo['name'] == 'ClearFormat':
            self.clearRangeCellFormat(evtInfo['range'])
        elif evtInfo['name'] == 'Save':
            print(self.model.serialize())
            self.notifyListener('Save', self.model)
        self.invalidWindow()
        menu = args[1]
        win32gui.DestroyWindow(menu.hwnd)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDOWN:
            self.endEdit()
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            r = self.getRowAtY(y)
            c = self.getColAtX(x)
            if r >= 0 or c >= 0:
                self.selRange = (r, c)
                self.invalidWindow()
            win32gui.SetFocus(self.hwnd)
            return True
        if msg == win32con.WM_MOUSEMOVE:
            if wParam & win32con.MK_LBUTTON:
                x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
                r = self.getRowAtY(y)
                c = self.getColAtX(x)
                if self.setEndSelRange(r, c):
                    self.invalidWindow()
            return True
        if msg == win32con.WM_MOUSEWHEEL:
            delta = (wParam >> 16) & 0xffff
            if delta & 0x8000:
                delta = -(0xffff - delta + 1)
            delta = delta // 120
            self.scrollUpDown(delta)
            return True
        if msg == win32con.WM_LBUTTONDBLCLK:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            r = self.getRowAtY(y)
            c = self.getColAtX(x)
            if r >= 0 and c >= 0:
                self.beginEdit(r, c)
            return True
        if msg == win32con.WM_KEYDOWN:
            if wParam == win32con.VK_LEFT:
                if self.startCol > 0:
                    self.startCol -= 1
                    self.invalidWindow()
            elif wParam == win32con.VK_RIGHT:
                self.startCol += 1
                self.invalidWindow()
            elif wParam == win32con.VK_UP:
                if self.startRow > 0:
                    self.startRow -= 1
                    self.invalidWindow()
            elif wParam == win32con.VK_DOWN:
                self.startRow += 1
                self.invalidWindow()
            elif wParam == win32con.VK_DELETE:
                self.model.clearRange(self.selRange)
                self.invalidWindow()
            return True
        if msg == win32con.WM_RBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            r = self.getRowAtY(y)
            c = self.getColAtX(x)
            if r >= 0 or c >= 0:
                self.onContextMenu(r, c)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

def test():
    class H:
        def __init__(self) -> None:
            self.say = 'Hello'
        def bb(self):
            print('hello')
    a = H()
    print(a.__dict__)

GS = {}
if __name__ == '__main__':
    test()
    sheet = SheetWindow()
    for r in range(5):
        for c in range(4):
            #sheet.model.setCell(r, c, f'{r},{c}')
            pass
    #sx = sheet.model.serialize()
    #print(sx)
    ss = r'{"rowStyle": {"3": {"height": 55}}, "colStyle": {"2": {"width": 120}}, "data": {"0": {"text": "0,0"}, "1": {"text": "0,1"}, "2": {"text": "0,2"}, "3": {"text": "0,3"}, "256": {"text": "1,0"}, "257": {"text": "1,1"}, "258": {"text": "1,2"}, "259": {"text": "1,3", "bgColor": 6750105}, "512": {"text": "2,0"}, "513": {"text": "2,1", "bgColor": 16738047}, "514": {"text": "2,2"}, "515": {"text": "2,3", "bgColor": 6750105}, "768": {"text": "3,0"}, "769": {"text": "3,1", "bgColor": 16738047}, "770": {"text": "3,2", "color": 10092288, "bgColor": 16763904}, "771": {"text": "3,3", "color": 10092288, "bgColor": 6750105}, "1024": {"text": "4,0"}, "1025": {"text": "4,1", "bgColor": 16738047}, "1026": {"text": "4,2"}, "1027": {"text": "4,3", "bgColor": 6750105}, "1281": {"text": "", "bgColor": 16738047}, "1537": {"text": "", "bgColor": 16738047}, "1793": {"text": "", "bgColor": 16738047}, "772": {"text": "", "color": 10092288, "bgColor": 16763904}, "773": {"text": "", "bgColor": 16763904}, "1283": {"text": "", "bgColor": 6750105}, "1282": {"text": "20"}, "1538": {"text": "520你好呀"}}}'
    sheet.model.unserialize(ss)

    sheet.createWindow(None, (0, 0, 1000, 500), win32con.WS_OVERLAPPEDWINDOW, title='I-Sheet')
    win32gui.ShowWindow(sheet.hwnd, win32con.SW_NORMAL)
    win32gui.PumpMessages()