import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, json, copy
from multiprocessing import Process
from multiprocessing.shared_memory import SharedMemory

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from THS import hot_utils, hot_win_small, ths_win, hot_win
from db import ths_orm

curCode = None
thsWindow = ths_win.ThsWindow()
thsFPWindow = ths_win.ThsFuPingWindow()
hotWindow = hot_win.HotWindow()
simpleWindow = hot_win_small.SimpleWindow('HOT')
simpleWindow2 = hot_win_small.SimpleWindow('ZT_GN')
thsShareMem = ths_win.ThsShareMemory()
simpleHotZHWindow = hot_win_small.SimpleHotZHWindow()
codeBasicWindow = hot_win_small.CodeBasicWindow()

def updateCode(nowCode):
    global curCode, thsShareMem
    try:
        icode = int(nowCode)
    except Exception as e:
        nowCode = '0'
    if curCode == nowCode:
        return
    curCode = nowCode
    hotWindow.updateCode(nowCode)
    simpleWindow.changeCode(nowCode)
    simpleWindow2.changeCode(nowCode)
    codeBasicWindow.changeCode(nowCode)
    thsShareMem.writeCode(nowCode)

def showHotWindow():
    # check window size changed
    if hotWindow.rect[1] > 0: # y > 0
        return
    rr = win32gui.GetClientRect(thsWindow.topHwnd)
    y = rr[3] - rr[1] - hotWindow.rect[3]
    if y < 0:
        return
    x = hotWindow.rect[0]
    win32gui.SetWindowPos(hotWindow.hwnd, 0, x, y, 0, 0, 0x0010|0x0200|0x0001|0x0004)
    hotWindow.rect = (x, y, hotWindow.rect[2], hotWindow.rect[3])

class WinStateMgr:
    def __init__(self, fileName) -> None:
        self.curPageName = None
        self.windowsInfo = {}
        path = os.path.dirname(__file__)
        path = os.path.join(path, fileName)
        self.fileName = path

    def read(self):
        if not os.path.exists(self.fileName):
            return
        file = open(self.fileName, 'r')
        txt = file.read().strip()
        file.close()
        if txt:
            self.windowsInfo = json.loads(txt)

    def save(self):
        file = open(self.fileName, 'w')
        txt = json.dumps(self.windowsInfo)
        file.write(txt)
        file.close()

def updateWindowInfo(thsWin, stateMgr : WinStateMgr):
    winsInfo = stateMgr.windowsInfo
    curPageName = thsWin.getPageName()
    if not curPageName:
        return
    if stateMgr.curPageName!= curPageName: # changed page
        stateMgr.curPageName = curPageName
        if curPageName not in winsInfo:
            winsInfo[curPageName] = {'s1': None, 's2': None, 's3': None, 's4': None}
        cp = winsInfo[curPageName]
        simpleWindow.setWindowState(cp.get('s1', None))
        simpleWindow2.setWindowState(cp.get('s3', None))
        simpleHotZHWindow.setWindowState(cp.get('s2', None))
        codeBasicWindow.setWindowState(cp.get('s4', None))
        if curPageName == '技术分析':
            ths_win.ThsSmallF10Window.adjustPos()
    else:
        if curPageName not in winsInfo:
            winsInfo[curPageName] = {'s1': None, 's2': None, 's3': None}
        cp = winsInfo[curPageName]
        cp2 = {}
        cp2['s1'] = simpleWindow.getWindowState()
        cp2['s2'] = simpleHotZHWindow.getWindowState()
        cp2['s3'] = simpleWindow2.getWindowState()
        cp2['s4'] = codeBasicWindow.getWindowState()
        if cp != cp2:
            cp.update(cp2)
            stateMgr.save()

def _workThread(thsWin, fileName):
    global curCode
    stateMgr = WinStateMgr(fileName)
    stateMgr.read()
    while True:
        time.sleep(0.5)
        #mywin.eyeWindow.show()
        if not win32gui.IsWindow(thsWin.topHwnd):
            #win32gui.PostQuitMessage(0)
            #sys.exit(0)  #仅退出当前线程
            os._exit(0) # 退出进程
            break
        #showHotWindow()
        if win32gui.GetForegroundWindow() != thsWin.topHwnd:
            continue
        updateWindowInfo(thsWin, stateMgr)
        nowCode = thsWin.findCode()
        if curCode != nowCode:
            updateCode(nowCode)
        selDay = thsWin.getSelectDay()
        if selDay:
            hotWindow.updateSelectDay(selDay)
            simpleWindow.changeSelectDay(selDay)
            simpleWindow2.changeSelectDay(selDay)
            thsShareMem.writeSelDay(selDay)

def onListen(evt, args):
    if args == 'ListenHotWindow' and evt.name == 'mode.change':
        #showSortAndLiangDianWindow(not evtInfo['maxMode'], True)
        pass

def subprocess_main():
    while True:
        if thsWindow.init():
            break
        time.sleep(10)
    thsShareMem.open()
    hotWindow.createWindow(thsWindow.topHwnd)
    simpleWindow.createWindow(thsWindow.topHwnd)
    simpleWindow2.createWindow(thsWindow.topHwnd)
    simpleHotZHWindow.createWindow(thsWindow.topHwnd)
    codeBasicWindow.createWindow(thsWindow.topHwnd)
    hotWindow.addListener(onListen, 'ListenHotWindow')
    threading.Thread(target = _workThread, args=(thsWindow, 'hot-win32.json')).start()
    win32gui.PumpMessages()
    print('Quit Sub Process')

def subprocess_main_fp():
    while True:
        if thsFPWindow.init():
            break
        time.sleep(10)
    thsShareMem.open()
    hotWindow.createWindow(thsFPWindow.topHwnd)
    simpleWindow.createWindow(thsFPWindow.topHwnd)
    simpleWindow2.createWindow(thsFPWindow.topHwnd)
    simpleHotZHWindow.createWindow(thsFPWindow.topHwnd)
    threading.Thread(target = _workThread, args=(thsFPWindow, 'hot-win32-fp.json')).start()
    win32gui.PumpMessages()
    print('Quit Sub Process(THS FU PING)')    


def listen_ThsFuPing_Process():
    print('open listen fu ping prcess')
    while True:
        p = Process(target = subprocess_main_fp, daemon = True)
        p.start()
        print('start a new sub process(FU PING), pid=', p.pid)
        p.join()

if __name__ == '__main__':
    tsm = ths_win.ThsShareMemory(True)
    tsm.open()
    # listen ths fu ping
    #p = Process(target = listen_ThsFuPing_Process, daemon = False, name='hot_win32.py')
    #p.start()
    #th = threading.Thread(target=listen_ThsFuPing_Process, daemon=True, name='hot_win32.py')
    #th.start()
    #time.sleep(1)
    while True:
        p = Process(target = subprocess_main, daemon = True)
        p.start()
        print('start a new sub process, pid=', p.pid)
        p.join()
