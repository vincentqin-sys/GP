import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, json, functools
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from db import tck_orm

def formatDay(day):
    if not day:
        return day
    if type(day) == int:
        return f'{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}'
    if type(day) == str:
        if len(day) == 8:
            return day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : ]
    return day

def _buildKey(data, kind, enableDays):
    if kind == None:
        kind = ''
    k = 'code' if 'code' in data else 'secu_code'
    if enableDays:
        key = f'{data[k]}:{kind}:{data["day"]}'
    else:
        key = f'{data[k]}:{kind}'
    return key

def mergeMarks(datas : list, kind, enableDays : bool):
    qr = tck_orm.Mark.select().dicts()
    marks = {}
    for d in qr:
        k = _buildKey(d, kind, enableDays)
        marks[k] = d
    for d in datas:
        k = _buildKey(d, kind, enableDays)
        if k in marks:
            d['markColor'] = marks[k]['markColor']
            d['markText'] = marks[k]['markText']

def getMarkModel(enable):
    model = [
        {'name': 'mark_1', 'title': '标记红色重点', 'enable': enable, 'markValue': 1},
        {'name': 'mark_2', 'title': '标记蓝色观察', 'enable': enable, 'markValue': 2},
        {'name': 'mark_3', 'title': '标记绿色负面', 'enable': enable, 'markValue': 3},
    ]
    return model

def markColor2RgbColor(markColor):
    if not markColor:
        return None
    CS = (0x0000dd, 0xdd0000, 0x00AA00)
    if markColor >= 1 and markColor <= len(CS):
        return CS[markColor - 1]
    return None

def markRender(win, hdc, row, col, colName, value, rowData, rect):
    color = win.css['textColor']
    mc = rowData.get('markColor', None)
    color = markColor2RgbColor(mc) or color
    align = win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE
    win.drawer.drawText(hdc, value, rect, color, align = align)

