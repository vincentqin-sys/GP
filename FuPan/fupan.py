from win32.lib.win32con import WS_CHILD, WS_VISIBLE
import win32gui, win32con, sys, os
import ddlr, kpl, multi_kline

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from THS import base_win

class FuPanMgrWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.layout = base_win.GridLayout((30, '1fr'), ('100%', ), (5, 0))
        self.childWin = []
        self.cardLayout = base_win.Cardayout()

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        gp = base_win.GroupButton([{'name': 'KPL', 'title': '开盘啦'}, {'name': 'DDLR', 'title': '大单流入'}])
        gp.setSelGroup(0)
        gp.createWindow(self.hwnd, (0, 0, 200, 30))
        gp.addListener('GroupButton', self.changeGroup)
        gpLy = base_win.AbsLayout()
        gpLy.setContent(0, 0, gp)
        self.layout.setContent(0, 0, gpLy)

        kplWin = kpl.KPL_MgrWindow()
        kplWin.createWindow(self.hwnd, (0, 0, 1, 1))
        kplWin.init()
        self.cardLayout.addContent(kplWin)
        ddlrWin = ddlr.DDLR_MinuteMgrWindow()
        ddlrWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.cardLayout.addContent(ddlrWin)
        self.cardLayout.showCardByIdx(0)
        self.layout.setContent(1, 0, self.cardLayout)

    
    def changeGroup(self, target, evtName, evtInfo):
        idx = evtInfo['groupIdx']
        self.cardLayout.showCardByIdx(idx)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE and wParam != win32con.SIZE_MINIMIZED:
            w = lParam & 0xffff
            h = (lParam >> 16) & 0xffff
            self.layout.resize(0, 0, w, h)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

if __name__ == '__main__':
    fp = FuPanMgrWindow()
    fp.createWindow(None, (0, 0, 1000, 500), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    win32gui.ShowWindow(fp.hwnd, win32con.SW_MAXIMIZE)
    win32gui.PumpMessages()
