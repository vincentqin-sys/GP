import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy

class BaseWindow:
    bindHwnds = {}

    def __init__(self) -> None:
        self.hwnd = None
        self.oldProc = None
        self.listeners = []
        self.drawer = Drawer.instance()
        self._bitmap = None
        self._bitmapSize = None
        self.cacheBitmap = False
    
    # func = function(target, evtName, evtInfo)
    def addListener(self, target, func):
        self.listeners.append((target, func))

    def notifyListener(self, evtName, evtInfo):
        for ls in self.listeners:
            obj, func = ls
            func(obj, evtName, evtInfo)

    # @param rect = (x, y, width, height)
    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className = 'STATIC', title = ''): #  0x00800000 | 
        self.hwnd = win32gui.CreateWindow(className, title, style, *rect, parentWnd, None, None, None)
        BaseWindow.bindHwnds[self.hwnd] = self
        self.oldProc = win32gui.SetWindowLong(self.hwnd, win32con.GWL_WNDPROC, BaseWindow._WinProc)
        #print(f'[BaseWindow.createWindow] self.oldProc=0x{self.oldProc :x}, title=', title)

    def getClientSize(self):
        if not self.hwnd:
            return None
        l, t, r, b = win32gui.GetClientRect(self.hwnd)
        return (r, b)
    
    # @return True: 已处理事件,  False:未处理事件
    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_PAINT:
            self._draw()
            return True
        if msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return True
        return False

    def _draw(self, fontSize = 14):
        hdc, ps = win32gui.BeginPaint(self.hwnd)
        l, t, r, b = win32gui.GetClientRect(self.hwnd)
        w, h = r - l, b - t
        mdc = win32gui.CreateCompatibleDC(hdc)
        if (not self._bitmap) or (w != self._bitmapSize[0]) or (h != self._bitmapSize[1]):
            if self._bitmap: win32gui.DeleteObject(self._bitmap)
            self._bitmap = bmp = win32gui.CreateCompatibleBitmap(hdc, w, h)
            self._bitmapSize = (w, h)
        else:
            bmp = self._bitmap
        win32gui.SelectObject(mdc, bmp)
        self.drawer.fillRect(mdc, win32gui.GetClientRect(self.hwnd), 0x000000)
        win32gui.SetBkMode(mdc, win32con.TRANSPARENT)
        win32gui.SetTextColor(mdc, 0xffffff)
        self.drawer.use(mdc, self.drawer.getFont(fontSize = 14))
        self.onDraw(mdc)
        win32gui.BitBlt(hdc, 0, 0, w, h, mdc, 0, 0, win32con.SRCCOPY)
        win32gui.EndPaint(self.hwnd, ps)
        win32gui.DeleteObject(mdc)
        if not self.cacheBitmap:
            win32gui.DeleteObject(self._bitmap)
            self._bitmap = None
            self._bitmapSize = None
        return True
        
    def onDraw(self, hdc):
        pass

    @staticmethod
    def _WinProc(hwnd, msg, wParam, lParam):
        self = BaseWindow.bindHwnds[hwnd]
        rs = self.winProc(hwnd, msg, wParam, lParam)
        if rs == True:
            return 0
        if rs != False:
            return rs
        #if self.oldProc:
        #    return win32gui.CallWindowProc(self.oldProc, hwnd, msg, wParam, lParam)
        return win32gui.DefWindowProc(hwnd, msg, wParam, lParam)
    
    def invalidWindow(self):
        win32gui.InvalidateRect(self.hwnd, None, True)

class Thread:
    def __init__(self) -> None:
        self.tasks = []
        self.stoped = False
        self.event = threading.Event()
        self.thread = threading.Thread(target = Thread._run, args=(self,))

    def addTask(self, taskId, fun, args):
        for tk in self.tasks:
            if tk[2] == taskId:
                return
        self.tasks.append((fun, args, taskId))
        self.event.set()

    def start(self):
        self.thread.start()

    def stop(self):
        self.stoped = True
    
    @staticmethod
    def _run(self):
        while not self.stoped:
            if len(self.tasks) == 0:
                self.event.wait()
                self.event.clear()
            else:
                task = self.tasks[0]
                fun, args, taskId,  *_ = task
                fun(*args)
                self.tasks.pop(0)
                print('run task taskId=', taskId)

class Drawer:
    _instance = None

    @staticmethod
    def instance():
        if not Drawer._instance:
            Drawer._instance = Drawer()
        return Drawer._instance

    def __init__(self) -> None:
        self.pens = {}
        self.hbrs = {}
        self.fonts = {}

    def getPen(self, color, style = win32con.PS_SOLID, width = 1):
        if type(color) == int:
            name = f'{style}-{color :06d}-{width}'
            ps = self.pens.get(name, None)
            if not ps:
                ps = self.pens[name] = win32gui.CreatePen(style, width, color)
            return ps
        return None

    def getBrush(self, color):
        if type(color) == int:
            name = f'solid-{color :06d}'
            ps = self.hbrs.get(name, None)
            if not ps:
                ps = self.hbrs[name] = win32gui.CreateSolidBrush(color)
            return ps
        return None

    def getFont(self, name = '新宋体', fontSize = 14):
        key = f'{name}:{fontSize}'
        font = self.fonts.get(key, None)
        if not font:
            a = win32gui.LOGFONT()
            a.lfHeight = fontSize
            a.lfFaceName = name
            self.fonts[key] = font = win32gui.CreateFontIndirect(a)
        return font

    def use(self, hdc, obj):
        if obj:
            win32gui.SelectObject(hdc, obj)

    # rgb = int 0xrrggbb  -> 0xbbggrr
    @staticmethod
    def rgbToColor(rgb):
        r = (rgb >> 16) & 0xff
        g = (rgb >> 8) & 0xff
        b = rgb & 0xff
        return (b << 16) | (g << 8) | r

    # color = int(0xbbggrr color)
    def drawLine(self, hdc, sx, sy, ex, ey, color, style = win32con.PS_SOLID, width = 1):
        ps = self.getPen(color, style, width)
        self.use(hdc, ps)
        win32gui.MoveToEx(hdc, sx, sy)
        win32gui.LineTo(hdc, ex, ey)

    # only draw borders
    # rect = list or tuple (left, top, right, bottom)
    def drawRect(self, hdc, rect, pen):
        if not rect:
            return
        self.use(hdc, pen)
        hbr = win32gui.GetStockObject(win32con.NULL_BRUSH)
        win32gui.SelectObject(hdc, hbr)
        win32gui.Rectangle(hdc, *rect)
    
    def drawRect2(self, hdc, rect, penColor, penStyle = win32con.PS_SOLID, penWidth = 1):
        pen = self.getPen(penColor, penStyle, penWidth)
        self.drawRect(hdc, rect, pen)

    # rect = list or tuple (left, top, right, botton)
    # color = int (0xbbggrr color)
    def fillRect(self, hdc, rect, color):
        if not rect:
            return
        if type(rect) == list:
            rect = tuple(rect)
        hbr = self.getBrush(color)
        win32gui.FillRect(hdc, rect, hbr)
    
    # rect = list or tuple (left, top, right, botton)
    # color = int(0xbbggrr color) | None(not set color)
    def drawText(self, hdc, text, rect, color = None, align = win32con.DT_CENTER):
        if not text or not rect:
            return
        if type(color) == int:
            win32gui.SetTextColor(hdc, color)
        if type(rect) == list:
            rect = tuple(rect)
        win32gui.DrawText(hdc, text, len(text), rect, align)

    # rect = list or tuple (left, top, right, bottom)
    def fillCycle(self, hdc, rect, color):
        if not rect:
            return
        win32gui.SelectObject(hdc, win32gui.GetStockObject(win32con.NULL_PEN))
        self.use(hdc, self.getBrush(color))
        win32gui.Ellipse(hdc, *rect)

class Layout:
    def __init__(self) -> None:
        self.rect = None # (x, y, width, height)

    def resize(self, x, y, width, height):
        self.rect = (x, y, width, height)

class GridLayout(Layout):
    # templateRows = 分行, 设置高度  整数固定: 200 ; 自动: 'auto'; 片段: 1fr | 2fr; 百分比: 15% 
    #       Eg: (200, 'auto', '15%')  fr与auto不能同时出现, auto最多只能有一个
    # templateColumns = 分列, 设置宽度  整数固定: 200 ; 自动: 'auto'; 片段: 1fr | 2fr; 百分比: 15% 
    #       Eg: (200, '1fr', '2fr' '15%')
    # gaps = (行间隙, 列间隙)  Eg:  (5, 10)
    def __init__(self, templateRows, templateColumns, gaps):
        super().__init__()
        self.templateRows = templateRows
        self.templateColumns = templateColumns
        if not gaps: gaps = (0, 0)
        self.gaps = gaps
        self.winsInfo = {}
        self.layouts = {}
    
    # @param style = {  autoFit: True(is default), 
    #            horExpand : int; 0 ( is default) | -1 : right expand all columns |  int(expand num)
    #            verExpand: int;  0 (is default)  | -1 : down expand all rows     |  int(expand num)
    #            priority: 100 (default) 越小越优先计算
    #    }
    # align : left|top|right|bottom
    # @param winType  'HWND', 'Layout', None
    def setContent(self, row, col, win, style = None):
        defaultStyle = {'autoFit' : True, 'horExpand' : 0, 'verExpand' : 0, 'priority': 100}
        if style:
            defaultStyle.update(style)
        self.winsInfo[(row, col)] = {'win' : win, 'style' : defaultStyle, 'content': True, 'position': (row, col)}

    def resize(self, x, y, width, height):
        super().resize(x, y, width, height)
        self.calcLayout(width, height)
        for k in self.layouts:
            winInfo = self.layouts[k]
            if winInfo['content']:
                self.adjustContentRect(x, y, winInfo)

    def parseTemplate(self, template, wh, gap):
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
                vals[i] = max(less, 0)
                break
        return vals

    def calcLayout(self, width, height):
        self.rows = self.parseTemplate(self.templateRows, height, self.gaps[0])
        self.cols = self.parseTemplate(self.templateColumns, width, self.gaps[1])
        self.layouts.clear()
        self.layouts.update(copy.copy(self.winsInfo))
        ls = []
        for r in range(len(self.rows)):
            for c in range(len(self.cols)):
                k = (r, c)
                ws = self.layouts.get(k)
                if ws: ls.append(ws)
        ls.sort(key = lambda d : d['style']['priority'])
        for item in ls:
            pos = item['position']
            item['rect'] = self.calcContentRect(*pos, item)

    def getHorVerExpandEnd(self, row, col, horExpand, verExpand, fill):
        maxCol = len(self.cols) if horExpand < 0 else min(len(self.cols), col + horExpand + 1)
        maxRow = len(self.rows) if verExpand < 0 else min(len(self.rows), row + verExpand + 1)
        if horExpand > 0 or (horExpand < 0 and verExpand < 0 and horExpand < verExpand): # hor first search
            _, endCol = self.getHorExpandEnd(row, col, horExpand, False)
            endRow = row
            for r in range(row + 1, maxRow, 1):
                _, _c = self.getHorExpandEnd(r, col, horExpand, False)
                if _c != endCol:
                    break
                endRow = r
        else: # ver first search
            endRow, _ = self.getVerExpandEnd(row, col, verExpand, False)
            endCol = col
            for c in range(col + 1, maxCol, 1):
                _r, _ = self.getVerExpandEnd(row, c, verExpand, False)
                if _r != endRow:
                    break
                endCol = c
        if not fill:
            return (endRow, endCol)
        for r in range(row, endRow + 1):
            for c in range(col, endCol + 1):
                if r == row and c == col:
                    continue
                self.layouts[(r, c)] = {'win' : None, 'name': f'expand-hor-ver-item({row, col})', 'content': False}
        return (endRow, endCol)

    def getHorExpandEnd(self, row, col, horExpand, fill):
        maxCol = len(self.cols) if horExpand < 0 else min(len(self.cols), col + horExpand + 1)
        rc = col
        for c in range(col + 1, maxCol, 1):
            k = (row, c)
            if (k in self.layouts):
                return (row, rc)
            if fill:
                self.layouts[k] = {'win' : None, 'name': f'expand-hor-item({row, col})', 'content': False}
            rc = c
        return (row, rc)

    def getVerExpandEnd(self, row, col, verExpand, fill):
        maxRow = len(self.rows) if verExpand < 0 else min(len(self.rows), row + verExpand + 1)
        rr = row
        for r in range(row + 1, maxRow, 1):
            k = (r, col)
            if (k in self.layouts):
                return (rr, col)
            if fill:
                self.layouts[k] = {'win' : None, 'name': f'expand-ver-item({row, col})', 'content': False}
            rr = r
        return (rr, col)

    def calcContentRect(self, row, col, winInfo):
        style = winInfo['style']
        horExpand = style['horExpand']
        verExpand = style['verExpand']
        if horExpand != 0 and verExpand != 0:
            endRow, endCol = self.getHorVerExpandEnd(row, col, horExpand, verExpand, True)
        elif horExpand != 0 and verExpand == 0:
            endRow, endCol = self.getHorExpandEnd(row, col, horExpand, True)
        elif horExpand == 0 and verExpand != 0:
            endRow, endCol = self.getVerExpandEnd(row, col, verExpand, True)
        else:
            endRow, endCol = row, col
        rect = self.calcRect(row, col, endRow, endCol)
        return rect

    def getLeftTop(self, row, col):
        y = row * self.gaps[0]
        x = col * self.gaps[1]
        for r in range(0, row):
            y += self.rows[r]
        for c in range(0, col):
            x += self.cols[c]
        return (x, y)

    # return (l, t, r, b)
    def calcRect(self, row, col, endRow, endCol):
        left, top = self.getLeftTop(row, col)
        right, bottom = self.getLeftTop(endRow, endCol)
        right += self.cols[endCol]
        bottom += self.rows[endRow]
        return (left, top, right, bottom)

    def adjustContentRect(self, x, y, winInfo):
        style = winInfo['style']
        win = winInfo['win']
        rect = winInfo.get('rect')
        if not win or not rect:
            return
        w, h = rect[2] - rect[0], rect[3] - rect[1]
        x += rect[0]
        y += rect[1]
        if style['autoFit']:
            if isinstance(win, BaseWindow):
                win32gui.SetWindowPos(win.hwnd, None, x, y, w, h, win32con.SWP_NOZORDER)
            elif type(win) == int:
                # is HWND object
                win32gui.SetWindowPos(win, None, x, y, w, h, win32con.SWP_NOZORDER)
            elif isinstance(win, Layout):
                win.resize(x, y, w, h)
            else:
                print('[GridLayout.adjustContentRect] unsport win type: ', winInfo)

class AbsLayout(Layout):
    def __init__(self) -> None:
        super().__init__()
        self.winsInfo = []

    # win = BaseWindow, HWND, unsupport Layout
    def setContent(self, x, y, win):
        if win:
            self.winsInfo.append({'win': win, 'x' : x, 'y': y})

    def resize(self, x, y, width, height):
        super().resize(x, y, width, height)
        for it in self.winsInfo:
            self.adjustContentRect(x, y, it)

    def adjustContentRect(self, x, y, winInfo):
        win = winInfo['win']
        x += winInfo['x']
        y += winInfo['y']
        if isinstance(win, BaseWindow):
            win32gui.SetWindowPos(win.hwnd, None, x, y, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
        elif type(win) == int:
            win32gui.SetWindowPos(win, None, x, y, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
        elif isinstance(win, Layout):
            win.resize(x, y, win.rect[2], win.rect[3])
        else:
            print('[AbsLayout.adjustContentRect] unsupport win type :', winInfo)

class TableWindow(BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.rowHeight = 18
        self.headHeight = 20
        self.tailHeight = 0
        self.columnCount = 1
        self.startIdx = 0
        self.data = None # a data array

    def getValueAt(self, row, col):
        return None

    def getColumnWidth(self, colIdx):
        w, h = self.getClientSize()
        return w // self.columnCount
    
    def drawColumnHeads(self, hdc):
        if self.headHeight <= 0:
            return

    def drawRow(self, hdc, rowIdx, rect):
        pass

    def drawTail(self, hdc, rect):
        pass

    def getVisibleRange(self):
        pass
    
    def onDraw(self, hdc):
        self.drawColumnHeads(hdc)

    

class ColumnWindow(BaseWindow):
    def __init__(self):
        super().__init__()
        self.columnHeadHeight = 0
        self.rowHeight = 18
        self.columnCount = 1
        self.data = None
        self.columnHead = None # title

    def getColumnHead(self, columnIdx):
        return self.columnHead
    
    def setData(self, data):
        self.data = data

    def getRowNum(self):
        w, h = self.getClientSize()
        h -= self.columnHeadHeight
        return h // self.rowHeight
    
    def getColumnWidth(self):
        w, h = self.getClientSize()
        return w // self.columnCount

    def drawColumnHead(self, hdc, columnIdx):
        if not self.data:
            return
        title = self.getColumnHead(columnIdx)
        cw = self.getColumnWidth()
        rc = (columnIdx * cw, 0, (columnIdx + 1) * cw, self.columnHeadHeight)
        self.drawer.drawText(hdc, title, rc, 0xdddddd)
        self.drawer.drawLine(hdc, rc[0], rc[3] - 1, rc[2], rc[3] - 1, 0xcccccc)

    def drawItemData(self, hdc, columnIdx, rowIdx, idx, data):
        rc = self.getItemRect(columnIdx, rowIdx)
        pass

    def getItemRect(self, col, row):
        sx = col * self.rowHeight
        ex = sx + self.getColumnWidth()
        sy = self.rowHeight * row + self.columnHeadHeight
        ey = sy + self.rowHeight
        return (sx, sy, ex, ey)

    def getVisibleRange(self):
        if not self.data:
            return (0, 0)
        rowNum = self.getRowNum()
        colNum = self.columnCount
        maxNum = rowNum * colNum
        # only show last maxNum items
        dlen = len(self.data)
        if dlen <= maxNum:
            return (0, maxNum)
        return (dlen - maxNum, dlen)

    def onDraw(self, hdc):
        if not self.data:
            return
        rowNum = self.getRowNum()
        colNum = self.columnCount
        begin, end = self.getVisibleRange()
        for i in range(begin, end):
            idx = i - begin
            colIdx = idx // rowNum
            rowIdx = idx % rowNum
            if colIdx >= colNum:
                continue
            itemData = self.data[i]
            self.drawItemData(hdc, colIdx, rowIdx, i, itemData)
        for i in range(0, colNum):
            self.drawColumnHead(hdc, i)
        

def testGridLayout():
    class TestMain(BaseWindow):
        def __init__(self, gl) -> None:
            super().__init__()
            self.gl = gl

        def onDraw(self, hdc):
            win32gui.SetTextColor(hdc, 0)
            colors = (0xadef22, 0xfeaefe, 0x329f3c, 0xef89ca, 0x9efacc)
            for i, k in enumerate(self.gl.winsInfo):
                pos = gl.winsInfo[k]['position']
                ws = gl.layouts[pos]
                style = ws['style']
                rc = ws['rect']
                self.drawer.fillRect(hdc, rc, colors[i % len(colors)])
                txt = f'{pos} \n horExpand={style["horExpand"]} \n verExpand={style["verExpand"]}'
                self.drawer.drawText(hdc, txt, rc)

            for k in self.gl.layouts:
                ly = self.gl.layouts[k]
                if ly and not ly['content']:
                    x, y = self.gl.getLeftTop(*k)
                    #self.drawer.fillRect(hdc, (x, y, x + 10, y + 10), 0x0000ff)

    rowtp = (50, '20%', '1fr', '2fr', 60, 50, 100)
    coltp = (100, 'auto', '30%', '10%', 60, '10%')
    gl = GridLayout(rowtp, coltp, (5, 10))
    gl.setContent(0, 0, None, style={})
    gl.setContent(0, 1, None, style={'horExpand' : 0})
    gl.setContent(0, 2, None, style={'horExpand' : 0})
    gl.setContent(0, 3, None, style={'horExpand' : 0})
    gl.setContent(0, 5, None, style={'horExpand' : 0})
    
    gl.setContent(2, 0, None, style={'verExpand' : -1})
    gl.setContent(1, 1, None, style={'horExpand' : -1, 'verExpand' : -1})
    gl.setContent(6, 1, None, style={'horExpand' : 1, 'priority': 30})
    gl.setContent(2, 3, None, style={'priority': 30})
    gl.setContent(3, 2, None, style={'priority': 30})
    gl.setContent(5, 4, None, style={'priority': 30})

    main = TestMain(gl)
    main.createWindow(None, (0, 0, 1002, 602), win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW)
    rc = win32gui.GetClientRect(main.hwnd)
    print(rc)
    gl.resize(*rc)
    win32gui.PumpMessages()


if __name__ == '__main__':
    testGridLayout()
