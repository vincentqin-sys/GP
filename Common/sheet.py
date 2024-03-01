import os, sys
import win32gui, win32con
import requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Download import henxin
from Common import base_win

class CellValue:
    def __init__(self, val, type_) -> None:
        self.val = val
        self.type_ = type_  # s: str  f:formual

class SheetModel:
    def __init__(self) -> None:
        self.data = {} # an dict object { (row, col) : CellData, ...}
        self.columnStyle = {} # column view style { col: {width: xx} }
        self.rowStyle = {} # row view style {row : {height: xx}}

    # cell = CellValue | any python object(to str) | None
    def setCell(self, row, col, cell):
        if row < 0 or col < 0:
            print('[SheetModel.setCell] invalue param, row=', row, 'col=', col)
            return
        if not cell:
            self.data[(row, col)] = None
            return
        if isinstance(cell, CellValue):
            self.data[(row, col)] = cell
            return
        val = str(val)
        if val and val[0] == '=':
            self.data[(row, col)] = CellValue(cell, 'f')
        else:
            self.data[(row, col)] = CellValue(cell, 's')
    
    def getCell(self, row, col):
        key = (row, col)
        return self.data.get(key, None)

    def insertRow(self, rowIdx, insertNum = 1):
        if rowIdx < 0 or insertNum <= 0:
            return
        keys = []
        for k in self.data:
            r, c = k
            if r >= rowIdx:
                keys.append(k)
        for k in keys:
            r, c = k
            self.data[(r + insertNum, c)] = self.data[k]
            del self.data[k]

    def insertColumn(self, colIdx, insertNum = 1):
        if colIdx < 0 or insertNum <= 0:
            return
        keys = []
        for k in self.data:
            r, c = k
            if c >= colIdx:
                keys.append(k)
        for k in keys:
            r, c = k
            self.data[(r, c + insertNum)] = self.data[k]
            del self.data[k]

    def delRow(self, rowIdx, delNum = 1):
        if rowIdx < 0 or delNum <= 0:
            return
        keys = []
        for k in self.data:
            r, c = k
            if r >= rowIdx:
                keys.append(k)
        for k in keys:
            r, c = k
            if r >= rowIdx and r < rowIdx + delNum:
                del self.data[k]
            else:
                self.data[(r - delNum, c)] = self.data[k]
                del self.data[k]

    def delColumn(self, colIdx, delNum = 1):
        if colIdx < 0 or delNum <= 0:
            return
        keys = []
        for k in self.data:
            r, c = k
            if c >= colIdx:
                keys.append(k)
        for k in keys:
            r, c = k
            if c >= colIdx and c < colIdx + delNum:
                del self.data[k]
            else:
                self.data[(r, c - delNum)] = self.data[k]
                del self.data[k]

    # return (row-num, col-num)
    def getMaxRowColNum(self):
        mr, mc = -1, -1
        for k in self.data:
            r, c = k
            mr = max(r, mr)
            mc = max(c, mc)
        return mr + 1, mc + 1

    def getColumnStyle(self, col):
        return self.columnStyle.get(col, None)
    
    def getRowStyle(self, row):
        return self.rowStyle.get(row, None)

    def unserialize(self, srcData):
        self.data = {}
        # TODO:

    def serialize(self):
        pass
        # TODO:

class SheetWindow(base_win.BaseWindow):
    COLUMN_HEADER_HEIGHT = 30 # 列头高
    ROW_HEADER_WIDTH = 40 # 行头宽
    DEFAULT_ROW_HEIGHT = 25 # 行高
    DEFAULT_COL_WIDTH = 80 # 列宽

    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0xdddddd
        self.model = SheetModel()
        self.startRow = 0
        self.startCol = 0
        self.selRowCol = None # (row, col)

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

    def onDraw(self, hdc):
        self.drawGridLines(hdc)
        pass

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDOWN:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            r = self.getRowAtY(y)
            c = self.getColAtX(x)
            self.selRowCol = (r, c)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)


if __name__ == '__main__':
    sheet = SheetWindow()
    sheet.createWindow(None, (0, 0, 1000, 500), win32con.WS_OVERLAPPEDWINDOW)
    win32gui.ShowWindow(sheet.hwnd, win32con.SW_NORMAL)
    win32gui.PumpMessages()