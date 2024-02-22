import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, threading
import sys, pyautogui
import peewee as pw

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from THS import orm, hot_utils
from Download import henxin
from Common import base_win

#-----------------------------------------------------------
class ThsSortQuery:
    lhbDB = None

    def __init__(self):
        path = sys.argv[0]
        path = path[0 : path.index('GP') ]
        if not ThsSortQuery.lhbDB:
            ThsSortQuery.lhbDB = pw.SqliteDatabase(f'{path}GP/db/LHB.db')
        
    def getPMTag(self, v):
        if (v < 0.2): return '优秀'
        if (v < 0.4): return '良好'
        if (v < 0.6): return '一般'
        if (v < 0.8): return '较差'
        return '垃圾'

    def getLhbInfo(self, code):
        cc = self.lhbDB.cursor()
        cc.execute('select count(*) from tdxlhb where code = "' + code + '" ')
        data = cc.fetchone()
        count = data[0]
        cc.close()
        txt = f'龙虎榜 {count}次'
        return txt
    
    def getMaxHotInfo(self, code):
        code = int(code)
        maxHotZH = orm.THS_HotZH.select(pw.fn.min(orm.THS_HotZH.zhHotOrder), orm.THS_HotZH.day).where(orm.THS_HotZH.code == code).tuples()
        maxHot = orm.THS_Hot.select(pw.fn.min(orm.THS_Hot.hotOrder), orm.THS_Hot.day).where(orm.THS_Hot.code == code).tuples()
        info = ''
        for d in maxHotZH:
            if d[0]:
                info = f'最高热度综合排名: {d[0] :> 3d}  {d[1] // 10000}.{d[1] // 100 % 100:02d}.{d[1]%100:02d}'
            break
        for d in maxHot:
            if d[0]:
                info += f'\n    最高热度排名: {d[0] :> 3d}  {d[1] // 10000}.{d[1] // 100 % 100:02d}.{d[1]%100:02d}'
            break
        return info

    def getCodeInfo_THS(self, code):
        code = int(code)
        code = "%06d" % code
        gdInfo = orm.THS_Top10_LTGD.select().where(orm.THS_Top10_LTGD.code == code).order_by(orm.THS_Top10_LTGD.day.desc())
        jgcgInfo = orm.THS_JGCG.select().where(orm.THS_JGCG.code == code).order_by(orm.THS_JGCG.day_sort.desc())
        hydbInfo = orm.THS_HYDB.select().where(orm.THS_HYDB.code == code).order_by(orm.THS_HYDB.day.desc())

        name = ''
        rate = '--'
        jgNum = '--'
        for jgcg in jgcgInfo:
            jgNum = jgcg.jjsl
            rate = int(jgcg.rate) if jgcg.rate else 0
            break
        jg = f"机构 {jgNum}家, 持仓{rate}%"

        for gd in gdInfo:
            rate = int(gd.rate) if gd.rate else 0
            jg += f'   前十流通股东{rate}%'
            break

        hy2, hy3 = '', ''
        hyName = ''
        gntc = orm.THS_GNTC.get_or_none(code = code)
        if gntc:
            hyName = gntc.hy
            name = gntc.name
        for m in hydbInfo:
            if m.hydj == '三级' and not hy3:
                hy3 = f'  {m.hydj} {m.zhpm} / {m.hysl} [{self.getPMTag(m.zhpm / m.hysl)}]\n'
            elif m.hydj == '二级' and not hy2:
                hy2 = f'  {m.hydj} {m.zhpm} / {m.hysl} [{self.getPMTag(m.zhpm / m.hysl)}]\n'
        txt = hyName + '\n' + jg + '\n' + hy2 + hy3
        # 龙虎榜信息
        txt += self.getLhbInfo(code)
        txt += '\n' + self.getMaxHotInfo(code)
        return {'info': txt, 'code': code, 'name': name}

# param days (int): [YYYYMMDD, ....]
# param selDay : int
# return [startIdx, endIdx)
def findDrawDaysIndex(days, selDay, maxNum):
    if not days:
        return (0, 0)
    if len(days) <= maxNum:
        return (0, len(days))
    if not selDay:
        return (len(days) - maxNum, len(days))
    if type(days[0]) != int:
        for i in range(len(days)):
            days[i] = int(days[i].replace('-', '.'))
    #最左
    if selDay <= days[0]:
        return (0, maxNum)
    #最右
    if selDay >= days[len(days) - 1]:
        return (len(days) - maxNum, len(days))
    
    idx = 0
    for i in range(len(days) - 1): # skip last day
        if (selDay >= days[i]) and (selDay < days[i + 1]):
            idx = i
            break
    # 居中优先显示
    fromIdx = lastIdx = idx
    while True:
        if lastIdx < len(days):
            lastIdx += 1
        if lastIdx - fromIdx >= maxNum:
            break
        if fromIdx > 0:
            fromIdx -= 1
        if lastIdx - fromIdx >= maxNum:
            break
    return (fromIdx, lastIdx)

class CardView:
    def __init__(self, hwnd):
        self.hwnd = hwnd
    def onDraw(self, hdc):
        pass
    def winProc(self, hwnd, msg, wParam, lParam):
        return False
    def getWindowTitle(self):
        return None

class CardWindow(base_win.BaseWindow):
    # maxSize = (width, height)
    # minSize = (width, height)
    def __init__(self, maxSize, minSize) -> None:
        super().__init__()
        self.cardViews = []
        self.MAX_SIZE = maxSize
        self.MIN_SIZE = minSize
        self.maxMode = True
        self.curCardViewIdx = 0

    def addCardView(self, cardView):
        self.cardViews.append(cardView)

    def getCurCardView(self):
        if self.cardViews:
            idx = self.curCardViewIdx % len(self.cardViews)
            return self.cardViews[idx]
        return None

    def onDraw(self, hdc):
        cardView = self.getCurCardView()
        if self.maxMode and cardView:
            cardView.onDraw(hdc)
    
    def changeCardView(self):
        idx = self.curCardViewIdx
        self.curCardViewIdx = (idx + 1) % len(self.cardViews)
        if self.curCardViewIdx != idx:
            cv = self.getCurCardView()
            title = cv.getWindowTitle()
            if title != None:
                win32gui.SetWindowText(self.hwnd, title)
            win32gui.InvalidateRect(self.hwnd, None, True)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_NCLBUTTONDBLCLK:
            self.maxMode = not self.maxMode
            if self.maxMode:
                win32gui.SetWindowPos(self.hwnd, 0, 0, 0, *self.MAX_SIZE, win32con.SWP_NOMOVE | win32con.SWP_NOZORDER) # win32con.HWND_TOP
            else:
                win32gui.SetWindowPos(self.hwnd, 0, 0, 0, *self.MIN_SIZE, win32con.SWP_NOMOVE| win32con.SWP_NOZORDER)
            return True
        if msg == win32con.WM_RBUTTONUP:
            self.changeCardView()
            return True

        cardView = self.getCurCardView()
        if self.maxMode and cardView:
            r = cardView.winProc(hwnd, msg, wParam, lParam)
            if r != False:
                return r
        return super().winProc(hwnd, msg, wParam, lParam)

#-------------小窗口----------------------------------------------
class SortCardView(CardView):
    def __init__(self, hwnd):
        super().__init__(hwnd)
        self.query = ThsSortQuery()
        self.sortData = None
        self.selectDay = 0

    def updateSelectDay(self, selDay):
        self.selectDay = selDay

    def updateCode(self, code):
        if type(code) == int:
            code = f'{code :06d}'
        # load sort data
        self.zsData = None
        self.sortData = self.query.getCodeInfo_THS(code)
        win32gui.SetWindowText(self.hwnd, f'{self.sortData["code"]} {self.sortData["name"]}')

    def onDraw(self, hdc):
        if not self.sortData:
            return
        win32gui.SetTextColor(hdc, 0xdddddd)
        lines = self.sortData['info'].split('\n')
        rect = win32gui.GetClientRect(self.hwnd)
        for i, line in enumerate(lines):
            H = 18
            y = i * H + 2
            win32gui.DrawText(hdc, line, len(line), (2, y, rect[2], y + H), win32con.DT_LEFT)

class ZSCardView(CardView):
    def __init__(self, hwnd):
        super().__init__(hwnd)
        self.selectDay = 0

    def onDraw(self, hdc):
        if not self.zsData:
            return
        H = 18
        rect = win32gui.GetClientRect(self.hwnd)
        RH = rect[3] - rect[1]
        RW = rect[2] - rect[0]
        MAX_ROWS = RH // H - 2
        days = [d['day'] for d in self.zsData]
        fromIdx, endIdx = findDrawDaysIndex(days, self.selectDay, MAX_ROWS * 2)
        for i in range(fromIdx, endIdx):
            zs = self.zsData[i]
            if zs['day'] == self.selectDay:
                win32gui.SetTextColor(hdc, 0x0000ff)
            else:
                win32gui.SetTextColor(hdc, 0xdddddd)
            day = str(zs['day'])[4 : ]
            day = day[0 : 2] + '.' + day[2 : 4]
            idx = i - fromIdx
            y = (idx % MAX_ROWS) * H + 2 + H
            x = RW // 2 if idx >= MAX_ROWS else 0
            rect = (x + 2, y, x + RW // 2, y + H)
            line = f'{day}    {zs["zdf_PM"] :< 4d}     {zs["zdf_50PM"] :< 6d}'
            win32gui.DrawText(hdc, line, len(line), rect, win32con.DT_LEFT)
        # draw title
        pen = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xaaccaa)
        win32gui.SelectObject(hdc, pen)
        win32gui.SetTextColor(hdc, 0xdddddd)
        for i in range(2):
            trc = (i * RW // 2, 0, i * RW // 2 + RW // 2, H)
            title = f'       全市排名  50亿排名'
            win32gui.DrawText(hdc, title, len(title), trc, win32con.DT_LEFT)
        win32gui.MoveToEx(hdc, 0, H)
        win32gui.LineTo(hdc, RW, H)
        win32gui.MoveToEx(hdc, RW // 2, 0)
        win32gui.LineTo(hdc, RW // 2, RH)
        win32gui.DeleteObject(pen)
    
    def updateCode(self, code):
        self.zsData = self.getZSInfo(code)
        name = self.zsData[0]['name'] if self.zsData else ''
        win32gui.SetWindowText(self.hwnd, f'{code} {name}')

    def getZSInfo(self, zsCode):
        if type(zsCode) == int:
            zsCode = f'{zsCode :06d}'
        qr = orm.THS_ZS_ZD.select().where(orm.THS_ZS_ZD.code == zsCode).order_by(orm.THS_ZS_ZD.day.asc())
        data = [d.__data__ for d in qr]
        for d in data:
            d['day'] = int(d['day'].replace('-', ''))
        return data
    
    def updateSelectDay(self, selDay):
        if type(selDay) == str:
            selDay = int(selDay.replace('-', ''))
        self.selectDay = selDay

class HotCardView(CardView):
    def __init__(self, hwnd):
        super().__init__(hwnd)
        self.hotData = None
        self.ROW_HEIGHT = 18
        self.hotsInfo = [None] * 25  # {data: , rect: (), }
        self.tipInfo = {} # {rect:(), hotInfo: xx, detail:[], }
        self.resetTipInfo()
        self.showStartIdx = 0
        self.selectDay = 0

    def resetTipInfo(self):
        self.tipInfo['rect'] = None
        self.tipInfo['hotRect'] = None
        self.tipInfo['detail'] = None

    def updateSelectDay(self, selDay):
        self.selectDay = selDay

    def onDraw(self, hdc):
        rect = win32gui.GetClientRect(self.hwnd)
        if not self.hotData:
            win32gui.SetTextColor(hdc, 0xdddddd)
            win32gui.DrawText(hdc, '无Hot信息', -1, rect, win32con.DT_CENTER)
            return
        rr = win32gui.GetClientRect(self.hwnd)
        win32gui.SetTextColor(hdc, 0xdddddd)
        H = 18
        rect = win32gui.GetClientRect(self.hwnd)
        RH = rect[3] - rect[1]
        RW = rect[2] - rect[0]
        MAX_ROWS = RH // H
        days = [d['day'] for d in self.hotData]
        fromIdx, endIdx = findDrawDaysIndex(days, self.selectDay, MAX_ROWS * 2)
        for i in range(len(self.hotsInfo)):
            self.hotsInfo[i] = None
        for i in range(fromIdx, endIdx):
            hot = self.hotData[i]
            if hot['day'] == self.selectDay:
                win32gui.SetTextColor(hdc, 0x0000ff)
            else:
                win32gui.SetTextColor(hdc, 0xdddddd)
            day = str(hot['day'])[4 : ]
            day = day[0 : 2] + '.' + day[2 : 4]
            zhHotOrder = '' if hot['zhHotOrder'] == 0 else f"{hot['zhHotOrder'] :>3d}"
            avgHotOrder = f"{hot['avgHotOrder'] :.1f}"
            avgHotOrder = avgHotOrder[0 : 3]
            avgHotVal = int(hot['avgHotValue'])
            line = f"{day} {hot['minOrder'] :>3d}->{hot['maxOrder'] :<3d} {avgHotVal :>3d}万 {zhHotOrder}"
            idx = i - fromIdx
            y = (idx % MAX_ROWS) * H + 2
            x = RW // 2 if idx >= MAX_ROWS else 0
            rect = (x + 2, y, x + RW // 2, y + H)
            win32gui.DrawText(hdc, line, len(line), rect, win32con.DT_LEFT)
            self.hotsInfo[i - fromIdx] = {'data': hot, 'rect': rect}
        pen = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xaaccaa)
        win32gui.SelectObject(hdc, pen)
        win32gui.MoveToEx(hdc, RW // 2, 0)
        win32gui.LineTo(hdc, RW // 2, rr[3])
        self.drawTip(hdc)
        win32gui.DeleteObject(pen)

    def drawTip(self, hdc):
        tipRect = self.tipInfo['rect']
        if not tipRect:
            return
        hotDetail = self.tipInfo['detail']
        if not hotDetail:
            return
        bk = win32gui.CreateSolidBrush(0)
        ps = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
        win32gui.SelectObject(hdc, ps)
        win32gui.SelectObject(hdc, bk)
        win32gui.Rectangle(hdc, *tipRect)
        si1 = max(self.showStartIdx, 0)
        si2 = max(0, len(hotDetail) - 5)
        si = min(si1, si2)
        self.showStartIdx = si
        win32gui.SetTextColor(hdc, 0x3333CD)
        for i in range(si, len(hotDetail)):
            hot = hotDetail[i]
            txt = f" {hot['time'] // 100 :02d}:{hot['time'] % 100 :02d}  {hot['hotValue'] :>3d}万  {hot['hotOrder'] :>3d}"
            y = (i - si) * self.ROW_HEIGHT + 5
            rc = (tipRect[0], y, tipRect[2], y + self.ROW_HEIGHT)
            win32gui.DrawText(hdc, txt, len(txt), rc, win32con.DT_CENTER)
        rc = self.tipInfo['hotRect']
        win32gui.MoveToEx(hdc, rc[0], rc[3] - 2)
        win32gui.LineTo(hdc, rc[2], rc[3] - 2)
        win32gui.DeleteObject(bk)
        win32gui.DeleteObject(ps)

    def updateCode(self, code):
        self.showStartIdx = 0
        self.resetTipInfo()
        for i in range(len(self.hotsInfo)):
            self.hotsInfo[i] = None
        if type(code) != int:
            code = int(code)
        self.code = code
        # load hot data
        qq = orm.THS_Hot.select(orm.THS_Hot.day, pw.fn.min(orm.THS_Hot.hotOrder).alias('minOrder'), pw.fn.max(orm.THS_Hot.hotOrder).alias('maxOrder')).where(orm.THS_Hot.code == code).group_by(orm.THS_Hot.day) #.order_by(orm.THS_Hot.day.desc())
        #print(qq.sql())
        self.hotData = [d for d in qq.dicts()]
        qq2 = orm.THS_HotZH.select(orm.THS_HotZH.day, orm.THS_HotZH.zhHotOrder, orm.THS_HotZH.avgHotOrder, orm.THS_HotZH.avgHotValue).where(orm.THS_HotZH.code == code)
        qdata = {}
        for d in qq2.tuples():
            qdata[d[0]] = d[1 : ]
        for d in self.hotData:
            day = d['day']
            if day in qdata:
                d['zhHotOrder'] = qdata[day][0]
                d['avgHotOrder'] = qdata[day][1]
                d['avgHotValue'] = qdata[day][2]
            else:
                d['zhHotOrder'] = 0
                d['avgHotOrder'] = 0
                d['avgHotValue'] = 0

        if self.hotData and len(self.hotData) > 0:
            last = self.hotData[-1]
            if last['zhHotOrder'] == 0:
                rd = hot_utils.calcHotZHOnDayCode(last['day'], code)
                if rd:
                    last['zhHotOrder'] = rd['zhHotOrder']
                    last['avgHotOrder'] = rd['avgHotOrder']
                    last['avgHotValue'] = rd['avgHotValue']

    def isInRect(self, x, y, rect):
        if not rect:
            return False
        f1 = x >= rect[0] and x < rect[2]
        f2 = y >= rect[1] and y < rect[3]
        return f1 and f2

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            self.showStartIdx = 0
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            if self.isInRect(x, y, self.tipInfo['rect']):
                self.resetTipInfo()
                win32gui.InvalidateRect(hwnd, None, True)
                return True
            for hot in self.hotsInfo:
                if hot and self.isInRect(x, y, hot['rect']):
                    if self.tipInfo['hotRect'] == hot['rect']:
                        self.resetTipInfo()
                    else:
                        self.setTip(hot)
                    win32gui.InvalidateRect(hwnd, None, True)
                    return True
        if msg == win32con.WM_MOUSEWHEEL:
            delta = (wParam >> 16) & 0xffff
            if delta & 0x8000:
                self.showStartIdx += 5
            else:
                self.showStartIdx -= 5
            win32gui.InvalidateRect(hwnd, None, True)
            return True
        return False
    
    def setTip(self, hot):
        code = self.code
        rr = win32gui.GetClientRect(self.hwnd)
        w, h = rr[2], rr[3]
        if (hot['rect'][0] + hot['rect'][2]) >= w:
            tipRect = (0, 0, w // 2, h)
        else:
            tipRect = (w // 2, 0, w, h)
        self.tipInfo['rect'] = tipRect
        self.tipInfo['hotRect'] = hot['rect']
        if 'detail' not in hot:
            day = hot['data']['day']
            info = orm.THS_Hot.select().where(orm.THS_Hot.code == code, orm.THS_Hot.day == day)
            hot['detail'] = [d.__data__ for d in info]
        self.tipInfo['detail'] = hot['detail']

class KPLCardView(CardView):
    def __init__(self, hwnd):
        super().__init__(hwnd)
        self.kplZTData = None
        self.ROW_HEIGHT = 18
        self.selectDay = 0

    def updateSelectDay(self, selDay):
        self.selectDay = selDay

    def updateCode(self, code):
        qq = orm.KPL_ZT.select().where(orm.KPL_ZT.code == code).order_by(orm.KPL_ZT.day.asc())
        def fmtDay(d): 
            d['day'] = d['day'].replace('-', '')
            return d
        self.kplZTData = [fmtDay(d) for d in qq.dicts()]

    def onDraw(self, hdc):
        win32gui.SetTextColor(hdc, 0xdddddd)
        rect = win32gui.GetClientRect(self.hwnd)
        if not self.kplZTData:
            line = '\n\n无开盘啦涨停信息'
            win32gui.DrawText(hdc, line, len(line), rect, win32con.DT_CENTER)
            return
        
        H = self.ROW_HEIGHT
        RH = rect[3] - rect[1]
        RW = rect[2] - rect[0]
        MAX_ROWS = RH // H
        days = [d['day'] for d in self.kplZTData]
        fromIdx, endIdx = findDrawDaysIndex(days, self.selectDay, MAX_ROWS * 2)
        for i in range(fromIdx, endIdx):
            kpl = self.kplZTData[i]
            if kpl['day'] == str(self.selectDay):
                win32gui.SetTextColor(hdc, 0x0000ff)
            else:
                win32gui.SetTextColor(hdc, 0xdddddd)
            day = kpl['day']
            day = day[2 : 4] + '-' + day[4 : 6] + '-' + day[6 : ]
            line = f"{day} {kpl['ztReason']}"
            idx = i - fromIdx
            y = (idx % MAX_ROWS) * H + 2
            x = RW // 2 if idx >= MAX_ROWS else 0
            win32gui.DrawText(hdc, line, len(line), (x + 2, y, x + RW // 2, y + H), win32con.DT_LEFT)
        pen = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xaaccaa)
        win32gui.SelectObject(hdc, pen)
        win32gui.MoveToEx(hdc, RW // 2, 0)
        win32gui.LineTo(hdc, RW // 2, rect[3])
        win32gui.DeleteObject(pen)

class SimpleWindow(CardWindow):
    def __init__(self) -> None:
        super().__init__((380, 230), (380, 30))
        self.curCode = None
        self.selectDay = 0
        self.zsCardView = None

    def createWindow(self, parentWnd):
        style = (0x00800000 | 0x10000000 | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION) & ~win32con.WS_SYSMENU
        w = win32api.GetSystemMetrics(0) # desktop width
        rect = (int(w / 3), 300, *self.MAX_SIZE)
        super().createWindow(parentWnd, rect, style, title='SimpleWindow')
        #win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        win32gui.ShowWindow(self.hwnd, win32con.SW_NORMAL)
        self.addCardView(SortCardView(self.hwnd))
        self.addCardView(HotCardView(self.hwnd))
        self.addCardView(KPLCardView(self.hwnd))
        self.zsCardView = ZSCardView(self.hwnd)

    def changeCardView(self):
        scode = f'{self.curCode :06d}' if type(self.curCode) == int else self.curCode
        if scode and scode[0 : 2] == '88':
            return
        super().changeCardView()

    def getCurCardView(self):
        scode = f'{self.curCode :06d}' if type(self.curCode) == int else self.curCode
        if scode and scode[0 : 2] == '88':
            return self.zsCardView
        return super().getCurCardView()

    def changeCode(self, code):
        if (self.curCode == code) or (not code):
            return
        self.curCode = code
        scode = f'{code :06d}' if type(code) == int else code
        if scode[0 : 2] == '88':
            self.zsCardView.updateCode(code)
        else:
            for cv in self.cardViews:
                cc =  getattr(cv, 'updateCode')
                if cc: cc(code)
        if self.hwnd:
            win32gui.InvalidateRect(self.hwnd, None, True)

    # param selDay yyyy-mm-dd or int 
    def changeSelectDay(self, selDay):
        if not selDay:
            selDay = 0
        if type(selDay) == str:
            selDay = selDay.replace('-', '')
            selDay = int(selDay)
        if self.selectDay == selDay:
            return
        self.selectDay = selDay
        for cv in self.cardViews:
            cc =  getattr(cv, 'updateSelectDay', None)
            if cc: cc(selDay)
        self.zsCardView.updateSelectDay(selDay)
        if self.hwnd:
            win32gui.InvalidateRect(self.hwnd, None, True)

    def hide(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
    
    def show(self):
        if not win32gui.IsWindowVisible(self.hwnd):
            win32gui.ShowWindow(self.hwnd, win32con.SW_NORMAL)

#----------------------------------------
class ListView(CardView):
    thread = None
    def __init__(self, hwnd):
        super().__init__(hwnd)
        self.ROW_HEIGHT = 18
        self.selIdx = -1
        self.pageIdx = 0
        self.data = None
        if not ListView.thread:
            ListView.thread = base_win.Thread()
            ListView.thread.start()

    def getColumnNum(self):
        return 1
    
    def getColumnWidth(self):
        n = self.getColumnNum()
        w = win32gui.GetClientRect(self.hwnd)[2]
        return w // n

    def getRowNum(self):
        rect = win32gui.GetClientRect(self.hwnd)
        h = rect[3] - rect[1]
        return h // self.ROW_HEIGHT
    
    def getPageSize(self):
        return self.getRowNum() * self.getColumnNum()

    def getMaxPageNum(self):
        if not self.data:
            return 0
        return (len(self.data) + self.getPageSize() - 1) // self.getPageSize()

    def getItemRect(self, idx):
        pz = self.getPageSize()
        idx -= self.pageIdx * pz
        if idx < 0 or idx >= pz:
            return None
        c = idx // self.getRowNum()
        cw = self.getColumnWidth()
        sx, ex = c * cw, (c + 1) * cw
        sy = (idx % self.getRowNum()) * self.ROW_HEIGHT
        ey = sy + self.ROW_HEIGHT
        return (sx, sy + 2, ex, ey + 2)

    def getItemIdx(self, x, y):
        c = x // self.getColumnWidth()
        r = y // self.ROW_HEIGHT
        idx = c * self.getRowNum() + r
        idx += self.getPageSize() * self.pageIdx
        return idx

    def getVisibleRange(self):
        pz = self.getPageSize()
        start = pz * self.pageIdx
        end = (self.pageIdx + 1) * pz
        start = min(start, len(self.data) - 1)
        end = min(end, len(self.data) - 1)
        return start, end

    def openTHSCode(self, code):
        topWnd = win32gui.GetParent(self.hwnd)
        win32gui.SetForegroundWindow(topWnd)
        if type(code) == int:
            code = f'{code :06d}'
        pyautogui.typewrite(code, interval=0.05)
        pyautogui.press('enter')
        #win32gui.SetActiveWindow(self.hwnd)
        self.thread.addTask('AW', self.activeWindow, None)
    
    def activeWindow(self):
        time.sleep(1)
        win32gui.SetForegroundWindow(self.hwnd)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_MOUSEWHEEL:
            wParam = (wParam >> 16) & 0xffff
            if wParam & 0x8000:
                wParam = wParam - 0xffff + 1
            if wParam > 0: # up
                self.pageIdx = max(self.pageIdx - 1, 0)
            else:
                self.pageIdx = min(self.pageIdx + 1, self.getMaxPageNum() - 1)
            win32gui.InvalidateRect(self.hwnd, None, True)
            return True
        if msg == win32con.WM_LBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.selIdx = self.getItemIdx(x, y)
            win32gui.InvalidateRect(self.hwnd, None, True)
            return True
        if msg == win32con.WM_LBUTTONDBLCLK:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            selIdx = self.getItemIdx(x, y)
            if not self.data or selIdx < 0 or selIdx >= len(self.data):
                return False
            code = self.data[selIdx]['code']
            self.openTHSCode(code)
            return True
        if msg == win32con.WM_KEYDOWN:
            if wParam == win32con.VK_DOWN:
                if self.data and self.selIdx < len(self.data):
                    self.selIdx += 1
                    if self.selIdx > 0 and self.selIdx % self.getPageSize() == 0:
                        self.pageIdx += 1
                    win32gui.InvalidateRect(hwnd, None, True)
            elif wParam == win32con.VK_UP:
                if self.data and self.selIdx > 0:
                    self.selIdx -= 1
                    if self.selIdx > 0 and (self.selIdx + 1) % self.getPageSize() == 0:
                        self.pageIdx -= 1
                    win32gui.InvalidateRect(hwnd, None, True)
            elif wParam == win32con.VK_RETURN:
                if self.data and self.selIdx >= 0:
                    code = self.data[self.selIdx]['code']
                    self.openTHSCode(code)
            return True
        return False

#-------------小窗口（全热度）----------------------------------------------
class HotZHCardView(ListView):
    def __init__(self, hwnd) -> None:
        super().__init__(hwnd)
        self.codeInfos = {}
        qr = orm.THS_Newest.select()
        for q in qr:
            self.codeInfos[q.code] = {'name': q.name}
        self.thread = base_win.Thread()
        self.thread.start()
        self.henxinUrl = henxin.HexinUrl()
        self.updateDataTime = 0

        self.curSelDay : int = 0
        self.maxHotDay : int = 0
        self.windowTitle = 'HotZH'

    def updateData(self, foreUpdate = False):
        lt = time.time()
        if not foreUpdate and lt - self.updateDataTime < 60:
            return
        self.updateDataTime = lt
        maxHotDay = orm.THS_Hot.select(pw.fn.max(orm.THS_Hot.day)).scalar()
        maxHotZhDay = orm.THS_HotZH.select(pw.fn.max(orm.THS_HotZH.day)).scalar()
        self.maxHotDay = maxHotDay
        if self.curSelDay == 0 or self.curSelDay == maxHotDay or self.curSelDay == maxHotZhDay:
            if maxHotDay == maxHotZhDay:
                qr = orm.THS_HotZH.select().where(orm.THS_HotZH.day == maxHotZhDay).order_by(orm.THS_HotZH.zhHotOrder.asc())
                self.data = [d.__data__ for d in qr]
            else:
                self.data = hot_utils.calcHotZHOnDay(maxHotDay)
        else:
            # is history 
            qr = orm.THS_HotZH.select().where(orm.THS_HotZH.day == self.curSelDay).order_by(orm.THS_HotZH.zhHotOrder.asc())
            self.data = [d.__data__ for d in qr]

    def loadCodeInfoNet(self, code):
        try:
            if type(code) == int:
                code = f'{code :06d}'
            data = self.codeInfos.get(code, None)
            if not data:
                self.codeInfos[code] = data = {}
            url = self.henxinUrl.getFenShiUrl(code)
            obj = self.henxinUrl.loadUrlData(url)
            data['name'] = obj['name']
            dts = obj['data'].split(';')
            if len(dts) != 0:
                dt = dts[-1].split(',')
                curPrice = float(dt[1])
                data['HX_curPrice'] = curPrice
                data['HX_prePrice'] = float(obj['pre'])
                pre = data['HX_prePrice']
                data['HX_zhangFu'] = (curPrice - pre) / pre * 100
                data['HX_updateTime'] = time.time()
            win32gui.InvalidateRect(self.hwnd, None, True)
        except Exception as e:
            print('[HotZHView.loadCodeInfoNet]', data, e)

    def loadCodeInfoNative(self, code, setNull):
        if type(code) == int:
            code = f'{code :06d}'
        data = self.codeInfos.get(code, None)
        if not data:
            self.codeInfos[code] = data = {}
            data['name'] = ''
        if setNull:
            if 'HX_curPrice_Native' in data:
                del data['HX_curPrice_Native']
            if 'HX_prePrice_Native' in data:
                del data['HX_prePrice_Native']
            if 'HX_zhangFu_Native' in data:
                del data['HX_zhangFu_Native']
            return
        dt = datafile.DataFile(code, datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL)
        idx = dt.getItemIdx(self.curSelDay)
        if idx <= 0:
            return
        pre = dt.data[idx - 1].close
        cur = dt.data[idx].close
        data['HX_curPrice_Native'] = cur / 100
        data['HX_prePrice_Native'] = pre / 100
        data['HX_zhangFu_Native'] = (cur - pre) / pre * 100
        win32gui.InvalidateRect(self.hwnd, None, True)

    def getCodeInfo(self, code):
        if type(code) == int:
            code = f'{code :06d}'
        data = self.codeInfos.get(code, None)
        if not data:
            data = self.codeInfos[code] = {}
        if ('HX_updateTime' not in data) or (time.time() - data['HX_updateTime'] > 120): # 120 seconds
            data['HX_updateTime'] = time.time()
            if self.curSelDay == 0 or self.curSelDay == self.maxHotDay:
                self.thread.addTask(code + '-Native', self.loadCodeInfoNative, (code, True))
                self.thread.addTask(code + '-Net', self.loadCodeInfoNet, (code, ))
            else:
                self.thread.addTask(code + '-Native', self.loadCodeInfoNative, (code, False))
                self.thread.addTask(code + '-Net', self.loadCodeInfoNet, (code, ))
            return data
        return data

    def drawItem(self, hdc, data, idx):
        rect = self.getItemRect(idx)
        if not rect:
            return
        code = f"{data['code'] :06d}"
        info = self.getCodeInfo(code)
        name = ''
        zf, nativeZF = '', ''
        if info:
            name = info.get('name', '')
            zf = info.get('HX_zhangFu', None)
            if zf != None:
                zf = f'{zf :.2f}% '
            nativeZF = info.get('HX_zhangFu_Native', None)
            if nativeZF != None:
                nativeZF = f'{nativeZF :.2f}% '
        txt = f"{data['zhHotOrder']:>3d} {name}"
        win32gui.SetTextColor(hdc, 0xdddddd)
        win32gui.DrawText(hdc, txt, len(txt), rect, win32con.DT_LEFT)
        if nativeZF:
            color = 0x00ff00 if  '-' in nativeZF else 0x0000ff
            win32gui.SetTextColor(hdc, color)
            rc2 = list(rect)
            rc2[2] = 145
            win32gui.DrawText(hdc, nativeZF, len(nativeZF), tuple(rc2), win32con.DT_RIGHT)
        if zf:
            color = 0x00ff00 if  '-' in zf else 0x0000ff
            win32gui.SetTextColor(hdc, color)
            win32gui.DrawText(hdc, zf, len(zf), rect, win32con.DT_RIGHT)
        if self.selIdx == idx:
            ps = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
            win32gui.SelectObject(hdc, ps)
            win32gui.MoveToEx(hdc, rect[0], rect[3] - 2)
            win32gui.LineTo(hdc, rect[2], rect[3] - 2)
            win32gui.DeleteObject(ps)

    def onDraw(self, hdc):
        self.updateData()
        if not self.data:
            return
        rect = win32gui.GetClientRect(self.hwnd)
        vr = self.getVisibleRange()
        for i in range(*vr):
            self.drawItem(hdc, self.data[i], i)

        for i in range(1, self.getColumnNum()):
            ps = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
            win32gui.SelectObject(hdc, ps)
            x = i * self.getColumnWidth()
            win32gui.MoveToEx(hdc, x, 0)
            win32gui.LineTo(hdc, x, rect[3])
            win32gui.DeleteObject(ps)

    def getWindowTitle(self):
        return self.windowTitle

    def onDayChanged(self, target, evtName, evtInfo):
        if evtName == 'DatePopupWindow.selDayChanged':
            selDay = evtInfo['curSelDay']
            if selDay > self.maxHotDay:
                return
            if self.curSelDay == selDay:
                return
            qr = orm.THS_Newest.select()
            self.codeInfos.clear()
            for q in qr:
                self.codeInfos[q.code] = {'name': q.name}
            self.curSelDay = selDay
            self.selIdx = -1
            self.pageIdx = 0
            if selDay == self.maxHotDay:
                self.windowTitle = f'HotZH'
                win32gui.SetWindowText(self.hwnd, self.windowTitle)
            else:
                tradeDays = hot_utils.getTradeDaysByHot()
                bef = 0
                for i in range(len(tradeDays) - 1, 0, -1):
                    if selDay < tradeDays[i]:
                        bef += 1
                    else:
                        break
                self.windowTitle = f'HotZH   {selDay}   {bef}天前'
                win32gui.SetWindowText(self.hwnd, self.windowTitle)
            self.updateData(True)
            win32gui.InvalidateRect(self.hwnd, None, True)

class KPL_AllCardView(ListView):
    def __init__(self, hwnd):
        super().__init__(hwnd)
        self.windowTitle = 'KPL-ZT'
        self.curSelDay = 0
        day = orm.KPL_ZT.select(pw.fn.max(orm.KPL_ZT.day)).scalar()
        self.updateData(day)

    def getFont(self):
        fnt = getattr(self, '_font', None)
        if not fnt:
            a = win32gui.LOGFONT()
            a.lfHeight = 12
            a.lfFaceName = '宋体'
            self._font = fnt = win32gui.CreateFontIndirect(a)
        return fnt

    def getWindowTitle(self):
        if not self.curSelDay:
            return 'KPL-ZT'
        tradeDays = hot_utils.getTradeDaysByHot()
        bef = 0
        for i in range(len(tradeDays) - 1, 0, -1):
            if self.curSelDay < tradeDays[i]:
                bef += 1
            else:
                break
        self.windowTitle = f'KPL-ZT   {self.curSelDay}   {bef}天前'
        return self.windowTitle
    
    def updateData(self, day):
        if day == self.curSelDay:
            return
        if not day:
            day = orm.KPL_ZT.select(pw.fn.max(orm.KPL_ZT.day)).scalar()
        if not day:
            day = '0000-00-00'
        if type(day) == int:
            day = str(day)
        if len(day) == 8:
            day = day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
        self.curSelDay = int(day.replace('-', ''))
        qr = orm.KPL_ZT.select().where(orm.KPL_ZT.day == day)
        self.data = [d.__data__ for d in qr]
        self.pageIdx = 0
        self.selIdx = -1
   
    def drawItem(self, hdc, data, idx):
        rect = self.getItemRect(idx)
        if not rect:
            return
        win32gui.SetTextColor(hdc, 0xdddddd)
        name = data['name']
        nl = 0
        for n in name:
            nl += 1 if ord(n) < 256 else 2
        if nl < 8:
            name += ' ' * (8 - nl)
        nl = 0
        status = data["status"]
        if '连' in status:
            status = status.replace('连', '') + ' '
        elif len(status) >= 4: # x天y板
            status = status[0 : -1]
        txt = f'{name} {data["ztTime"]} {status} {data["ztReason"]}'
        win32gui.SelectObject(hdc, self.getFont())
        win32gui.DrawText(hdc, txt, len(txt), rect, win32con.DT_LEFT)
        if self.selIdx == idx:
            ps = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
            win32gui.SelectObject(hdc, ps)
            win32gui.MoveToEx(hdc, rect[0], rect[3] - 2)
            win32gui.LineTo(hdc, rect[2], rect[3] - 2)
            win32gui.DeleteObject(ps)

    def onDraw(self, hdc):
        vr = self.getVisibleRange()
        if not vr:
            return
        for i in range(*vr):
            self.drawItem(hdc, self.data[i], i)

    def onDayChanged(self, target, evtName, evtInfo):
        selDay = evtInfo['curSelDay']
        if selDay == self.curSelDay:
            return
        self.updateData(selDay)
        win32gui.SetWindowText(self.hwnd, self.getWindowTitle())
        win32gui.InvalidateRect(self.hwnd, None, True)


class SimpleHotZHWindow(CardWindow):
    def __init__(self) -> None:
        super().__init__((220, 310), (220, 30))
        self.maxMode = True #  是否是最大化的窗口

    def createWindow(self, parentWnd):
        style = (0x00800000 | 0x10000000 | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION) & ~win32con.WS_SYSMENU
        w = win32api.GetSystemMetrics(0) # desktop width
        rect = (w - self.MAX_SIZE[0], 300, *self.MAX_SIZE)
        super().createWindow(parentWnd, rect, style, title='HotZH')
        #win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        win32gui.ShowWindow(self.hwnd, win32con.SW_NORMAL)
        self.addCardView(HotZHCardView(self.hwnd))
        self.addCardView(KPL_AllCardView(self.hwnd))

    def onDraw(self, hdc):
        super().onDraw(hdc)
        ps = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
        bk = win32gui.GetStockObject(win32con.NULL_BRUSH)
        size = self.getClientSize()
        win32gui.SelectObject(hdc, ps)
        win32gui.SelectObject(hdc, bk)
        win32gui.Rectangle(hdc, 0, 0, size[0] - 1, size[1] - 1)
        win32gui.DeleteObject(ps)
        #win32gui.DeleteObject(bk)

    def onDayChanged(self, args, evtName, evtInfo):
        cv = self.getCurCardView()
        dc = getattr(cv, 'onDayChanged', None)
        if not dc:
            return
        dc(args, evtName, evtInfo)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_CONTEXTMENU:
            if not getattr(self, 'DP', None):
                self.DP = base_win.DatePopupWindow()
                self.DP.createWindow(hwnd)
                self.DP.addListener(self.onDayChanged, 'DatePicker')
            rc = win32gui.GetWindowRect(hwnd)
            self.DP.show(x = rc[0] + 8, y = rc[1] + 30)
            return False
        return super().winProc(hwnd, msg, wParam, lParam)