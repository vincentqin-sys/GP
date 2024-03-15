import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os
from multiprocessing import Process
from multiprocessing.shared_memory import SharedMemory

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from THS import orm, hot_utils, hot_win_small, ths_win, hot_win

curCode = None
thsWindow = ths_win.ThsWindow()
thsFPWindow = ths_win.ThsFuPingWindow()
hotWindow = hot_win.HotWindow()
simpleWindow = hot_win_small.SimpleWindow()
thsShareMem = ths_win.ThsShareMemory()
simpleHotZHWindow = hot_win_small.SimpleHotZHWindow()

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

windowsInfo = {}
def updateWindowInfo(thsWin):
    _id = id(thsWin)
    if _id not in windowsInfo:
        windowsInfo[_id] = {'curPageName': None}
    wi = windowsInfo[_id]
    curPageName = thsWin.getPageName()
    if not curPageName:
        return
    if wi['curPageName'] != curPageName: # changed page
        wi['curPageName'] = curPageName
        if curPageName not in wi:
            wi[curPageName] = {'s1': None, 's2': None}
        cp = wi[curPageName]
        simpleWindow.setWindowState(cp['s1'])
        simpleHotZHWindow.setWindowState(cp['s2'])
        if curPageName == '技术分析':
            ths_win.ThsSmallF10Window.adjustPos()
    else:
        if curPageName not in wi:
            wi[curPageName] = {'s1': None, 's2': None}
        cp = wi[curPageName]
        cp['s1'] = simpleWindow.getWindowState()
        cp['s2'] = simpleHotZHWindow.getWindowState()

def _workThread(thsWin):
    global curCode, windowsInfo
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
        updateWindowInfo(thsWin)
        nowCode = thsWin.findCode()
        if curCode != nowCode:
            updateCode(nowCode)
        selDay = thsWin.getSelectDay()
        if selDay:
            hotWindow.updateSelectDay(selDay)
            simpleWindow.changeSelectDay(selDay)
            thsShareMem.writeSelDay(selDay)

# show-hide sort wnd, liang dian wnd
def showSortAndLiangDianWindow(show, move):
    liangDianWnd = None # win32gui.FindWindow('smallF10_dlg', '小F10')
    left, _, right, _ = win32gui.GetWindowRect(thsWindow.topHwnd)
    width = right - left
    if show:
        simpleWindow.show()
        if liangDianWnd:
            win32gui.ShowWindow(liangDianWnd, win32con.SW_SHOW)
    else:
        simpleWindow.hide()
        if liangDianWnd:
            win32gui.ShowWindow(liangDianWnd, win32con.SW_HIDE)
    if move:
        if liangDianWnd:
            win32gui.SetWindowPos(liangDianWnd, None, 560, 800, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOREDRAW | win32con.SWP_NOZORDER)
        if width > 1500:
            win32gui.SetWindowPos(simpleWindow.hwnd, None, 1087, 800, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOREDRAW | win32con.SWP_NOZORDER)

def onListen(evtName, evtInfo, args):
    if args == 'ListenHotWindow' and evtName == 'mode.change':
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
    simpleHotZHWindow.createWindow(thsWindow.topHwnd)
    hotWindow.addListener(onListen, 'ListenHotWindow')
    threading.Thread(target = _workThread, args=(thsWindow, )).start()
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
    simpleHotZHWindow.createWindow(thsFPWindow.topHwnd)
    threading.Thread(target = _workThread, args=(thsFPWindow, )).start()
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
    th = threading.Thread(target=listen_ThsFuPing_Process, daemon=True, name='hot_win32.py')
    th.start()
    time.sleep(1)
    while True:
        p = Process(target = subprocess_main, daemon = True)
        p.start()
        print('start a new sub process, pid=', p.pid)
        p.join()
