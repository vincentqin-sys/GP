import peewee as pw
from peewee import fn
import os, json, time, sys, pyautogui, io, datetime, win32api, win32event, winerror

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

from THS import orm, hot_utils
from Tdx import datafile
from Download import fiddler, ths_dd_win, ths_ddlr
from Common import holiday

def autoLoadOne(code, ddWin : ths_dd_win.THS_DDWindow):
    ddWin.grubFocusInSearchBox()
    # clear input text
    for i in range(20):
        pyautogui.press('backspace')
        pyautogui.press('delete')
    pyautogui.typewrite(code, 0.1)
    time.sleep(0.2)
    pyautogui.press('enter')
    time.sleep(5)
    ddWin.releaseFocus()
    if not ths_ddlr.codeExists(code):
        return False
    lds = ths_ddlr.ThsDdlrStructLoader()
    ldd = ths_ddlr.ThsDdlrDetailLoader()
    lds.loadOneFile(code, True)
    ldd.loadOneFile(code, True)
    return True

# 自动下载同花顺热点Top200个股的大单数据
def autoLoadTop200Data():
    d = datetime.datetime.today()
    print(d.strftime('%Y-%m-%d:%H:%M:%S'), '->')
    print('自动下载Top 200大单买卖数据(同花顺Level-2)')
    fd = fiddler.Fiddler()
    thsWin = ths_dd_win.THS_Window()
    ddWin = ths_dd_win.THS_DDWindow()
    successTimes, lxFailTimes = 0, 0
    try:
        fd.open()
        time.sleep(10)
        thsWin.open()
        ddWin.initWindows()
        if not ddWin.openDDLJ():
            print('同花顺大单页面打开失败')
            raise Exception()
        print('开始下载同花顺大单数据...')
        cs = getCodes()
        for i in range(len(cs) - 1, -1, -1):
            info = cs[i]
            sc = autoLoadOne(info['code'], ddWin)
            if sc:
                cs.pop(i)
                successTimes += 1
                lxFailTimes = 0
            else:
                info['times'] += 1
                lxFailTimes += 1
            if lxFailTimes >= 5:
                break
    except:
        pass
    ddWin.closeDDLJ()
    thsWin.close()
    fd.close()
    print(f'Load success {successTimes}')

def checkLoadFinised():
    cs = getCodes()
    fails = []
    for i in range(len(cs) - 1, -1, -1):
        info = cs[i]
        if info['times'] >= 3:
            fails.append(info['code'])
            cs.pop(i)
    if len(fails) > 0:
        print('Fails :', fails)
    return len(cs) == 0

def runOneTime():
    # check is finished
    if checkLoadFinised():
        return True
    pyautogui.hotkey('win', 'd')
    autoLoadTop200Data()
    print('\n')
    return checkLoadFinised()

def checkDDLR_Amount():
    query = orm.THS_DDLR.select(orm.THS_DDLR.code).distinct().where(orm.THS_DDLR.amount.is_null(True) | (orm.THS_DDLR.amount == 0) ).tuples()
    for q in query:
        code = q[0]
        df = datafile.DataFile(code, datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL)
        cs = orm.THS_DDLR.select().where(orm.THS_DDLR.code == code)
        for ddlr in cs:
            if not ddlr.amount:
                ad = df.getItemData(ddlr.day)
                if ad:
                    ddlr.amount = ad.amount / 100000000
                    ddlr.save()
    
def getDesktopGUILock():
    LOCK_NAME = 'D:/__Desktop_GUI_Lock__'
    mux = win32event.CreateMutex(None, False, LOCK_NAME)
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        win32api.CloseHandle(mux)
        return None
    return mux

def releaseDesktopGUILock(lock):
    if lock:
        win32api.CloseHandle(lock)

# seconds
def checkUserNoInputTime():
    a = win32api.GetLastInputInfo()
    cur = win32api.GetTickCount()
    diff = cur - a
    sec = diff / 1000
    return sec >= 5 * 60

_codes = {}
def getCodes():
    global _codes
    curDay = orm.THS_Hot.select(pw.fn.max(orm.THS_Hot.day)).scalar()
    if curDay in _codes:
        return _codes[curDay]
    ds = hot_utils.calcHotZHOnDay(curDay)
    datas = [{'code': f"{d['code'] :06d}", 'times': 0} for d in ds]
    datas.reverse()
    _codes[curDay] = datas
    return datas

def main():
    lastDay = None
    while True:
        today = datetime.datetime.now()
        if today.weekday() >= 5: # 周六周日
            time.sleep(60 * 60)
            continue
        if holiday.isHoliday(today):
            time.sleep(60 * 60)
            continue
        nowDay = today.strftime('%Y-%m-%d')
        if lastDay == nowDay:
            checkDDLR_Amount()
            time.sleep(60 * 60)
            continue
        st = today.strftime('%H:%M')
        if (st < '18:00' ):
            time.sleep(5 * 60)
            continue
        lock = getDesktopGUILock()
        if not lock:
            time.sleep(5 * 60)
            continue
        if runOneTime():
            lastDay = nowDay
            checkDDLR_Amount()
        releaseDesktopGUILock(lock)
        time.sleep(60 * 60)


if __name__ == '__main__':
    #runOneTime()
    main()