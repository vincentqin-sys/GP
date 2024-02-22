import peewee as pw
from peewee import fn
import os, json, time, sys, pyautogui, io, datetime, win32api, win32event, winerror

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

from THS import orm, hot_utils
from Tdx import datafile
from Download import fiddler, ths_dd_win, ths_ddlr
from Common import holiday

def autoLoadOne(code, ddWin):
    ddWin.grubFocusInSearchBox()
    # clear input text
    for i in range(20):
        pyautogui.press('backspace')
        pyautogui.press('delete')
    pyautogui.typewrite(code, 0.01)
    pyautogui.press('enter')
    time.sleep(3)
    ddWin.releaseFocus()
    return ths_ddlr.codeExists(code)

# 自动下载同花顺热点Top200个股的大单数据
def autoLoadTop200Data():
    d = datetime.datetime.today()
    print(d.strftime('%Y-%m-%d:%H:%M:%S'), '->')
    print('自动下载Top 200大单买卖数据(同花顺Level-2)')
    print('Fiddler拦截onBeforeResponse, 将数据下载下来')
    fd = fiddler.Fiddler()
    fd.open()
    time.sleep(10)

    ddWin = ths_dd_win.THS_DDWindow()
    ddWin.initWindows()
    if not ddWin.openDDLJ():
        fd.close()
        raise Exception('[autoLoadTop200Data] 同花顺的大单页面打开失败')
    
    curDay = orm.THS_Hot.select(pw.fn.max(orm.THS_Hot.day)).scalar()
    ds = hot_utils.calcHotZHOnDay(curDay)
    datas = [d['code'] for d in ds]
    MAX_NUM = len(datas)
    successTimes, failTimes = 0, 0
    fails = []
    for idx, code in enumerate(datas):
        code = f"{code :06d}"
        sc = autoLoadOne(code, ddWin)
        if sc: 
            successTimes += 1
        else: 
            failTimes += 1
            fails.append(code)
        if failTimes >= 10 and failTimes >= successTimes:
            break
    fd.close()
    print(f'Load {MAX_NUM}, Success {successTimes}, Fail {failTimes}')
    print('Fails: ', fails)
    print('Try load fails')
    for code in fails:
        sc = autoLoadOne(code, ddWin)
        if sc:
            tg = 'success' if sc else 'Fail'
            print('Load ', code, tg)
    if successTimes + failTimes != MAX_NUM:
        raise Exception('[autoLoadTop200Data] 下载失败')

def test2():
    curDay = orm.THS_Hot.select(pw.fn.max(orm.THS_Hot.day)).scalar()
    datas = orm.THS_Hot.select(orm.THS_Hot.code).distinct().where(orm.THS_Hot.day == curDay).tuples()
    datas = [d[0] for d in datas]
    print(len(datas))

def runOneTime():
    try:
        pyautogui.hotkey('win', 'd')
        autoLoadTop200Data()
        lds = ths_ddlr.LoadThsDdlrStruct()
        lds.loadAllFileData()
        ldd = ths_ddlr.LoadThsDdlrDetail()
        # 写入 xxxxxx.dd 文件， 数据格式： 日期;开始时间,买卖方式(1:主动买 2:被动买 3:主动卖 4:被动卖),成交金额(万元); ...
        ldd.loadAllFilesData()
        return True
    except Exception as e:
        print('Occur Exception: ', e)
    return False

def run():
    lock = getDesktopGUILock()
    if not lock:
        return False
    rs = False
    for i in range(3): # try 3 times
        rs = runOneTime()
        if rs:
            break
    releaseDesktopGUILock(lock)
    print('\n\n')
    return rs

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
            time.sleep(60 * 60)
            checkDDLR_Amount()
            continue
        st = today.strftime('%H:%M')
        if (st < '18:00' ):
            time.sleep(5 * 60)
            continue
        if run(): # checkUserNoInputTime() and
            lastDay = nowDay
            checkDDLR_Amount()


if __name__ == '__main__':
    main()