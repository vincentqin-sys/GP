import win32gui, win32con, threading, time, os, sys

w = __file__.index('GP')
cwd = __file__[0 : w + 2]
sys.path.append(cwd)
from THS import ths_win, kline, base_win
from THS .download import henxin
from FuPan import multi_kline

# 板块概念对照个股的K线
class BKGN_KLineMgrWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()


win = multi_kline.MultiKLineWindow()
tsm = ths_win.ThsShareMemory()
selDay = 0
curCode = 0

def onListen(code, day):
    global selDay, win, curCode
    if code == curCode:
        return
    curCode = code
    win.updateCode(f'{code :06d}')
    win.invalidWindow()

if __name__ == '__main__':
    tsm.open()
    tsm.addListener('FP-1', onListen)
    rect = (0, 0, 1300, 400)
    win.createWindow(None, rect, win32con.WS_VISIBLE | win32con.WS_OVERLAPPEDWINDOW, title='复盘-K线对照')
    win32gui.ShowWindow(win.hwnd, win32con.SW_MAXIMIZE)
    win32gui.PumpMessages()