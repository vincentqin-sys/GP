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

    def onPressEnter(self, event, args):
        if event.name == 'PressEnter':
            self.close()
            self.notifyListener(self.Event('InputEnd', self, text = self.getText()))

# listeners: OK = {src(is dialog)}
#            Cancel = {src(is dialog)}
class ConfirmDialog(Dialog):
    # info : tip msg
    def __init__(self, info : str) -> None:
        super().__init__()
        self.info = info

    def createWindow(self, parentWnd, rect = (0, 0, 300, 150), style = win32con.WS_POPUP | win32con.WS_CHILD | win32con.WS_CAPTION, className='STATIC', title='I-ConfirmDialog'):
        super().createWindow(parentWnd, rect, style, className, title)
        w, h = self.getClientSize()
        layout = base_win.GridLayout(('1fr', 25), ('1fr', 60, 60), (10, 20))
        label = base_win.Label(self.info)
        label.createWindow(self.hwnd, (0, 0, 1, 1))
        okBtn = base_win.Button({'title': 'OK'})
        okBtn.createWindow(self.hwnd, (0, 0, 1, 1))
        calncelBtn = base_win.Button({'title': 'Cancel'})
        calncelBtn.createWindow(self.hwnd, (0, 0, 1, 1))

        layout.setContent(0, 0, label, {'horExpand': -1})
        layout.setContent(1, 1, okBtn)
        layout.setContent(1, 2, calncelBtn)
        layout.resize(10, 10, w - 20, h - 15)
        okBtn.addListener(self.onListen, 'OK')
        calncelBtn.addListener(self.onListen, 'Cancel')

    def onListen(self, evt, evtName):
        if evt.name != 'Click':
            return
        self.close()
        self.notifyListener(self.Event(evtName, self))

# listeners : SelectColor = color
class PopupColorWindow(base_win.PopupWindow):
    HSV_H_STEP = 30
    HSV_SV_STEP = 20
    COL_NUM = 360 // HSV_H_STEP
    ROW_NUM = 100 // HSV_SV_STEP * 2
    CELL_SIZE = 15

    def __init__(self) -> None:
        super().__init__()
        self.destroyOnHide = True

    def getColorAtXY(self, x, y):
        row = y // self.CELL_SIZE
        col = x // self.CELL_SIZE
        return self.getColor(row, col)

    def getColor(self, row, col):
        h = col * self.HSV_H_STEP
        s, v = 0, 0.6
        s = row * self.HSV_SV_STEP / 100 + 0.3
        if s > 1:
            v = s - 1
            s = 1
        if v > 1:
            v = 1
        color = base_win.Drawer.hsv2rgb(h, s, v)
        return color

    def onDraw(self, hdc):
        for r in range(self.ROW_NUM):
            for c in range(self.COL_NUM):
                sx = c * self.CELL_SIZE
                sy = r * self.CELL_SIZE
                self.drawer.fillRect(hdc, (sx, sy, sx + self.CELL_SIZE, sy + self.CELL_SIZE), self.getColor(r, c))

    def createWindow(self, parentWnd, rect = None, style = win32con.WS_POPUP | win32con.WS_CHILD, className='STATIC', title=''):
        W = self.CELL_SIZE * self.COL_NUM
        H = self.CELL_SIZE * self.ROW_NUM
        rect = (rect[0], rect[1], W, H)
        super().createWindow(parentWnd, rect, style, className, title)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            color = self.getColorAtXY(x, y)
            self.hide()
            if color >= 0:
                self.notifyListener(self.Event('SelectColor', self, color = color))
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

if __name__ == '__main__':
    cw = PopupColorWindow()
    cw.createWindow(None, (100, 100, 0, 0)) # , win32con.WS_OVERLAPPEDWINDOW
    
    #cw = ConfirmDialog("确认删除吗？")
    #cw.createWindow(None)
    #cw.showCenter()

    win32gui.ShowWindow(cw.hwnd, win32con.SW_SHOW)
    win32gui.PumpMessages()