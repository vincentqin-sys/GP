import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr
from Common import base_win
from Tck import ddlr_detail, timeline, kline
from THS import ths_win

def createKLineWindow(parent, rect = None, style = None):
    win = kline.KLineCodeWindow()
    win.addIndicator('rate | amount')
    win.addIndicator(kline.DayIndicator())
    #win.addIndicator(kline.DdlrIndicator( {'height': 100}))
    #win.addIndicator(kline.DdlrIndicator({}, False))
    #win.addIndicator(kline.DdlrPmIndicator())
    win.addIndicator(kline.ScqxIndicator()) # {'itemWidth': 40}
    win.addIndicator(kline.HotIndicator()) # {'itemWidth': 40}
    win.addIndicator(kline.ThsZT_Indicator())
    win.addIndicator(kline.ClsZT_Indicator())
    win.addIndicator(kline.DdeIndicator())
    win.addIndicator(kline.LhbIndicator())
    dw = win32api.GetSystemMetrics (win32con.SM_CXSCREEN)
    dh = win32api.GetSystemMetrics (win32con.SM_CYSCREEN) - 35
    if not rect:
        BORDER = 7
        W, H = int(dw + BORDER * 2), max(int(dh * 0.85), 650)
        x = -BORDER
        y = dh - H
        rect = (x, y, W, H)
    if not style:
        style = win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION
    win.createWindow(parent, rect, style) # WS_OVERLAPPEDWINDOW
    win.klineWin.addListener(openKlineMinutes_Simple, win)
    return win

def openInCurWindow_Code(parent : base_win.BaseWindow, data):
    win = createKLineWindow(parent.hwnd)
    win.changeCode(data['code'])
    win.klineWin.setMarkDay(data.get('day', None))
    win.klineWin.makeVisible(-1)
    return win

def openInCurWindow_ZS(parent : base_win.BaseWindow, data):
    win = kline.KLineCodeWindow()
    win.addIndicator('amount')
    win.addIndicator(kline.DayIndicator({}))
    win.addIndicator(kline.ThsZsPMIndicator({}))
    dw = win32api.GetSystemMetrics (win32con.SM_CXSCREEN)
    dh = win32api.GetSystemMetrics (win32con.SM_CYSCREEN) - 35
    W, H = int(dw * 1), int(dh * 0.8)
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
    win = timeline.TimelinePanKouWindow()
    rc = win32gui.GetWindowRect(parent.hwnd)
    #rc2 = (rc[0], rc[1], rc[2] - rc[0], rc[3] - rc[1])
    SW = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    SH = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    w, h = max(800, int(SW * 0.6)), 600
    x, y = (SW - w) // 2, (SH - h) // 2
    rc2 = (x, y, w, h)
    win.createWindow(parent.hwnd, rc2, win32con.WS_POPUPWINDOW | win32con.WS_CAPTION)
    win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)
    day = evt.data.day
    win.load(evt.code, day)
    return win

def openInThsWindow(data):
    thsWin = ths_win.ThsWindow._ins
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