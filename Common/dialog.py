import sys, win32con, win32gui, win32api
sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Common import base_win

class Dialog(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()

    def createWindow(self, parentWnd, rect, style = win32con.WS_POPUP | win32con.WS_CHILD | win32con.WS_CAPTION | win32con.WS_SYSMENU, className='STATIC', title='I-Dialog'):
        super().createWindow(parentWnd, rect, style, className, title)

    def showCenter(self):
        pr = win32gui.GetParent(self.hwnd)
        if pr:
            rc = win32gui.GetWindowRect(pr)
        else:
            rc = (0, 0, win32api.GetSystemMetrics(win32con.SM_CXSCREEN), win32api.GetSystemMetrics(win32con.SM_CYSCREEN))
        src = win32gui.GetWindowRect(self.hwnd)
        w = rc[2] - rc[0] - (src[2] - src[0])
        h = rc[3] - rc[1] - (src[3] - src[1])
        x = rc[0] + w // 2
        y = rc[1] + h // 2
        win32gui.SetWindowPos(self.hwnd, 0, x, y, 0, 0, win32con.SWP_NOZORDER | win32con.SWP_NOSIZE)
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.SetActiveWindow(self.hwnd)

    def hide(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)

    def close(self):
        #win32gui.CloseWindow(self.hwnd)
        win32gui.DestroyWindow(self.hwnd)

# listeners : InputEnd = {src, text}
class InputDialog(Dialog):
    def __init__(self) -> None:
        super().__init__()
        self.editor = base_win.Editor()
        self.css['bgColor'] = self.editor.css['bgColor']
        self.editor.css['borderColor'] = self.editor.css['bgColor']

    def setText(self, text):
        self.editor.setText(text)

    def getText(self):
        return self.editor.text

    def createWindow(self, parentWnd, rect, style = win32con.WS_POPUP | win32con.WS_CHILD | win32con.WS_CAPTION | win32con.WS_SYSMENU, className='STATIC', title='I-InputDialog'):
        super().createWindow(parentWnd, rect, style, className, title)
        w, h = self.getClientSize()
        self.editor.createWindow(self.hwnd, (10, 0, w - 20, h))
        self.editor.addListener(self.onPressEnter, None)

    def selectAll(self):
        txt = self.getText()
        if not txt:
            return
        self.editor.setSelRange(0, len(txt))

    def showCenter(self):
        super().showCenter()
        win32gui.SetFocus(self.editor.hwnd)

    def onPressEnter(self, evtName, evtInfo, args):
        if evtName == 'PressEnter':
            self.close()
            self.notifyListener('InputEnd', {'src': self, 'text': self.getText()})

# listeners : SelectColor = color
class PopupColorWindow(base_win.PopupWindow):
    MAX_COL_NUM = 13
    CELL_SIZE = 15
    def __init__(self) -> None:
        super().__init__()
        self.colors = [0x663300,0x996633,0xCC6633,0x993300,0x990000,0xCC0000,0x660000,0x666600,0x996600,0xCC9900,0xCC6600,0xCC3300,0xFF0000,0xFF3333,0x993333,0x999966,0x999900,0xCCCC33,0xFFCC00,0xFF9900,0xFF6600,0xFF6633,0xCC3333,0x996666,0x669933,0x99CC00,0xCCFF00,0xFFFF00,0xFFCC33,0xFF9933,0xFF9966,0xFF6666,0xFF0066,0xCC0066,0x339933,0x66CC00,0x99FF00,0xCCFF66,0xFFFF66,0xFFCC66,0xFFCC99,0xFF9999,0xFF6699,0xFF3399,0xFF0099,0x006600,0x00CC00,0x00FF00,0x99FF66,0xCCFF99,0xFFFFCC,0xFFCCCC,0xFF99CC,0xFF66CC,0xFF33CC,0xFF00CC,0xCC0099,0x003300,0x339900,0x33CC33,0x66FF66,0x99FF99,0xCCFFCC,0xFFFFFF,0xFFCCFF,0xFF99FF,0xFF66FF,0xFF00FF,0xCC00CC,0x660066,0x006633,0x009900,0x33FF66,0x66FF99,0x99FFCC,0xCCFFFF,0xCCCCFF,0xCC99FF,0xCC66FF,0xCC33FF,0x9900CC,0x993399,0x003333,0x009966,0x33FF99,0x66FFCC,0x99FFFF,0x99CCFF,0x9999FF,0x9966FF,0x9933FF,0x9933CC,0x990099,0x336666,0x00CC99,0x33FFCC,0x66FFFF,0x66CCFF,0x6699FF,0x6666FF,0x6600FF,0x9966CC,0x663399,0x669999,0x00CCCC,0x00FFFF,0x00CCFF,0x3399FF,0x0066FF,0x5050FF,0x6600CC,0x330066,0x336699,0x0099CC,0x0099FF,0x0066CC,0x0033FF,0x0000FF,0x0000CC,0x330099,0x003366,0x006699,0x0033CC,0x003399,0x000099,0x000080,0x333399]
        self.rowItems = [7, 8, 9, 10, 11, 12, 13, 12, 11, 10, 9, 8, 7]
        self.destroyOnHide = True

    def getColor(self, x, y):
        row = y // self.CELL_SIZE
        if row >= len(self.rowItems):
            return -1
        its = self.rowItems[row]
        sx = (self.MAX_COL_NUM - its) * self.CELL_SIZE // 2
        col = (x - sx) // self.CELL_SIZE
        if col >= its:
            return -1
        idx = 0
        for i in range(row):
            idx += self.rowItems[i]
        idx += col
        if idx >= len(self.colors):
            return -1
        return self.colors[idx]

    def onDraw(self, hdc):
        idx = 0
        for r in range(len(self.rowItems)):
            for c in range(self.rowItems[r]):
                sx = c * self.CELL_SIZE + (self.MAX_COL_NUM - self.rowItems[r]) * self.CELL_SIZE // 2
                sy = r * self.CELL_SIZE
                self.drawer.fillRect(hdc, (sx, sy, sx + self.CELL_SIZE, sy + self.CELL_SIZE), self.colors[idx])
                idx += 1

    def createWindow(self, parentWnd, rect = None, style = win32con.WS_POPUP | win32con.WS_CHILD, className='STATIC', title=''):
        WH = self.CELL_SIZE * self.MAX_COL_NUM
        if not rect:
            rect = (0, 0, WH, WH)
        else:
            rect = (rect[0], rect[1], WH, WH)
        super().createWindow(parentWnd, rect, style, className, title)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            color = self.getColor(x, y)
            self.hide()
            if color >= 0:
                self.notifyListener('SelectColor', color)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)


if __name__ == '__main__':
    cw = PopupColorWindow()
    cw.createWindow(None, (100, 100, 0, 0)) # , win32con.WS_OVERLAPPEDWINDOW
    win32gui.ShowWindow(cw.hwnd, win32con.SW_SHOW)
    win32gui.PumpMessages()