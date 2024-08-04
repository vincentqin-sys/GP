import win32gui, win32con , win32api, win32ui, pyautogui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from db import ths_orm, tck_orm

_ths_gntc_s = {}


# return ths_orm.THS_GNTC dict
def get_THS_GNTC(code):
    if type(code) == int:
        code = f'{code :06d}'
    if not _ths_gntc_s:
        q = ths_orm.THS_GNTC.select().dicts()
        for it in q:
            _ths_gntc_s[it['code']] = it
    return _ths_gntc_s.get(code, None)


# day = int | str | date | datetime | float [ time.time() ]
def formatDate(day, hasSplit = True):
    if not day:
        return day
    if isinstance(day, float):
        day = datetime.datetime.fromtimestamp(day)
    if isinstance(day, datetime.date):
        if hasSplit:
            return f'{day.year}-{day.month :02d}-{day.day :02d}'
        return str(day.year * 10000 + day.month * 100 + day.day)
    if type(day) == int:
        if hasSplit:
            return f'{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}'
        return str(int)
    if type(day) == str:
        if len(day) == 8 and hasSplit:
            return day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : ]
    return day

# ts = float[ time.time() ] | datetime.datetime
def formatDateTime(ts):
    if isinstance(ts, float):
        ts = datetime.datetime.fromtimestamp(ts)
    ds = formatDate(ts)
    ms = f'{ts.hour :02d}:{ts.minute :02d}:{ts.second :02d}'
    return f'{ds} {ms}'