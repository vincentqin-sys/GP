import win32gui, win32con, threading, time
import ths_win, kline
from download import henxin

win = kline.KLineWindow()
tsm = ths_win.ThsShareMemory()
selDay = 0

def _workThread():
    global selDay, win
    while True:
        time.sleep(0.5)
        day = tsm.readSelDay()
        if selDay == day or not win.model:
            continue
        idx = win.model.getItemIdx(day)
        if idx < 0:
            continue
        selDay = day
        win.makeVisible(idx)
        win.setSelIdx(idx)

if __name__ == '__main__':
    tsm.open()
    rect = (0, 0, 1300, 500)
    win.createWindow(None, rect, win32con.WS_VISIBLE | win32con.WS_OVERLAPPEDWINDOW)
    henxinUrl = henxin.HexinUrl()
    win.loadCode_Ths(881164, henxinUrl)
    win.makeVisible(-1)
    threading.Thread(target = _workThread).start()
    win32gui.PumpMessages()