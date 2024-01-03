import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os
from multiprocessing import Process
from multiprocessing.shared_memory import SharedMemory
import hot_simple_win, ths_win, hot_win

curCode = None
thsWindow = ths_win.ThsWindow()
hotWindow = hot_win.HotWindow()
simpleWindow = hot_simple_win.SimpleWindow()

def updateCode(nowCode):
    global curCode
    try:
        icode = int(nowCode)
    except Exception as e:
        nowCode = '0'
    if curCode == nowCode:
        return
    curCode = nowCode
    hotWindow.updateCode(nowCode)
    simpleWindow.changeCode(nowCode)

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

def _workThread():
    global curCode
    while True:
        time.sleep(0.5)
        #mywin.eyeWindow.show()
        if not win32gui.IsWindow(thsWindow.topHwnd):
            #win32gui.PostQuitMessage(0)
            #sys.exit(0)  #仅退出当前线程
            os._exit(0) # 退出进程
            break
        if True or thsWindow.isInKlineWindow() or thsWindow.isInMyHomeWindow():
            showHotWindow()
            nowCode = thsWindow.findCode()
            if curCode != nowCode:
                updateCode(nowCode)
            selDay = thsWindow.getSelectDay()
            if selDay:
                hotWindow.updateSelectDay(selDay)
                simpleWindow.changeSelectDay(selDay)
            if (not hotWindow.maxMode): #  and (not isInMyHomeWindow())
                #showSortAndLiangDianWindow(True, False)
                pass
        elif thsWindow.isInFenShiWindow():
            if not hotWindow.maxMode:
                #showSortAndLiangDianWindow(True, True)
                pass
            pass
        else:
            simpleWindow.hide()

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

def onListen(target, evtName, evtInfo):
    if target == 'ListenHotWindow' and evtName == 'mode.change':
        showSortAndLiangDianWindow(not evtInfo['maxMode'], True)

def subprocess_main():
    while True:
        if thsWindow.init():
            break
        time.sleep(10)
    hotWindow.createWindow(thsWindow.topHwnd)
    simpleWindow.createWindow(thsWindow.topHwnd)
    hotWindow.addListener('ListenHotWindow', onListen)
    threading.Thread(target = _workThread).start()
    win32gui.PumpMessages()
    print('Quit Sub Process')

if __name__ == '__main__':
    while True:
        p = Process(target = subprocess_main, daemon = True)
        p.start()
        print('start a new sub process, pid=', p.pid)
        p.join()
