import win32gui, win32con , win32api, win32ui # pip install pywin32
import os, sys

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Common import base_win

class CellRenderWindow(base_win.BaseWindow):

    # templateColumns = 分列, 设置宽度  整数固定: 200 ; 自动: 'auto'; 片段: 1fr | 2fr; 百分比: 15% 
    #       Eg: (200, '1fr', '2fr', '15%')
    def __init__(self, templateColumns, colsGaps = 5) -> None:
        super().__init__()
        self.templateColumns = templateColumns
        self.colsGaps = colsGaps
        self.paddings = (2, 2, 2, 2)
        self.rows = []

    # rowInfo = { height: int | function(cell object), 
    #             bgColor: None | int | function(cell object), 
    #             margin: 0 | int, top margin
    #           }
    # cell = { text: str | function(cell object),
    #          paddings:(l, t, r, b) 可选,
    #          span: int (default is 1) 跨列数
    #          bgColor: None | int | function(cell object), 
    #          color: None | int | function(cell object),
    #          textAlign: int | None,
    #          fontSize: int | None, fontWeight: int | None }
    # cell = function(rowInfo, cellIdx)
    def addRow(self, rowInfo, *cells):
        self.rows.append({'rowInfo': rowInfo, 'cells': cells})

    def getColWidth(self, col, span, colsWidth):
        if span <= 0:
            return 0
        w = 0
        j = 0
        for i in range(0, span):
            if i + col < len(colsWidth):
                w += colsWidth[i + col]
                j += 1
        if j > 0:
            w += (j - 1) * self.colsGaps
        return w

    def _drawRow(self, hdc, rc, rowInfo):
        if 'bgColor' in rowInfo and type(rowInfo['bgColor']) == int:
            self.drawer.fillRect(hdc, rc, rowInfo['bgColor'])

    def _drawCells(self, hdc, cells, colsWidth, sx, sy, rowInfo):
        colIdx = 0
        for i in range(len(cells)):
            cell = cells[i]
            if callable(cell):
                cell = cell(rowInfo, i)
            if cell == None:
                cell = {}
            span = cell.get('span', 1)
            cw = self.getColWidth(colIdx, span, colsWidth)
            rc2 = [sx, sy, sx + cw, sy + rowInfo['height']]
            self.drawCell(hdc, rc2, cell)
            sx += cw + self.colsGaps
            colIdx += span

    def onDraw(self, hdc):
        W, H = self.getClientSize()
        CW = W - self.paddings[0] - self.paddings[2]
        colsWidth = self._parseTemplate(self.templateColumns, CW, self.colsGaps)

        sy = self.paddings[1]
        for row in self.rows:
            sx = self.paddings[0]
            rowInfo = row['rowInfo']
            sy += rowInfo.get('margin', 0)
            rc = (sx, sy, W - self.paddings[2], sy + rowInfo['height'])
            self._drawRow(hdc, rc, rowInfo)
            cells = row['cells']
            self._drawCells(hdc, cells, colsWidth, sx, sy, rowInfo)
            sy += rowInfo['height']

    def drawCell(self, hdc, rect, cell):
        if not cell:
            return
        if 'bgColor' in cell and type(cell['bgColor']) == int:
            self.drawer.fillRect(hdc, rect, cell['bgColor'])
        pd = cell.get('paddings', None)
        if pd:
            rect[0] += pd[0]
            rect[1] += pd[1]
            rect[2] -= pd[2]
            rect[3] -= pd[3]
        fontSize = cell.get('fontSize', self.css['fontSize'])
        fontWeight = cell.get('fontWeight', self.css['fontWeight'])
        self.drawer.use(hdc, self.drawer.getFont(fontSize = fontSize, weight = fontWeight))
        color = cell.get('color', self.css['textColor'])
        align = cell.get('textAlign', win32con.DT_LEFT)
        text = cell.get('text', None)
        txt = None
        if isinstance(text, str):
            txt = text
        elif callable(text):
            txt = text(cell)
        self.drawer.drawText(hdc, txt, rect, color = color, align=align)

    def _parseTemplate(self, template, wh, gap):
        num = len(template)
        vals = [0] * num
        allTp = 0
        for i, tp in enumerate(template):
            if type(tp) == int:
                vals[i] = tp
                continue
            if type(tp) != str:
                raise Exception('Error: unknow template of ', tp)
            tp = tp.strip()
            if '%' == tp[-1]:
                tp = float(tp[0 : -1]) / 100
                vals[i] = int(wh * tp)
                continue
            if tp[-2 : ] == 'fr':
                tp = int(tp[0 : -2])
                allTp += tp
        used = gap * (num - 1)
        for t in vals: used += t
        less = wh - used
        if less <= 0:
            return vals
        for i, tp in enumerate(template):
            if type(tp) != str:
                continue
            tp = tp.strip()
            if tp[-2 : ] == 'fr':
                tp = int(tp[0 : -2])
                vals[i] = int(tp * less / allTp)
        for i, tp in enumerate(template):
            if type(tp) == str:
                tp = tp.strip()
            if tp == 'auto':
                vals[i] = int(max(less, 0))
                break
        return vals

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE and wParam != win32con.SIZE_MINIMIZED:
            self.invalidWindow()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

if __name__ == '__main__':
    win = CellRenderWindow((50, 100, '10%', '1fr', '1fr'), 10)
    win.addRow({'height': 40, 'margin': 20}, 
                {'text': '(0, 0)', 'color': 0xff00ff, 'bgColor':0xaabbcc},
                {'text': '(0, 1)', 'color': 0xff00ff, 'bgColor':0xaabbcc},
                {'text': '(0, 2)', 'color': 0xff00ff, 'bgColor':0xaabbcc},
                {'bgColor':0xaabbcc},
                {'text': '(0, 4)', 'color': 0xff00ff, 'bgColor':0xaabbcc},
                )
    win.addRow({'height': 80, 'bgColor_': 0xdd88ff, 'margin': 5},
                {'text': '(0, 0)', 'color': 0xff00ff, 'bgColor':0xdd88ff, 'span': 2},
                {'text': '(0, 2)', 'color': 0xff00ff, 'bgColor':0xdd88ff, 'span': 2},
                {'text': '(0, 4)', 'color': 0xff00ff, 'bgColor':0xdd88ff,  'textAlign': win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE},
                )
    win.createWindow(None, (100, 100, 600, 400), win32con.WS_OVERLAPPEDWINDOW)
    win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)
    win32gui.PumpMessages()