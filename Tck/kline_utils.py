import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr
from Common import base_win, timeline, kline
from Tck import ddlr_detail
from THS import ths_win

def openInCurWindow_Code(parent : base_win.BaseWindow, data):
    win = kline.KLineCodeWindow()
    win.addIndicator('rate | amount')
    win.addIndicator(kline.DayIndicator())
    #win.addIndicator(kline.DdlrIndicator( {'height': 100}))
    win.addIndicator(kline.DdlrIndicator({}, False))
    win.addIndicator(kline.DdlrPmIndicator())
    win.addIndicator(kline.HotIndicator())
    win.addIndicator(kline.TckIndicator())
    dw = win32api.GetSystemMetrics (win32con.SM_CXSCREEN)
    dh = win32api.GetSystemMetrics (win32con.SM_CYSCREEN) - 35
    W, H = 1250, min(750, dh)
    x = (dw - W) // 2
    y = (dh - H) // 2
    win.createWindow(parent.hwnd, (0, y, W, H), win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION)
    win.changeCode(data['code'])
    win.klineWin.setMarkDay(data['day'])
    win.klineWin.addListener(openKlineMinutes_Simple, win)
    win.klineWin.makeVisible(-1)
    return win

def openInCurWindow_ZS(parent : base_win.BaseWindow, data):
    win = kline.KLineCodeWindow()
    win.addIndicator('amount')
    win.addIndicator(kline.DayIndicator({}))
    win.addIndicator(kline.ThsZsPMIndicator({}))
    dw = win32api.GetSystemMetrics (win32con.SM_CXSCREEN)
    dh = win32api.GetSystemMetrics (win32con.SM_CYSCREEN) - 35
    W, H = 1250, min(750, dh)
    x = (dw - W) // 2
    y = (dh - H) // 2
    win.createWindow(parent.hwnd, (0, y, W, H), win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION)
    win.changeCode(data['code'])
    win.klineWin.setMarkDay(data['day'])
    win.klineWin.addListener(openKlineMinutes_Simple, win)
    win.klineWin.makeVisible(-1)
    return win

def openInCurWindow(parent : base_win.BaseWindow, data):
    code = data['code']
    if code[0] == '8':
        return openInCurWindow_ZS(parent, data)
    else:
        return openInCurWindow_Code(parent, data)

def openKlineMinutes_DDLR(evt, parent : base_win.BaseWindow):
    if evt.name != 'DbClick':
        return
    win = ddlr_detail.DDLR_MinuteMgrWindow()
    rc = win32gui.GetWindowRect(parent.hwnd)
    win.createWindow(parent.hwnd, rc, win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION)
    day = evt.data.day
    win.updateCodeDay(evt.code, day)

def openKlineMinutes_Simple(evt, parent : base_win.BaseWindow):
    if evt.name != 'DbClick':
        return
    win = timeline.SimpleTTimelineWindow()
    rc = win32gui.GetWindowRect(parent.hwnd)
    rc2 = (rc[0], rc[1], rc[2] - rc[0], rc[3] - rc[1])
    win.createWindow(parent.hwnd, rc2, win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION)
    day = evt.data.day
    win.load(evt.code, day)

thsWin = ths_win.ThsWindow()
thsWin.init()
def openInThsWindow(data):
    if not thsWin.topHwnd or not win32gui.IsWindow(thsWin.topHwnd):
        thsWin.topHwnd = None
        thsWin.init()
    if not thsWin.topHwnd:
        return
    win32gui.SetForegroundWindow(thsWin.topHwnd)
    time.sleep(0.5)
    pyautogui.typewrite(data['code'], 0.1)
    time.sleep(0.2)
    pyautogui.press('enter')