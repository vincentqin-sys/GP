import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr
from Common import base_win, timeline, kline
from Tck import ddlr_detail

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
    win.klineWin.addListener(openKlineMinutes, win)
    win.klineWin.makeVisible(-1)

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
    win.klineWin.makeVisible(-1)

def openKlineMinutes(evt, parent : base_win.BaseWindow):
    if evt.name != 'DbClick':
        return
    win = ddlr_detail.DDLR_MinuteMgrWindow()
    rc = win32gui.GetWindowRect(parent.hwnd)
    win.createWindow(parent.hwnd, rc, win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION)
    day = evt.data.day
    win.updateCodeDay(evt.code, day)