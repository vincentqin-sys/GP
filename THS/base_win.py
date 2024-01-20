import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os

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
        print(f'[BaseWindow.createWindow] self.oldProc=0x{self.oldProc :x}, title=', title)

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


class CardView:
    def __init__(self, hwnd):
        self.hwnd = hwnd
    def onDraw(self, hdc):
        pass
    def winProc(self, hwnd, msg, wParam, lParam):
        return False

class CardWindow(BaseWindow):
    # maxSize = (width, height)
    # minSize = (width, height)
    def __init__(self, maxSize, minSize) -> None:
        super().__init__()
        self.cardViews = []
        self.MAX_SIZE = maxSize
        self.MIN_SIZE = minSize
        self.maxMode = True
        self.curCardViewIdx = 0

    def addCardView(self, cardView):
        self.cardViews.append(cardView)

    def onDraw(self, hdc):
        if self.maxMode and self.curCardViewIdx < len(self.cardViews):
            cardView = self.cardViews[self.curCardViewIdx]
            cardView.onDraw(hdc)
    
    def changeCardView(self):
        idx = self.curCardViewIdx
        self.curCardViewIdx = (idx + 1) % len(self.cardViews)
        if self.curCardViewIdx != idx:
            win32gui.InvalidateRect(self.hwnd, None, True)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_NCLBUTTONDBLCLK:
            self.maxMode = not self.maxMode
            if self.maxMode:
                win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, *self.MAX_SIZE, win32con.SWP_NOMOVE)
            else:
                win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, *self.MIN_SIZE, win32con.SWP_NOMOVE)
            return True
        if msg == win32con.WM_RBUTTONUP:
            self.changeCardView()
            return True

        if self.maxMode and self.curCardViewIdx < len(self.cardViews):
            cardView = self.cardViews[self.curCardViewIdx]
            r = cardView.winProc(hwnd, msg, wParam, lParam)
            if r != False:
                return r
        return super().winProc(hwnd, msg, wParam, lParam)

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
        

