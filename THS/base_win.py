import win32gui, win32con , win32api, win32ui, win32gui_struct # pip install pywin32
import threading, time, datetime, sys, os, copy, calendar

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
        self.menu = {}
    
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
        if msg == win32con.WM_COMMAND:
            itemId = wParam & 0xffff
            menuWnd = self.menu.get('hwnd', None)
            if not menuWnd:
                return False
            if menuWnd: win32gui.DestroyMenu(menuWnd)
            callback = self.menu.get('callback', None)
            idx = itemId
            if callback: callback(self.menu['args'], idx, self.menu['model'][idx])
        if msg == win32con.WM_RBUTTONUP:
            mm = self.menu.get('model', None)
            if mm:
                pos = win32gui.GetCursorPos()
                self.popMenu(*pos)
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
    
    # model =[ {title: xx, } ]   title = 'LINE' is hor-split-line
    # callback = function(args, model-idx, model-item)
    def setPopupMenu(self, model, callback, args):
        self.menu['model'] = model
        self.menu['callback'] = callback
        self.menu['args'] = args

    def popMenu(self, x, y):
        model = self.menu.get('model', None)
        if not model:
            return
        pm = win32gui.CreatePopupMenu()
        self.menu['hwnd'] = pm
        for i, it in enumerate(model):
            if it['title'] == 'LINE':
                mi, exta = win32gui_struct.PackMENUITEMINFO(wID = i, fType = win32con.MF_SEPARATOR)
            else:
                mi, exta = win32gui_struct.PackMENUITEMINFO(text = it['title'], wID = i)
            win32gui.InsertMenuItem(pm, i, True, mi)
        win32gui.TrackPopupMenu(pm, win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON, x, y, 0, self.hwnd, None)

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

    def getFont(self, name = '宋体', fontSize = 14, weight = 0):
        key = f'{name}:{fontSize}'
        font = self.fonts.get(key, None)
        if not font:
            a = win32gui.LOGFONT()
            a.lfHeight = fontSize
            a.lfFaceName = name
            if weight > 0:
                a.lfWeight = weight
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

    def setVisible(self, visible):
        pass

    def setWinVisible(self, win, visible):
        if isinstance(win, BaseWindow):
            if visible:
                win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)
            else:
                win32gui.ShowWindow(win.hwnd, win32con.SW_HIDE)
        elif type(win) == int:
            # is HWND object
            if visible:
                win32gui.ShowWindow(win, win32con.SW_SHOW)
            else:
                win32gui.ShowWindow(win, win32con.SW_HIDE)
        elif isinstance(win, Layout):
            win.setVisible(visible)
        else:
            print('[Layout.setVisible] unsport win type: ', win)

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

    def setVisible(self, visible):
        for k in self.winsInfo:
            winInfo = self.winsInfo[k]
            win = winInfo['win']
            self.setWinVisible(win, visible)

class AbsLayout(Layout):
    def __init__(self) -> None:
        super().__init__()
        self.winsInfo = []

    # win = BaseWindow, HWND
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

    def setVisible(self, visible):
        for winInfo in self.winsInfo:
            win = winInfo['win']
            self.setWinVisible(win, visible)

class Cardayout(Layout):
    def __init__(self) -> None:
        super().__init__()
        self.winsInfo = []
        self.curVisibleIdx = -1

    def addContent(self, win):
        ws = {'win': win}
        self.winsInfo.append(ws)
        self.setWinVisible(win, False)
    
    def resize(self, x, y, width, height):
        super().resize(x, y, width, height)
        for it in self.winsInfo:
            self.adjustContentRect(it, x, y, width, height)

    def adjustContentRect(self, winInfo, x, y, width, height):
        win = winInfo['win']
        if isinstance(win, BaseWindow):
            win32gui.SetWindowPos(win.hwnd, None, x, y, width, height, win32con.SWP_NOZORDER)
        elif type(win) == int:
            win32gui.SetWindowPos(win, None, x, y, width, height, win32con.SWP_NOZORDER)
        elif isinstance(win, Layout):
            win.resize(x, y, width, height)
        else:
            print('[Cardayout.adjustContentRect] unsupport win type :', winInfo)

    def setVisible(self, visible):
        if not visible:
            for winInfo in self.winsInfo:
                win = winInfo['win']
                self.setWinVisible(win, False)
        else:
            self.showCardByIdx(self.curVisibleIdx)
    
    def showCardByIdx(self, idx):
        if not self.winsInfo:
            return
        if self.curVisibleIdx != idx and self.curVisibleIdx >= 0 and self.curVisibleIdx < len(self.winsInfo):
            win = self.winsInfo[self.curVisibleIdx]['win']
            self.setWinVisible(win, False)
        self.curVisibleIdx = idx
        win = self.winsInfo[idx]['win']
        self.setWinVisible(win, True)

    def showCard(self, win):
        for i, winInfo in enumerate(self.winsInfo):
            if win == winInfo['win']:
                self.showCardByIdx(i)
                break

class TableWindow(BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.style = {}
        self.rowHeight = 20
        self.headHeight = 24
        self.tailHeight = 0
        self.startIdx = 0
        self.selRow = -1
        self.data = None # a data array, [{colName1: xx, colName2: xxx}, ...]
        # headers : need set  [{title:xx, name:xxx, width: x }, ...]  
        # '#idx' is index row column  width: int-> fix width; -1: expand all less width; float( < 1.0 ) -> percent of headers width
        self.headers = None # must be set TODO

    def getHeaders(self):
        return self.headers

    def getValueAt(self, row, col, colName):
        if not self.data:
            return None
        if colName == '#idx':
            return row + 1
        if row < len(self.data):
            return self.data[row][colName]
        return None

    def getColumnWidth(self, colIdx, colName):
        w, h = self.getClientSize()
        return w // self.getColumnCount()
    
    def getColumnCount(self):
        if not self.headers:
            return 1
        return len(self.headers)

    def getPageSize(self):
        h = self.getClientSize()[1]
        h -= self.headHeight + self.tailHeight
        maxRowCount = (h + self.rowHeight - 1) // self.rowHeight
        return maxRowCount
    
    # [startIdx, end)
    def getVisibleRange(self):
        if not self.data:
            return (0, 0)
        num = len(self.data)
        maxRowCount = self.getPageSize()
        end = self.startIdx + maxRowCount
        end = min(end, num)
        return (self.startIdx, end)
    
    def setData(self, data):
        self.data = data
        self.startIdx = 0
        self.selRow = -1

    # delta > 0 : up scroll
    # delta < 0 : down scroll
    def scroll(self, delta):
        if delta >= 0:
            self.startIdx = max(self.startIdx - delta, 0)
            self.invalidWindow()
            return
        delta = -delta
        vr = self.getVisibleRange()
        psz = self.getPageSize()
        nn = vr[1] - vr[0]
        if nn <= psz // 2:
            return
        mx = nn - psz // 2
        delta = min(delta, mx)
        self.startIdx += delta
        self.invalidWindow()
    
    def showRow(self, row):
        rg = self.getVisibleRange()
        if not rg:
            return
        num = rg[1] - rg[0]
        if num == 0:
            return
        if row >= rg[0] and row < rg[1]:
            return # is visible
        if row < rg[0]:
            self.startIdx -= rg[0] - row
        elif row >= rg[1]:
            self.startIdx += row - rg[1] + 1
        self.invalidWindow()

    def onDraw(self, hdc):
        self.drawer.fillRect(hdc, (0, 0, *self.getClientSize()), 0x151313)
        if not self.getHeaders():
            return
        self.drawHeaders(hdc)
        if not self.data:
            return
        vr = self.getVisibleRange()
        if not vr:
            return
        w = self.getClientSize()[0]
        sy = self.headHeight
        for i in range(vr[1] - vr[0]):
            rc = (0, sy + i * self.rowHeight, w, sy + (i + 1) * self.rowHeight)
            self.drawRow(hdc, i, i + vr[0], rc)

    def drawHeaders(self, hdc):
        hds = self.getHeaders()
        if self.headHeight <= 0 or not hds:
            return
        w = self.getClientSize()[0]
        self.drawer.fillRect(hdc, (0, 0, w, self.headHeight), 0x191919)
        rc = [0, 0, 0, self.headHeight]
        for i, hd in enumerate(hds):
            rc[2] += self.getColumnWidth(i, hd['name'])
            self.drawer.drawRect2(hdc, rc, 0x888888)
            rc2 = rc.copy()
            rc2[1] = (self.headHeight - 14) // 2
            self.drawer.drawText(hdc, hd['title'], rc2)
            rc[0] = rc[2]
        
    def drawCell(self, hdc, row, col, colName, value, rect):
        self.drawer.drawText(hdc, str(value), rect, 0xffffff, align=win32con.DT_LEFT)

    def drawRow(self, hdc, showIdx, row, rect):
        rc = [0, rect[1], 0, rect[3]]
        hds = self.getHeaders()
        if not hds:
            return
        if row == self.selRow:
            self.drawer.fillRect(hdc, rect, 0x393533)
        for i in range(len(hds)):
            colName = hds[i]['name']
            rc[2] += self.getColumnWidth(i, colName)
            val = self.getValueAt(row, i, colName)
            self.drawCell(hdc, row, i, colName, val, rc)
            rc[0] = rc[2]

    def drawTail(self, hdc, rect):
        if self.tailHeight <= 0:
            return

    def onClick(self, x, y):
        win32gui.SetFocus(self.hwnd)
        if y > self.headHeight and y < self.getClientSize()[1] - self.tailHeight:
            y -= self.headHeight
            self.selRow = y // self.rowHeight + self.startIdx
            win32gui.InvalidateRect(self.hwnd, None, True)

    def onMouseWheel(self, delta):
        if not self.data:
            return
        if delta & 0x8000:
            delta = delta - 0xffff - 1
        delta = delta // 120
        self.scroll(delta * 5)
        win32gui.InvalidateRect(self.hwnd, None, True)

    def onKeyDown(self, key):
        if not self.data:
            return False
        if key == win32con.VK_DOWN:
            if self.selRow < len(self.data) - 1:
                self.selRow += 1
                self.showRow(self.selRow)
                self.invalidWindow()
            return True
        elif key == win32con.VK_UP:
            if self.selRow > 0:
                self.selRow -= 1
                self.showRow(self.selRow)
                self.invalidWindow()
            return True
        elif key == win32con.VK_RETURN:
            if self.selRow >= 0 and self.data:
                self.notifyListener('RowEnter', {'src': self, 'selRow' : self.selRow, 'data': self.data[self.selRow]})
            return True
        return False

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDOWN:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.onClick(x, y)
            return True
        if msg == win32con.WM_MOUSEWHEEL:
            self.onMouseWheel((wParam >> 16) & 0xffff)
            return True
        if msg == win32con.WM_KEYDOWN:
            tg = self.onKeyDown(wParam)
            return tg
        return super().winProc(hwnd, msg, wParam, lParam)

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

class GroupButton(BaseWindow):
    def __init__(self, groups) -> None:
        super().__init__()
        self.groups = groups
        self.selGroupIdx = -1
    
    # group = int, is group idx or group object
    def setSelGroup(self, group):
        if type(group) == int:
            self.selGroupIdx = group
        win32gui.InvalidateRect(self.hwnd, None, True)

    def onDraw(self, hdc):
        w, h = self.getClientSize()
        cw = w / len(self.groups)
        for i in range(len(self.groups)):
            item = self.groups[i]
            color = 0x00008C if i == self.selGroupIdx else 0x333333
            rc = [int(cw * i), 0,  int((i + 1) * cw), h]
            self.drawer.fillRect(hdc, rc, color)
            self.drawer.drawRect(hdc, rc, self.drawer.getPen(0x202020))
            rc[1] = (h - 16) // 2
            self.drawer.drawText(hdc, item['title'], rc, 0x2fffff)

    def onClick(self, x, y):
        w, h = self.getClientSize()
        cw = w / len(self.groups)
        idx = int(x / cw)
        if self.selGroupIdx == idx:
            return
        self.selGroupIdx = idx
        self.notifyListener('click', {'group': self.groups[idx], 'groupIdx': idx})
        win32gui.InvalidateRect(self.hwnd, None, True)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.onClick(x, y)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)        

class Button(BaseWindow):
    # btnInfo = {name: xxx, title: xxx}
    def __init__(self, btnInfo) -> None:
        super().__init__()
        self.info = btnInfo
    
    def onDraw(self, hdc):
        w, h = self.getClientSize()
        TH = 14
        rc = (0, 0,  w, h)
        self.drawer.fillRect(hdc, rc, 0x333333)
        self.drawer.drawRect2(hdc, rc, 0x202020)
        rc = (0, (h - TH) // 2,  w, h - (h - TH) // 2)
        self.drawer.drawText(hdc, self.info['title'], rc, 0x2fffff)

    def onClick(self, x, y):
        self.notifyListener('click', self.info)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.onClick(x, y)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class DatePopupWindow(BaseWindow):
    TOP_HEADER_HEIGHT = 40
    PADDING = 10

    def __init__(self) -> None:
        super().__init__()
        self.preBtnRect = None
        self.nextBtnRect = None
        self.curSelDay = None # datetime.date object
        self.ownerHwnd = None
        self.setSelDay(None)

    def createWindow(self, parentWnd, rect = None, style = win32con.WS_POPUP | win32con.WS_CHILD, className='STATIC', title=''):
        style = win32con.WS_POPUP | win32con.WS_CHILD
        self.ownerHwnd = parentWnd
        W, H = 250, 240
        super().createWindow(parentWnd, (0, 0, W, H), style, className, title)
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        BTN_W, BTN_H = 20, 20
        self.nextBtnRect = (W - BTN_W - 5, 10, W - 5, 30)
        self.preBtnRect = (W - BTN_W * 2 - 15, 10, W - BTN_W - 15, 30)

    def show(self, x = None, y = None):
        self.setSelDay(self.curSelDay)
        ownerRect = win32gui.GetWindowRect(self.ownerHwnd)
        if x == None:
            x = ownerRect[0]
        if y == None:
            y = ownerRect[3]
        win32gui.SetWindowPos(self.hwnd, 0, x, y, 0, 0, win32con.SWP_NOZORDER | win32con.SWP_NOSIZE)
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.SetActiveWindow(self.hwnd)

    def hide(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)

    def onDraw(self, hdc):
        self.drawHeader(hdc, self.curYear, self.curMonth)
        self.drawContent(hdc, self.curYear, self.curMonth)

    def drawHeader(self, hdc, year, month):
        title = f'{year}年{month}月'
        self.drawer.drawText(hdc, title, (0, 10, 100, self.TOP_HEADER_HEIGHT), 0xcccccc)
        #self.drawer.drawRect2(hdc, self.nextBtnRect, 0x444444)
        #self.drawer.drawRect2(hdc, self.preBtnRect, 0x444444)
        self.drawer.drawText(hdc, '<<', self.preBtnRect, 0xcccccc)
        self.drawer.drawText(hdc, '>>', self.nextBtnRect, 0xcccccc)

    def drawContent(self, hdc, year, month):
        days = self.calcDays(year, month)
        sy = self.TOP_HEADER_HEIGHT
        w, h = self.getClientSize()
        ITEM_WIDTH = (w - self.PADDING * 2) / 7
        ITEM_HEIGHT = (h - self.TOP_HEADER_HEIGHT - self.PADDING) / ((len(days) + 6) // 7 + 1)
        XQ = ['一', '二', '三', '四', '五', '六' ,'日']
        XQ.extend(days)
        days = XQ
        DPY = (ITEM_HEIGHT - 14) // 2
        sy = self.TOP_HEADER_HEIGHT
        for i, day in enumerate(days):
            if i > 0 and i % 7 == 0:
                sy += ITEM_HEIGHT
            c = i % 7
            if not day:
                continue
            rc = [self.PADDING + int(c * ITEM_WIDTH), int(sy), self.PADDING + int(c * ITEM_WIDTH + ITEM_WIDTH), int(sy + ITEM_HEIGHT)]
            if self.curSelDay == day:
                self.drawer.drawRect2(hdc, rc, 0x00aa00)
            rc[1] += int(DPY)
            txt = day if type(day) == str else str(day.day)
            self.drawer.drawText(hdc, txt, rc, 0xcccccc)
            
    def calcDays(self, year, month):
        weeky, num = calendar.monthrange(year, month)
        days = []
        for i in range(0, weeky):
            days.append(None)
        for i in range(0, num):
            d = datetime.date(year, month, i + 1)
            days.append(d)
        return days

    def nextMonth(self):
        m = self.curMonth + 1
        if m == 13:
            self.curMonth = 1
            self.curYear += 1
        else:
            self.curMonth = m
        self.invalidWindow()

    def prevMonth(self):
        m = self.curMonth - 1
        if m == 0:
            self.curMonth = 12
            self.curYear -= 1
        else:
            self.curMonth = m
        self.invalidWindow()

    def getDayOf(self, x, y):
        w, h = self.getClientSize()
        if x < self.PADDING or x > w - self.PADDING or y < self.TOP_HEADER_HEIGHT or y >= h - self.PADDING:
            return None
        days = self.calcDays(self.curYear, self.curMonth)
        ITEM_WIDTH = int((w - self.PADDING * 2) / 7)
        ITEM_HEIGHT = int((h - self.TOP_HEADER_HEIGHT - self.PADDING) / ((len(days) + 6) // 7 + 1))
        if y <= self.TOP_HEADER_HEIGHT + ITEM_HEIGHT:
            return None # in XQ title
        x -= self.PADDING
        y -= self.TOP_HEADER_HEIGHT + ITEM_HEIGHT
        r = y // ITEM_HEIGHT
        c = x // ITEM_WIDTH
        idx = r * 7 + c
        if idx >=0 and idx < len(days):
            return days[idx]
        return None

    # day = int | datetime.date | str
    def setSelDay(self, day):
        if not day:
            day = datetime.date.today()
            self.curSelDay = None
            self.curYear = day.year
            self.curMonth = day.month
            return
        if type(day) == datetime.date:
            self.curSelDay = day
        elif type(day) == int:
            self.curSelDay = datetime.date(day // 10000, day // 100 % 100, day % 100)
        elif type(day) == str:
            day = int(day.replace('-', ''))
            self.curSelDay = datetime.date(day // 10000, day // 100 % 100, day % 100)
        self.curYear = self.curSelDay.year
        self.curMonth = self.curSelDay.month

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_ACTIVATE:
            ac = wParam & 0xffff
            if ac == win32con.WA_INACTIVE:
                self.hide()
            return True
        if msg == win32con.WM_LBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            if x >= self.preBtnRect[0] and x < self.preBtnRect[2] and y >= self.preBtnRect[1] and y < self.preBtnRect[3]:
                self.prevMonth()
            elif x >= self.nextBtnRect[0] and x < self.nextBtnRect[2] and y >= self.nextBtnRect[1] and y < self.nextBtnRect[3]:
                self.nextMonth()
            else:
                day = self.getDayOf(x, y)
                if day:
                    self.setSelDay(day)
                    self.hide()
                    sdd = self.curSelDay.year * 10000 + self.curSelDay.month * 100 + self.curSelDay.day
                    self.notifyListener('DatePopupWindow.selDayChanged', {'curSelDay': sdd})
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class DatePicker(BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.popWin = DatePopupWindow()
        self.popWin.addListener('DatePopupWindow', self.onSelDayChanged)

    def setSelDay(self, selDay):
        self.popWin.setSelDay(selDay)
        self.invalidWindow()
    
    def getSelDay(self):
        day = self.popWin.curSelDay
        if not day:
            return None
        return f'{day.year}-{day.month :02d}-{day.day :02d}'

    def onSelDayChanged(self, target, evtName, evtInfo):
        self.invalidWindow()
        self.notifyListener(evtName, evtInfo)

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.popWin.createWindow(self.hwnd)

    def onDraw(self, hdc):
        w, h = self.getClientSize()
        self.drawer.drawRect2(hdc, (0, 0, w, h), 0xcccccc)
        if not self.getSelDay():
            return
        sy = (h - 2 - 14) // 2
        self.drawer.drawText(hdc, self.getSelDay(), (0, sy, w - 1, h), 0xcccccc)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            if win32gui.IsWindowVisible(self.popWin.hwnd):
                self.popWin.hide()
            else:
                self.popWin.show()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

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
