import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os
import sys
import orm, hot_utils, base_win
import peewee as pw

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

    def getCodeInfo_THS(self, code):
        code = int(code)
        code = "%06d" % code
        gdInfo = orm.THS_GD.get_or_none(orm.THS_GD.code == code)
        jgccInfo = orm.THS_JGCC.get_or_none(orm.THS_JGCC.code == code)
        hydbInfo = orm.THS_HYDB_2.select().where(orm.THS_HYDB_2.code == code).order_by(orm.THS_HYDB_2.hy).execute()

        name = ''
        zb = ''
        if not jgccInfo:
            zb = '--'
            jgNum = '--'
        else:
            jgNum = jgccInfo.orgNum1
            name = jgccInfo.name
            if not jgccInfo.totalRate1:
                zb = '--'
            elif jgccInfo.totalRate1 < 1:
                zb = '<1'
            else:
                zb = int(jgccInfo.totalRate1)
        jg = "机构 %s家, 持仓%s%%" % (jgNum, zb)

        if gdInfo:
            jg += f'   前十流通股东{int(gdInfo.ltgdTop10Rate)}%'
            name = gdInfo.name

        hy = ''
        hyName = ''
        for m in hydbInfo:
            hy += f'  {m.hydj} {m.zhpm} / {m.hysl} [{self.getPMTag(m.zhpm / m.hysl)}]\n'
            hyName = m.hy
            name = m.name
        
        txt = hyName + '\n' + jg + '\n' + hy
        # 龙虎榜信息
        txt += self.getLhbInfo(code)
        
        return {'info': txt, 'code': code, 'name': name}

#-------------小窗口----------------------------------------------
class SimpleWindow(base_win.BaseWindow):
    DATA_TYPES = ('Sort', 'Hot')

    def __init__(self) -> None:
        super().__init__()
        self.size = None  # 窗口大小 (w, h)
        self.maxMode = True #  是否是最大化的窗口
        self.curCode = None
        self.sortData = None
        self.hotData = None
        self.query = ThsSortQuery()
        self.dataType = SimpleWindow.DATA_TYPES[0]
        self.selectDay = 0

    def createWindow(self, parentWnd):
        style = (0x00800000 | 0x10000000 | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION) & ~win32con.WS_SYSMENU
        w = win32api.GetSystemMetrics(0) # desktop width
        self.size = (360, 230)
        rect = (int(w / 3), 300, *self.size)
        #self.hwnd = win32gui.CreateWindowEx(win32con.WS_EX_TOOLWINDOW, 'STATIC', '', style, int(w / 3), 300, *self.size, parentWnd, None, None, None)
        #self.oldProc = win32gui.SetWindowLong(self.hwnd, win32con.GWL_WNDPROC, SimpleWindow._WinProc)
        #SimpleWindow.bindHwnds[self.hwnd] = self
        super().createWindow(parentWnd, rect, style, title='Hot-Simple-Window')
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        win32gui.ShowWindow(self.hwnd, win32con.SW_NORMAL)

    # param days (int): [YYYYMMDD, ....]
    # param selDay : int
    # return [startIdx, endIdx)
    def findDrawDaysIndex(self, days, selDay, maxNum):
        if not days:
            return (0, 0)
        if len(days) <= maxNum:
            return (0, len(days))
        if not selDay:
            return (len(days) - maxNum, len(days))
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

    def changeCode(self, code):
        if (self.curCode == code) or (not code):
            return
        self.curCode = code
        # load sort data
        self.sortData = self.query.getCodeInfo_THS(self.curCode)
        win32gui.SetWindowText(self.hwnd, f'{self.sortData["code"]} {self.sortData["name"]}')
        
        # load hot data
        qq = orm.THS_Hot.select(orm.THS_Hot.day, pw.fn.min(orm.THS_Hot.hotOrder).alias('minOrder'), pw.fn.max(orm.THS_Hot.hotOrder).alias('maxOrder')).where(orm.THS_Hot.code == self.curCode).group_by(orm.THS_Hot.day) #.order_by(orm.THS_Hot.day.desc())
        #print(qq.sql())
        self.hotData = [d for d in qq.dicts()]
        # 每日前10名的个数
        """qq = orm.THS_Hot.select(orm.THS_Hot.day, pw.fn.count().alias('_count')).where(orm.THS_Hot.code == self.curCode, orm.THS_Hot.hotOrder <= 10).group_by(orm.THS_Hot.day).order_by(orm.THS_Hot.day.desc())
        #print(qq.sql())
        qdata = {}
        for d in qq.tuples():
            qdata[d[0]] = d[1]
        for d in self.hotData:
            day = d['day']
            if day in qdata:
                d['count'] = qdata[day]
            else:
                d['count'] = 0
        """
        qq2 = orm.THS_HotZH.select(orm.THS_HotZH.day, orm.THS_HotZH.zhHotOrder, orm.THS_HotZH.avgHotOrder, orm.THS_HotZH.avgHotValue).where(orm.THS_HotZH.code == self.curCode)
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
                rd = hot_utils.calcHotZHOnDayCode(last['day'], self.curCode)
                if rd:
                    last['zhHotOrder'] = rd['zhHotOrder']
                    last['avgHotOrder'] = rd['avgHotOrder']
                    last['avgHotValue'] = rd['avgHotValue']
        
        if self.hwnd and self.size:
            #win32gui.InvalidateRect(self.wnd, (0, 0, *self.size), True)
            #win32gui.UpdateWindow(self.wnd)
            win32gui.InvalidateRect(self.hwnd, None, True)
            #win32gui.PostMessage(self.wnd, win32con.WM_PAINT)

    # param selDay yyyy-mm-dd or int 
    def changeSelectDay(self, selDay):
        if not selDay:
            selDay = 0
        if type(selDay) == str:
            selDay = selDay.replace('-', '')
            selDay = int(selDay)
        if self.selectDay != selDay:
            self.selectDay = selDay
            if self.hwnd and self.size:
                win32gui.InvalidateRect(self.hwnd, None, True)

    def changeDataType(self):
        idx = (self.DATA_TYPES.index(self.dataType) + 1) % len(self.DATA_TYPES)
        self.dataType = self.DATA_TYPES[idx]
        if self.hwnd and self.size:
            win32gui.InvalidateRect(self.hwnd, None, True)

    def draw(self, hdc):
        if self.dataType == 'Sort':
            self.drawSort(hdc)
        elif self.dataType == 'Hot':
            self.drawHot(hdc)
    
    def drawSort(self, hdc):
        if not self.sortData:
            return
        win32gui.SetTextColor(hdc, 0xdddddd)
        lines = self.sortData['info'].split('\n')
        for i, line in enumerate(lines):
            H = 18
            y = i * H + 2
            win32gui.DrawText(hdc, line, len(line), (2, y, self.size[0], y + H), 0)
    
    def drawHot(self, hdc):
        if not self.hotData:
            return
        win32gui.SetTextColor(hdc, 0xdddddd)
        H = 18
        rect = win32gui.GetClientRect(self.hwnd)
        RH = rect[3] - rect[1]
        RW = rect[2] - rect[0]
        MAX_ROWS = RH // H
        days = [d['day'] for d in self.hotData]
        fromIdx, endIdx = self.findDrawDaysIndex(days, self.selectDay, MAX_ROWS * 2)
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
            line = f"{day} {hot['minOrder'] :>3d}->{hot['maxOrder'] :<3d} {zhHotOrder} {avgHotVal :>3d}万"
            idx = i - fromIdx
            y = (idx % MAX_ROWS) * H + 2
            x = RW // 2 if idx >= MAX_ROWS else 0
            win32gui.DrawText(hdc, line, len(line), (x + 2, y, x + RW // 2, y + H), win32con.DT_LEFT)
        pen = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xaaccaa)
        win32gui.SelectObject(hdc, pen)
        win32gui.MoveToEx(hdc, RW // 2, 0)
        win32gui.LineTo(hdc, RW // 2, self.size[1])
        win32gui.DeleteObject(pen)

    def hide(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
    
    def show(self):
        if not win32gui.IsWindowVisible(self.hwnd):
            win32gui.ShowWindow(self.hwnd, win32con.SW_NORMAL)

    def winProc(self, hwnd, msg, wParam, lParam):
        if super().winProc(hwnd, msg, wParam, lParam):
            return True
        if msg == win32con.WM_RBUTTONUP or msg == win32con.WM_LBUTTONDBLCLK:
            self.changeDataType()
        return False
