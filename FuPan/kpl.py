import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys

cwd = os.getcwd()
w = cwd.index('GP')
cwd = cwd[0 : w + 2]
sys.path.append(cwd)
from Tdx import datafile
from THS.download import henxin, load_ths_ddlr
from THS import orm as ths_orm, base_win, kline

class KPL_Window(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()

    def onDraw(self, hdc):
        self.drawSCQX(hdc)
        pass

    def drawSCQX(self, hdc):
        pass

class KPL_Mgr:
    def __init__(self) -> None:
        self.layout = base_win.GridLayout((100, '1fr'), ('100%', ), (10, 0))

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            w, h = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.layout.resize(0, 100, w, h)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)
