import win32gui, win32con , win32api, win32ui, win32gui_struct # pip install pywin32
import threading, time, datetime, sys, os, copy, calendar, functools

# listeners : ContextMenu = {x, y} , default is diable
#             DbClick = {x, y} , default is diable
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
        self.css = {'fontSize' : 14, 'bgColor': 0x000000, 'textColor': 0xffffff} # config css style
        self.enableListeners = {'ContextMenu': False, 'DbClick': False}
    
    # func = function(evtName, evtInfo, args)
    def addListener(self, func, args = None):
        self.listeners.append((func, args))

    def notifyListener(self, evtName, evtInfo):
        for ls in self.listeners:
            func, args = ls
            func(evtName, evtInfo, args)

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
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            if not (style & win32con.WS_POPUP) and not (style & win32con.WS_CHILD) and not win32gui.GetParent(self.hwnd):
                win32gui.PostQuitMessage(0)
                return True
            del BaseWindow.bindHwnds[hwnd]
        if msg == win32con.WM_RBUTTONUP and self.enableListeners['ContextMenu']:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.notifyListener('ContextMenu', {'x': x, 'y': y})
            return True
        if msg == win32con.WM_LBUTTONDBLCLK and self.enableListeners['DbClick']:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.notifyListener('DbClick', {'x': x, 'y': y})
            return True
        return False

    def _draw(self):
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
        self.drawer.fillRect(mdc, win32gui.GetClientRect(self.hwnd), self.css['bgColor'])
        win32gui.SetBkMode(mdc, win32con.TRANSPARENT)
        win32gui.SetTextColor(mdc, self.css['textColor'])
        self.drawer.use(mdc, self.drawer.getFont(fontSize = self.css['fontSize']))
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
        self = BaseWindow.bindHwnds.get(hwnd, None)
        if not self:
            return win32gui.DefWindowProc(hwnd, msg, wParam, lParam)
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
        self.started = False
        self.event = threading.Event()
        self.thread = threading.Thread(target = Thread._run, args=(self,))

    def addTask(self, taskId, fun, args = None):
        for tk in self.tasks:
            if tk[2] == taskId:
                return
        self.tasks.append((fun, args, taskId))
        self.event.set()

    def start(self):
        if not self.started:
            self.started = True
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
                if args != None:
                    fun(*args)
                else:
                    fun()
                self.tasks.pop(0)

class TimerThread:
    def __init__(self) -> None:
        self.tasks = []
        self.stoped = False
        self.started = False
        self.thread = threading.Thread(target = Thread._run, args=(self,))

    def addTask(self, delaySeconds, fun, *args):
        self.tasks.append((fun, args, time.time() + delaySeconds))

    def start(self):
        if not self.started:
            self.started = True
            self.thread.start()

    def stop(self):
        self.stoped = True
    
    def runOnce(self):
        idx = 0
        while idx < len(self.tasks):
            task = self.tasks[idx]
            fun, args, _time,  *_ = task
            if time.time() < _time:
                idx += 1
                continue
            self.tasks.pop(idx)
            fun(*args)
    
    @staticmethod
    def _run(self):
        while not self.stoped:
            time.sleep(0.5)
            self.runOnce()

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

    def drawCycle(self, hdc, rect, penColor, penWidth):
        if not rect:
            return
        pen = self.getPen(penColor, win32con.PS_SOLID, penWidth)
        self.use(hdc, pen)
        self.use(hdc, win32gui.GetStockObject(win32con.NULL_BRUSH))
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

    def setTemplates(self, templateRows, templateColumns):
        self.templateRows = templateRows
        self.templateColumns = templateColumns
    
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

# listeners : DbClick = {x, y, row, data(row data), model(all data)}
#             RowEnter = {row, data, model}
class TableWindow(BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0xf0f0f0
        self.css['textColor'] = 0x333333
        self.css['headerBgColor'] = 0xc3c3c3
        self.css['cellBorder'] = 0xc0c0c0
        self.css['selBgColor'] = 0xf0a0a0
        self.enableListeners['DbClick'] = True
        self.rowHeight = 20
        self.headHeight = 24
        self.tailHeight = 0
        self.startIdx = 0
        self.selRow = -1
        self.sortHeader = {'header': None, 'state': None} # state: 'ASC' | 'DSC' |  None
        self.sortData = None

        self.data = None # a data array, [{colName1: xx, colName2: xxx}, ...]

        # headers : need set a list , items of
        #    { name:xxx,   '#idx' is index row column 
        #      title:xx,  
        #      sortable:True | False (default is False),
        #      width : int, fix width
        #      stretch: int, how stretch less width, is part of all stretchs
        #      formater: function(colName, val, rowData) -> return format str data
        #      sorter: function(colName, val, rowData, allDatas, asc:True|False)  -> return sorted value
        #      textAlign: int, win32con.DT_LEFT(is default) | .....
        self.headers = None # must be set TODO

    def getHeaders(self):
        return self.headers

    def getValueAt(self, row, col, colName):
        if not self.data:
            return None
        if colName == '#idx':
            return row + 1
        if row >= 0 and row < len(self.data):
            if self.sortData:
                return self.sortData[row].get(colName, None)
            return self.data[row].get(colName, None)
        return None

    def getColumnWidth(self, colIdx, colName):
        BASE_WIDTH = 40
        w, h = self.getClientSize()
        hd = self.headers[colIdx]
        cw = int(hd.get('width', -1))
        if cw < 0:
            return BASE_WIDTH
        stretch = int(hd.get('stretch', 0))
        if stretch <= 0:
            return cw

        fixWidth = 0
        frs = 0
        for hd in self.headers:
            cw = int(hd.get('width', -1))
            if cw < 0:
                fixWidth += BASE_WIDTH
            else:
                fixWidth += cw
            frs += int(hd.get('stretch', 0))
        lessWidth = w - fixWidth
        if lessWidth <= 0 or frs <= 0:
            return cw
        return cw + int(lessWidth * stretch / frs)
    
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
        if self.data == data:
            return
        self.data = data
        self.sortData = None
        for k in self.sortHeader:
            self.sortHeader[k] = None
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
        if not self.headers:
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

    def drawSort(self, hdc, rc):
        if not self.sortHeader:
            return
        hd = self.sortHeader['header']
        state = self.sortHeader['state']
        if not hd or not state:
            return
        WH = 6
        sx = rc[2] - 10
        sy = (rc[3] - rc[1] - WH) // 2
        if state == 'ASC':
            pts = [(sx + WH // 2, sy), (sx, sy + WH), (sx + WH, sy + WH)]
        else:
            pts = [(sx, sy), (sx + WH, sy), (sx + WH // 2, sy + WH)]
        hbr = win32gui.CreateSolidBrush(0xff007f)
        win32gui.SelectObject(hdc, hbr)
        win32gui.Polygon(hdc, pts)
        win32gui.DeleteObject(hbr)

    def drawHeaders(self, hdc):
        hds = self.getHeaders()
        if self.headHeight <= 0 or not hds:
            return
        w = self.getClientSize()[0]
        self.drawer.fillRect(hdc, (0, 0, w, self.headHeight), self.css['headerBgColor'])
        rc = [0, 0, 0, self.headHeight]
        for i, hd in enumerate(hds):
            rc[2] += self.getColumnWidth(i, hd['name'])
            self.drawer.drawRect2(hdc, rc, 0x888888)
            if self.sortHeader and self.sortHeader['header'] == hd:
                self.drawSort(hdc, rc)
            rc2 = rc.copy()
            rc2[1] = (self.headHeight - 14) // 2
            self.drawer.drawText(hdc, hd['title'], rc2)
            rc[0] = rc[2]
        
    def drawCell(self, hdc, row, col, colName, value, rect):
        hd = self.headers[col]
        formater = hd.get('formater', None)
        if formater:
            value = formater(colName, value, self.data[row])
        if value == None or value == '':
            return
        align = hd.get('textAlign', win32con.DT_LEFT)
        self.drawer.drawText(hdc, str(value), rect, self.css['textColor'], align = align)

    def drawRow(self, hdc, showIdx, row, rect):
        rc = [0, rect[1], 0, rect[3]]
        self.drawer.drawLine(hdc, rect[0], rect[3], rect[2], rect[3], self.css['cellBorder'])
        hds = self.headers
        if row == self.selRow:
            self.drawer.fillRect(hdc, rect, self.css['selBgColor'])
        for i in range(len(hds)):
            colName = hds[i]['name']
            rc[2] += self.getColumnWidth(i, colName)
            val = self.getValueAt(row, i, colName)
            self.drawCell(hdc, row, i, colName, val, rc)
            rc[0] = rc[2]

    def drawTail(self, hdc, rect):
        if self.tailHeight <= 0:
            return

    def getHeaderAtX(self, x):
        if not self.headers or x < 0:
            return None
        for i, hd in enumerate(self.headers):
            iw = self.getColumnWidth(i, hd['name'])
            if x <= iw:
                return hd
            x -= iw
        return None

    def setSortHeader(self, header):
        hd = self.sortHeader['header']
        st = self.sortHeader['state']
        if not header:
            self.sortHeader['header'] = None
            self.sortHeader['state'] = None
            self.sortData = None
            return
        if hd == header:
            a = ('ASC', 'DSC', None)
            idx = (a.index(st) + 1) % len(a)
            self.sortHeader['state'] = a[idx]
        else:
            self.sortHeader['header'] = header
            self.sortHeader['state'] = 'ASC'
        st = self.sortHeader['state']
        if st == None:
            self.sortData = None
            return
        reverse = st == 'DSC'
        if self.data:
            if 'sorter' in header:
                def keyn(rowData):
                    hdn = header['name']
                    return header['sorter'](hdn, rowData[hdn], rowData, self.data, st == 'ASC')
                self.sortData = sorted(self.data, key = keyn, reverse = reverse)
            else:
                self.sortData = sorted(self.data, key = lambda d: d[header['name']], reverse = reverse)
        else:
            self.sortData = None

    # get row idx, -2: in header, -3: in tail, -1: in empty rows
    def getRowIdx(self, y):
        if not self.data:
            return -1
        if y <= self.headHeight:
            return -2
        if y >= self.getClientSize()[1] - self.tailHeight:
            return -3
        y -= self.headHeight
        row = y // self.rowHeight + self.startIdx
        if row >= 0 and row < len(self.data):
            return row
        return -1

    def onClick(self, x, y):
        win32gui.SetFocus(self.hwnd)
        row = self.getRowIdx(y)
        if row == -2: # click headers
            hd = self.getHeaderAtX(x)
            if hd:
               self.setSortHeader(hd)
               self.invalidWindow()
        elif row >= 0:
            self.selRow = row
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
                dx = self.sortData if self.sortData else self.data
                self.notifyListener('RowEnter', {'row' : self.selRow, 'data': dx[self.selRow], 'model': dx})
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
        if msg == win32con.WM_LBUTTONDBLCLK and self.enableListeners['DbClick']:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            row = self.getRowIdx(y)
            if row >= 0:
                dx = self.sortData if self.sortData else self.data
                self.notifyListener('DbClick', {'x': x, 'y': y, 'row': row, 'data': dx[row], 'model': dx})
            return True
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

# listeners : Select = {selIdx}
class ListWindow(BaseWindow):
    def __init__(self, hwnd):
        super().__init__(hwnd)
        self.ROW_HEIGHT = 18
        self.selIdx = -1
        self.pageIdx = 0
        self.data = None

    def setData(self, data):
        self.data = data
        self.selIdx = -1
        self.pageIdx = 0

    def getPageSize(self):
        rect = win32gui.GetClientRect(self.hwnd)
        h = rect[3] - rect[1]
        return h // self.ROW_HEIGHT

    def getPageNum(self):
        if not self.data:
            return 0
        return (len(self.data) + self.getPageSize() - 1) // self.getPageSize()

    def getItemRect(self, idx):
        pz = self.getPageSize()
        idx -= self.pageIdx * pz
        if idx < 0 or idx >= pz:
            return None
        sy = idx * self.ROW_HEIGHT
        ey = sy + self.ROW_HEIGHT
        return (0, sy, self.getClientSize()[0], ey)

    def getItemIdx(self, y):
        idx = y // self.ROW_HEIGHT
        idx += self.getPageSize() * self.pageIdx
        return idx

    def getVisibleRange(self):
        pz = self.getPageSize()
        start = pz * self.pageIdx
        end = (self.pageIdx + 1) * pz
        start = min(start, len(self.data) - 1)
        end = min(end, len(self.data) - 1)
        return start, end
    
    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_MOUSEWHEEL:
            wParam = (wParam >> 16) & 0xffff
            if wParam & 0x8000:
                wParam = wParam - 0xffff + 1
            wParam = wParam // 120
            if wParam > 0: # up
                self.pageIdx = max(self.pageIdx - wParam, 0)
            else:
                self.pageIdx = min(self.pageIdx + wParam, self.getPageNum() - 1)
            win32gui.InvalidateRect(self.hwnd, None, True)
            return True
        if msg == win32con.WM_LBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            idx = self.getItemIdx(y)
            if self.selIdx != idx:
                self.selIdx = idx
                win32gui.InvalidateRect(self.hwnd, None, True)
                self.notifyListener('Select', {'selIdx': idx})
            return True
        if msg == win32con.WM_KEYDOWN:
            if wParam == win32con.VK_DOWN:
                if self.data and self.selIdx < len(self.data):
                    self.selIdx += 1
                    if self.selIdx > 0 and self.selIdx % self.getPageSize() == 0:
                        self.pageIdx += 1
                    win32gui.InvalidateRect(hwnd, None, True)
            elif wParam == win32con.VK_UP:
                if self.data and self.selIdx > 0:
                    self.selIdx -= 1
                    if self.selIdx > 0 and (self.selIdx + 1) % self.getPageSize() == 0:
                        self.pageIdx -= 1
                    win32gui.InvalidateRect(hwnd, None, True)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

# listeners : ClickSelect = {group, groupIdx}
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
        self.notifyListener('ClickSelect', {'group': self.groups[idx], 'groupIdx': idx})
        win32gui.InvalidateRect(self.hwnd, None, True)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.onClick(x, y)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)        

# listeners : Click = {info}
class Button(BaseWindow):
    # btnInfo = {name: xxx, title: xxx}
    def __init__(self, btnInfo) -> None:
        super().__init__()
        self.css['bgColor'] = 0x333333
        self.css['borderColor'] = 0x202020
        self.css['textColor'] = 0x2fffff
        self.info = btnInfo
    
    def onDraw(self, hdc):
        w, h = self.getClientSize()
        TH = 14
        rc = (0, 0,  w, h)
        self.drawer.fillRect(hdc, rc, self.css['bgColor'])
        self.drawer.drawRect2(hdc, rc, self.css['borderColor'])
        rc = (0, (h - TH) // 2,  w, h - (h - TH) // 2)
        self.drawer.drawText(hdc, self.info['title'], rc, self.css['textColor'])

    def onClick(self, x, y):
        self.notifyListener('Click', self.info)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.onClick(x, y)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class Label(BaseWindow):
    def __init__(self, text = None) -> None:
        super().__init__()
        self.css['borderColor'] = self.css['bgColor']
        self.text = text
    
    def setText(self, text):
        if text == None:
            self.text = ''
        elif isinstance(text, str):
            self.text = text
        else:
            self.text = str(text)
        self.invalidWindow()
    
    def onDraw(self, hdc):
        w, h = self.getClientSize()
        TH = 14
        rc = (0, 0,  w, h)
        self.drawer.fillRect(hdc, rc, self.css['bgColor'])
        self.drawer.drawRect2(hdc, rc, self.css['borderColor'])
        rc = (0, (h - TH) // 2,  w, h - (h - TH) // 2)
        self.drawer.drawText(hdc, self.text, rc, self.css['textColor'], win32con.DT_LEFT | win32con.DT_SINGLELINE | win32con.DT_VCENTER)

# listeners : Checked = {info}
class CheckBox(BaseWindow):
    _groups = {}

    # info = {name: xx, value:xx, title:'', checked: True|False }
    def __init__(self, info : dict) -> None:
        super().__init__()
        self.info = info
        name = info.get('name', None)
        if not name:
            return
        ls = CheckBox._groups.get(name, None)
        if not ls:
            ls = CheckBox._groups[name] = []
        ls.append(self)

    def onDraw(self, hdc):
        w, h = self.getClientSize()
        R = 14
        RR = 8
        sy = (h - R) // 2
        rc = (0, sy, R, sy + R)
        self.drawer.drawCycle(hdc, rc, 0x606060, 2)
        
        if self.isChecked():
            sy = (h - RR) // 2
            sx = (R - RR) // 2
            rc2 = (sx, sy, sx + RR, sy + RR)
            self.drawer.fillCycle(hdc, rc2, 0x338833)
        if 'title' in self.info:
            rc3 = (rc[2] + 3, (h - 14) // 2, w, h)
            self.drawer.drawText(hdc, self.info['title'], rc3, 0x2fffff, win32con.DT_LEFT)

    def isChecked(self):
        return self.info and self.info.get('checked', False)

    def setChecked(self, checked : bool):
        if self.isChecked() == checked:
            return
        if checked:
            name = self.info.get('name', None)
            self.uncheckedGroup(name)
        self.info['checked'] = checked
        self.invalidWindow()
        self.notifyListener('Checked', self.info)

    def uncheckedGroup(self, name):
        if not name:
            return
        ls = CheckBox._groups[name]
        for c in ls:
            if c != self:
                c.setChecked(False)

    def _destroy(self):
        if not self.info:
            return
        name = self.info.get('name', None)
        if not name:
            return
        ls = CheckBox._groups.get(name, None)
        if not ls:
            return
        ls.remove(self)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            self.setChecked(not self.isChecked())
            return True
        if msg == win32con.WM_DESTROY:
            self._destroy() # no return any
        return super().winProc(hwnd, msg, wParam, lParam)

class PopupWindow(BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ownerHwnd = None

    def createWindow(self, parentWnd, rect, style = win32con.WS_POPUP | win32con.WS_CHILD, className='STATIC', title=''):
        #style = win32con.WS_POPUP | win32con.WS_CHILD
        self.ownerHwnd = parentWnd
        super().createWindow(parentWnd, rect, style, className, title)
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

    def updateOwner(self, ownerHwnd):
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_HWNDPARENT, ownerHwnd)

    # x, y is screen pos
    def show(self, x = None, y = None):
        if self.ownerHwnd:
            ownerRect = win32gui.GetWindowRect(self.ownerHwnd)
        else:
            ownerRect = (0, 0, 0, 0)
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
        self.drawer.drawRect2(hdc, (0, 0, *self.getClientSize()), 0xAAAAAA)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_ACTIVATE:
            ac = wParam & 0xffff
            if ac == win32con.WA_INACTIVE:
                self.hide()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

# listeners : Select = model[idx]
class PopupMenu(PopupWindow):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0xf0f0f0
        self.css['selBgColor'] = 0xdfd0d0
        self.css['textColor'] = 0x222222
        self.css['disableTextColor'] = 0x909090
        self.LEFT_RIGHT_PADDING = 20
        self.SEPRATOR_HEIGHT = 2
        self.ARROW_HEIGHT = 10
        self.VISIBLE_MAX_ITEM = 20 # 最大显示的个数
        self.model = None  # [{title:xx, name:xx }, ...]   title = LINE 表示分隔线
        self.rowHeight = 24
        self.selIdx = -1
        self.startIdx = 0 # 开始显示的idx

    def setModel(self, model):
        self.model = model

    def show(self, x = None, y = None):
        if not self.hwnd:
            return
        self.selIdx = -1
        w, h = self.calcSize()
        win32gui.SetWindowPos(self.hwnd, 0, 0, 0, w, h, win32con.SWP_NOZORDER | win32con.SWP_NOMOVE)
        super().show(x, y)
    
    def calcSize(self):
        w, h = 0, 0
        if not self.model:
            return (100, self.rowHeight)
        hdc = win32gui.GetDC(self.hwnd)
        self.drawer.use(hdc, self.drawer.getFont())
        # calc max height
        for i in range(self.startIdx, min(self.startIdx + self.VISIBLE_MAX_ITEM, len(self.model))):
            m = self.model[i]
            title = m.get('title', '')
            h += self.SEPRATOR_HEIGHT if title == 'LINE' else self.rowHeight
        # calc max width
        for i in range(0, len(self.model)):
            m = self.model[i]
            title = m.get('title', '')
            sz = win32gui.GetTextExtentPoint32(hdc, title)
            w = max(w, sz[0])
        w += self.LEFT_RIGHT_PADDING * 2
        win32gui.ReleaseDC(self.hwnd, hdc)
        if len(self.model) > self.VISIBLE_MAX_ITEM:
            h += self.ARROW_HEIGHT * 2
        return (w, h)
    
    def getItemIdxAt(self, y):
        if not self.model:
            return -1
        sy = 0
        for i in range(self.startIdx, min(self.startIdx + self.VISIBLE_MAX_ITEM, len(self.model))):
            m = self.model[i]
            title = m.get('title', '')
            ih = self.SEPRATOR_HEIGHT if title == 'LINE' else self.rowHeight
            if y >= sy and y < sy + ih:
                return i
            sy += ih
        return -1

    def scroll(self, delta):
        if not self.model:
            return
        idx = self.startIdx - delta
        if delta < 0:
            maxIdx = len(self.model) - self.VISIBLE_MAX_ITEM
            idx = min(idx, maxIdx)
        else:
            idx = max(idx, 0)
        if self.startIdx == idx:
                return
        self.startIdx = idx
        w, h = self.calcSize()
        win32gui.SetWindowPos(self.hwnd, 0, 0, 0, w, h, win32con.SWP_NOZORDER | win32con.SWP_NOMOVE)
        self.invalidWindow()

    def drawArrow(self, hdc):
        if not self.model:
            return
        w, h = self.getClientSize()
        cx = w // 2
        AW, AH = 4, 4
        self.drawer.use(hdc, self.drawer.getBrush(0x333333))
        self.drawer.use(hdc, win32gui.GetStockObject(win32con.NULL_PEN))
        if self.startIdx > 0:
            sy = 2
            pts = [(cx, sy), (cx + AW, AH + sy), (cx - AW, AH + sy)]
            win32gui.Polygon(hdc, pts)
        if len(self.model) > self.startIdx + self.VISIBLE_MAX_ITEM:
            sy = h - AH - 3
            pts = [(cx, sy + AH), (cx + AW, sy), (cx - AW, sy)]
            win32gui.Polygon(hdc, pts)

    def onDraw(self, hdc):
        super().onDraw(hdc)
        if not self.model:
            return
        self.drawArrow(hdc)
        w = self.getClientSize()[0]
        sy = 0 if len(self.model) <= self.VISIBLE_MAX_ITEM else self.ARROW_HEIGHT
        rc = [self.LEFT_RIGHT_PADDING, sy, w - self.LEFT_RIGHT_PADDING, sy]
        for i in range(self.startIdx, min(self.startIdx + self.VISIBLE_MAX_ITEM, len(self.model))):
            m = self.model[i]
            title = m.get('title', '')
            ih = self.SEPRATOR_HEIGHT if title == 'LINE' else self.rowHeight
            rc[3] += ih
            if i == self.selIdx and title != 'LINE':
                rcs = [0, rc[1], w, rc[3]]
                self.drawer.fillRect(hdc, rcs, self.css['selBgColor'])
            if title == 'LINE':
                self.drawer.drawLine(hdc, rc[0], rc[1], rc[2], rc[1], 0x999999, width = 1)
            else:
                color = self.css['textColor'] if m.get('enable', True) else self.css['disableTextColor']
                bk = rc[1]
                rc[1] += (self.rowHeight - 14) // 2
                self.drawer.drawText(hdc, title, rc, color, win32con.DT_LEFT)
                rc[1] = bk
            rc[1] = rc[3]

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_MOUSEMOVE:
            y = (lParam >> 16) & 0xffff
            idx = self.getItemIdxAt(y)
            if self.selIdx != idx and idx >= 0 and self.model[idx].get('title', '') != 'LINE':
                self.selIdx = idx
                self.invalidWindow()
            return True
        if msg == win32con.WM_LBUTTONUP:
            y = (lParam >> 16) & 0xffff
            idx = self.getItemIdxAt(y)
            self.hide()
            if idx >= 0 and self.model[idx].get('title', '') != 'LINE' and self.model[idx].get('enable', True):
                self.notifyListener('Select', self.model[idx])
            return True
        if msg == win32con.WM_MOUSEWHEEL:
            delta = (wParam >> 16) & 0xffff
            if delta & 0x8000:
                delta = delta - 0xffff - 1
            delta = delta // 120
            self.scroll(delta)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class PopupMenuHelper:
    # x, y is screen position
    # model = [{'title': xx, 'enable' : True(is default) | False}, ...]  title:必选项 = LINE | ...., enable: 可选项
    # listener = function(args, evtName, evtInfo)
    # args = listener args. Auto add menu object to args ==> listener-function([args, menu], evtName, evtInfo)
    # return PopupMenu object
    @staticmethod
    def create(parentHwnd, model, listener, args = None):
        menu = PopupMenu()
        menu.createWindow(parentHwnd, (0, 0, 1, 1), title = 'I-PopupMenu')
        menu.setModel(model)
        menu.addListener(listener, (args, menu))
        return menu

# listeners :  Select = {day: int}
class DatePopupWindow(PopupWindow):
    TOP_HEADER_HEIGHT = 40
    PADDING = 10

    def __init__(self) -> None:
        super().__init__()
        self.preBtnRect = None
        self.nextBtnRect = None
        self.curSelDay = None # datetime.date object
        self.setSelDay(None)

    def createWindow(self, parentWnd, rect = None, style = win32con.WS_POPUP | win32con.WS_CHILD, className='STATIC', title=''):
        W, H = 250, 240
        super().createWindow(parentWnd, (0, 0, W, H), style, className, title)
        BTN_W, BTN_H = 20, 20
        self.nextBtnRect = (W - BTN_W - 5, 10, W - 5, 30)
        self.preBtnRect = (W - BTN_W * 2 - 15, 10, W - BTN_W - 15, 30)

    # x, y is screen pos
    def show(self, x = None, y = None):
        super().show(x, y)
        self.setSelDay(self.curSelDay)

    def onDraw(self, hdc):
        self.drawer.drawRect2(hdc, (0, 0, *self.getClientSize()), 0xAAAAAA)
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
        today = datetime.date.today()
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
            if isinstance(day, datetime.date) and day == today:
                self.drawer.drawText(hdc, txt, rc, 0x5555ff)
            else:
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
                    self.notifyListener('Select', {'day': sdd})
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

# listeners :  Select = {day: int}
class DatePicker(BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.popWin = DatePopupWindow()
        self.popWin.addListener(self.onSelDayChanged, 'DatePopupWindow')

    def setSelDay(self, selDay):
        self.popWin.setSelDay(selDay)
        self.invalidWindow()
    
    def getSelDay(self):
        day = self.popWin.curSelDay
        if not day:
            return None
        return f'{day.year}-{day.month :02d}-{day.day :02d}'

    def onSelDayChanged(self, evtName, evtInfo, args):
        if args != 'DatePopupWindow':
            return
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

# listeners : PressEnter = None
class Editor(BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0xf0f0f0
        self.css['textColor'] = 0x202020
        self.css['borderColor'] = 0xdddddd
        self.css['selBgColor'] = 0xf0c0c0
        self._createdCaret = False
        self.scrollX = 0 # always <= 0
        self.paddingX = 3 # 左右padding
        self.text = ''
        self.insertPos = 0
        self.selRange = None # (beginPos, endPos)

    def setText(self, text):
        if not text:
            self.text = ''
            return
        if not isinstance(text, str):
            text = str(text)
        self.text = text
        self.scrollX = 0
        self.setInsertPos(0)
    
    def setInsertPos(self, pos):
        self.selRange = None
        self.insertPos = pos
        if self._createdCaret and win32gui.GetFocus() == self.hwnd:
            rc = self.getCaretRect()
            win32gui.SetCaretPos(rc[0], rc[1])

    def makePosVisible(self, pos):
        if not self.text or pos < 0:
            return
        hdc = win32gui.GetDC(self.hwnd)
        self.drawer.use(hdc, self.drawer.getFont(fontSize=self.css['fontSize']))
        W, H = self.getClientSize()
        stw, *_ = win32gui.GetTextExtentPoint32(hdc, self.text[0 : pos])
        px = self.scrollX + stw + self.paddingX
        if px < self.paddingX:
            self.scrollX += self.paddingX - px
        elif px > W - self.paddingX:
            self.scrollX -= px - (W - self.paddingX)
        win32gui.ReleaseDC(self.hwnd, hdc)
        self.invalidWindow()

    def setSelRange(self, beginPos, endPos):
        if not self.text:
            self.selRange = None
            return
        beginPos = max(beginPos, 0)
        endPos = max(endPos, 0)
        beginPos = min(beginPos, len(self.text))
        endPos = min(endPos, len(self.text))
        if beginPos == endPos:
            self.selRange = None
            return
        if beginPos > endPos:
            beginPos, endPos = endPos, beginPos
        self.selRange = (beginPos, endPos)

    def deleteSelRangeText(self):
        if not self.selRange:
            return
        txt = self.text[0 : self.selRange[0]]
        txt2 = self.text[self.selRange[1] : ]
        self.text = txt + txt2
        if not self.text:
            self.insertPos = 0
            self.scrollX = 0
        self.selRange = None
        self.invalidWindow()

    def getXAtPos(self, pos):
        if not self.text or pos < 0:
            return self.paddingX
        hdc = win32gui.GetDC(self.hwnd)
        self.drawer.use(hdc, self.drawer.getFont(fontSize=self.css['fontSize']))
        tw, *_ = win32gui.GetTextExtentPoint32(hdc, self.text[0 : pos])
        x = self.scrollX + tw + self.paddingX
        win32gui.ReleaseDC(self.hwnd, hdc)
        return x
    
    def getPosAtX_Text(self, text, x):
        if not text:
            return 0
        hdc = win32gui.GetDC(self.hwnd)
        self.drawer.use(hdc, self.drawer.getFont(fontSize=self.css['fontSize']))
        pos = -1
        for i in range(0, len(text) + 1):
            cw, *_ = win32gui.GetTextExtentPoint32(hdc, self.text[0 : i])
            if x <= cw:
                pos = i
                break
        win32gui.ReleaseDC(self.hwnd, hdc)
        if pos >= 0:
            return pos
        return len(text)

    def getPosAtX(self, x):
        hdc = win32gui.GetDC(self.hwnd)
        pos = self.getPosAtX_Text(self.text, x - self.paddingX)
        win32gui.ReleaseDC(self.hwnd, hdc)
        return pos
    
    def onChar(self, key):
        if key < 32:
            return
        if self.selRange:
            self.deleteSelRangeText()
        ch = chr(key)
        if not self.text:
            self.text = ch
        else:
            self.text = self.text[0 : self.insertPos] + ch + self.text[self.insertPos : ]
        pos = self.insertPos + 1
        self.makePosVisible(pos)
        self.setInsertPos(pos)

    # (left, top, right, bottom)
    def getCaretRect(self):
        W, H = self.getClientSize()
        lh = self.css['fontSize'] + 4
        x = self.getXAtPos(self.insertPos)
        y = (H - lh ) // 2
        return (x, y, x + 1, y + lh)

    def drawCaret(self, hdc):
        if win32gui.GetFocus() != self.hwnd or self._createdCaret:
            return
        x, y, ex, ey = self.getCaretRect()
        self.drawer.drawLine(hdc, x, y, x, ey, 0x202020)

    def onDraw(self, hdc):
        if not self.text:
            self.drawCaret(hdc)
            return
        W, H = self.getClientSize()
        lh = self.css['fontSize']
        y = (H - lh) // 2
        if self.selRange:
            sx = self.getXAtPos(self.selRange[0])
            ex = self.getXAtPos(self.selRange[1])
            src = (sx, y - 2, ex, y + lh + 2)
            self.drawer.fillRect(hdc, src, self.css['selBgColor'])
        rc = (self.scrollX + self.paddingX, y, W, y + lh)
        self.drawer.drawText(hdc, self.text, rc, color=self.css['textColor'], align=win32con.DT_LEFT)
        self.drawCaret(hdc)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDOWN:
            win32gui.SetFocus(self.hwnd)
            x = lParam & 0xffff
            pos = self.getPosAtX(x)
            self.setInsertPos(pos)
            self.invalidWindow()
            return True
        if msg == win32con.WM_MOUSEMOVE:
            if wParam & win32con.MK_LBUTTON:
                x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
                pos = self.getPosAtX(x)
                self.setSelRange(self.insertPos, pos)
                self.invalidWindow()
            return True
        if msg == win32con.WM_LBUTTONDBLCLK:
            if self.text:
                self.setSelRange(0, len(self.text))
                self.invalidWindow()
            return True
        if msg == win32con.WM_CHAR or msg == win32con.WM_IME_CHAR:
            self.onChar(wParam)
            return True
        if msg == win32con.WM_KEYDOWN:
            if wParam == win32con.VK_LEFT:
                if self.insertPos > 0:
                    pos = self.insertPos - 1
                    self.makePosVisible(pos)
                    self.setInsertPos(pos)
            elif wParam == win32con.VK_RIGHT:
                if self.text and self.insertPos < len(self.text):
                    pos = self.insertPos + 1
                    self.makePosVisible(pos)
                    self.setInsertPos(pos)
            elif wParam == win32con.VK_DELETE:
                if self.selRange:
                    self.deleteSelRangeText()
                elif self.text and self.insertPos < len(self.text):
                    self.text = self.text[0 : self.insertPos] + self.text[self.insertPos + 1 : ]
                    self.makePosVisible(self.insertPos)
                    self.setInsertPos(self.insertPos)
                    self.invalidWindow()
            elif wParam == win32con.VK_BACK:
                if self.selRange:
                    self.deleteSelRangeText()
                elif self.text and self.insertPos > 0:
                    self.text = self.text[0 : self.insertPos - 1] + self.text[self.insertPos : ]
                    pos = self.insertPos - 1
                    self.makePosVisible(pos)
                    self.setInsertPos(pos)
                    self.invalidWindow()
            elif wParam == win32con.VK_RETURN:
                self.notifyListener('PressEnter', None)
            return True
        if msg == win32con.WM_SETFOCUS:
            rc = self.getCaretRect()
            win32gui.CreateCaret(self.hwnd, None, 1, rc[3] - rc[1])
            win32gui.SetCaretPos(rc[0], rc[1])
            win32gui.ShowCaret(self.hwnd)
            self._createdCaret = True
            return True
        if msg == win32con.WM_KILLFOCUS:
            if self._createdCaret:
                win32gui.HideCaret(self.hwnd)
                win32gui.DestroyCaret()
            self._createdCaret = False
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

def testPopMenu():
    def back(menu, e, ei):
        PopupMenuHelper.show(300, 100, model, menuSel)

    def menuSel(en, ei):
        print(en, ei)

    btn = Button({'title' : 'Hello'})
    btn.createWindow(None, (0, 0, 200, 100), win32con.WS_VISIBLE | win32con.WS_OVERLAPPEDWINDOW)
    model = [{'title': 'Hello 1 你好呀不' },  {'title': 'LINE'}, {'title': 'Hello 2'},
        {'title': 'Hello 3要'}, {'title': 'Hello 4'}, {'title': 'Hello 5'},
        {'title': 'Hello 6 kdil'},  {'title': 'LINE'}, {'title': 'Hello 7 KIL'}]
    btn.addListener(back, None)

if __name__ == '__main__':
    #testGridLayout()
    #testPopMenu()
    editor = Editor()
    editor.setText('Hel中国心人民')
    editor.setSelRange(2, 5)
    editor.createWindow(None, (300, 200, 200, 70), win32con.WS_OVERLAPPEDWINDOW  | win32con.WS_VISIBLE)
    win32gui.PumpMessages()
