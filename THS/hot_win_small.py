import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, threading
import sys
import orm, hot_utils, base_win, download.henxin as henxin
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
    DATA_TYPES = ('Sort', 'Hot', 'KPL_ZT')  # KPL_ZT 开盘啦涨停信息 

    def __init__(self) -> None:
        super().__init__()
        self.size = None  # 窗口大小 (w, h)
        self.maxMode = True #  是否是最大化的窗口
        self.curCode = None
        self.sortData = None
        self.kplZTData = None
        self.query = ThsSortQuery()
        self.dataType = SimpleWindow.DATA_TYPES[0]
        self.selectDay = 0
        self.hotDetailView = HotDetailView(self)

    def createWindow(self, parentWnd):
        style = (0x00800000 | 0x10000000 | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION) & ~win32con.WS_SYSMENU
        w = win32api.GetSystemMetrics(0) # desktop width
        self.size = (380, 230)
        rect = (int(w / 3), 300, *self.size)
        super().createWindow(parentWnd, rect, style, title='SimpleWindow')
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
        
        self.hotDetailView.changeCode(code)
        
        qq3 = orm.KPL_ZT_FuPan.select().where(orm.KPL_ZT_FuPan.code == self.curCode).order_by(orm.KPL_ZT_FuPan.day.asc())
        def fmtDay(d): 
            d['day'] = d['day'].replace('-', '')
            return d
        self.kplZTData = [fmtDay(d) for d in qq3.dicts()]

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
            self.hotDetailView.draw(hdc)
        elif self.dataType == 'KPL_ZT':
            self.drawKPL_ZT(hdc)

    def drawSort(self, hdc):
        if not self.sortData:
            return
        win32gui.SetTextColor(hdc, 0xdddddd)
        lines = self.sortData['info'].split('\n')
        for i, line in enumerate(lines):
            H = 18
            y = i * H + 2
            win32gui.DrawText(hdc, line, len(line), (2, y, self.size[0], y + H), 0)

    def drawKPL_ZT(self, hdc):
        win32gui.SetTextColor(hdc, 0xdddddd)
        rect = win32gui.GetClientRect(self.hwnd)
        if not self.kplZTData:
            line = '无开盘啦涨停信息'
            win32gui.DrawText(hdc, line, len(line), rect, win32con.DT_CENTER)
            return
        
        H = 18
        RH = rect[3] - rect[1]
        RW = rect[2] - rect[0]
        MAX_ROWS = RH // H
        days = [d['day'] for d in self.kplZTData]
        fromIdx, endIdx = self.findDrawDaysIndex(days, self.selectDay, MAX_ROWS * 2)
        for i in range(fromIdx, endIdx):
            kpl = self.kplZTData[i]
            if kpl['day'] == str(self.selectDay):
                win32gui.SetTextColor(hdc, 0x0000ff)
            else:
                win32gui.SetTextColor(hdc, 0xdddddd)
            day = kpl['day'][4 : ]
            line = f"{day[0:2]}.{day[2:4]} {kpl['ztReason']}"
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
        if msg == win32con.WM_RBUTTONUP:
            self.changeDataType()
            return True
        if self.dataType == 'Hot':
            return self.hotDetailView.winProc(hwnd, msg, wParam, lParam)
        return False

class Thread:
    def __init__(self) -> None:
        self.tasks = []
        self.stoped = False
        self.thread = threading.Thread(target = Thread._run, args=(self,))

    def addTask(self, _type, fun, args):
        for tk in self.tasks:
            if tk[2] == _type:
                return
        self.tasks.append((fun, args, _type))

    def start(self):
        self.thread.start()

    def stop(self):
        self.stoped = True
    
    @staticmethod
    def _run(self):
        while not self.stoped:
            if len(self.tasks) > 0:
                task = self.tasks[0]
                fun, args, *_ = task
                fun(*args)
                self.tasks.pop(0)
            else:
                time.sleep(1)

class HotDetailView:
    ROW_HEIGHT = 18

    def __init__(self, simpleWin):
        self.simpleWin = simpleWin
        self.hotData = None
        self.rectInfo = [None] * 50
        self.tipRect = None
        self.tipObj = None
        self.tipOrgRect = None
        self.showStartIdx = 0

    def draw(self, hdc):
        rr = win32gui.GetClientRect(self.simpleWin.hwnd)
        win32gui.SetTextColor(hdc, 0xdddddd)
        H = 18
        rect = win32gui.GetClientRect(self.simpleWin.hwnd)
        RH = rect[3] - rect[1]
        RW = rect[2] - rect[0]
        MAX_ROWS = RH // H
        days = [d['day'] for d in self.hotData]
        fromIdx, endIdx = self.simpleWin.findDrawDaysIndex(days, self.simpleWin.selectDay, MAX_ROWS * 2)
        for i in range(fromIdx, endIdx):
            hot = self.hotData[i]
            if hot['day'] == self.simpleWin.selectDay:
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
            self.rectInfo[i - fromIdx] = {'data': hot, 'rect': rect}
        pen = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xaaccaa)
        win32gui.SelectObject(hdc, pen)
        win32gui.MoveToEx(hdc, RW // 2, 0)
        win32gui.LineTo(hdc, RW // 2, rr[3])
        self.drawTip(hdc)
        win32gui.DeleteObject(pen)

    def drawTip(self, hdc):
        if (not self.tipObj) or (not self.tipRect):
            return
        hotDetail = self.tipObj.get('detail', None)
        if not hotDetail:
            return
        bk = win32gui.CreateSolidBrush(0)
        ps = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
        win32gui.SelectObject(hdc, ps)
        win32gui.SelectObject(hdc, bk)
        win32gui.Rectangle(hdc, *self.tipRect)
        si1 = max(self.showStartIdx, 0)
        si2 = max(0, len(hotDetail) - 5)
        si = min(si1, si2)
        self.showStartIdx = si
        win32gui.SetTextColor(hdc, 0x3333CD)
        for i in range(si, len(hotDetail)):
            hot = hotDetail[i]
            txt = f" {hot['time'] // 100 :02d}:{hot['time'] % 100 :02d}  {hot['hotValue'] :>3d}万  {hot['hotOrder'] :>3d}"
            y = (i - si) * self.ROW_HEIGHT + 5
            rc = (self.tipRect[0], y, self.tipRect[2], y + self.ROW_HEIGHT)
            win32gui.DrawText(hdc, txt, len(txt), rc, win32con.DT_CENTER)
        rc = self.tipOrgRect
        win32gui.MoveToEx(hdc, rc[0], rc[3] - 2)
        win32gui.LineTo(hdc, rc[2], rc[3] - 2)
        win32gui.DeleteObject(bk)
        win32gui.DeleteObject(ps)

    def changeCode(self, code):
        self.showStartIdx = 0
        self.tipObj = None
        self.tipRect = None
        self.tipOrgRect = None
        self.code = code if type(code) == int else int(code)
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
            if self.isInRect(x, y, self.tipRect):
                self.tipObj = None
                self.tipRect = None
                win32gui.InvalidateRect(hwnd, None, True)
                return True
            for ri in self.rectInfo:
                if ri and self.isInRect(x, y, ri['rect']):
                    self.setTip(ri)
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
    
    def setTip(self, ri):
        self.tipObj = ri['data']
        self.tipOrgRect = ri['rect']
        rr = win32gui.GetClientRect(self.simpleWin.hwnd)
        w, h = rr[2], rr[3]
        if (ri['rect'][0] + ri['rect'][2]) >= w:
            self.tipRect = (0, 0, w // 2, h)
        else:
            self.tipRect = (w // 2, 0, w, h)
        if 'detail' not in self.tipObj:
            info = orm.THS_Hot.select().where(orm.THS_Hot.code == self.code, orm.THS_Hot.day == self.tipObj['day'])
            self.tipObj['detail'] = [d.__data__ for d in info]


#-------------小窗口（全热度）----------------------------------------------
class HotZHView:
    ROW_HEIGHT = 18

    def __init__(self, hwnd) -> None:
        self.hwnd = hwnd
        self.data = None
        self.pageIdx = 0
        self.codeInfos = {}
        qr = orm.THS_Newest.select()
        for q in qr:
            self.codeInfos[q.code] = {'name': q.name}
        self.thread = Thread()
        self.thread.start()
        self.henxinUrl = henxin.HexinUrl()
        self.selIdx = -1

    def uploadData(self):
        maxHotDay = orm.THS_Hot.select(pw.fn.max(orm.THS_Hot.day)).scalar()
        maxHotZhDay = orm.THS_HotZH.select(pw.fn.max(orm.THS_HotZH.day)).scalar()
        if maxHotDay == maxHotZhDay:
            qr = orm.THS_HotZH.select().where(orm.THS_HotZH.day == maxHotZhDay).order_by(orm.THS_HotZH.zhHotOrder.asc())
            self.data = [d.__data__ for d in qr]
        else:
            self.data = hot_utils.calcHotZHOnDay(maxHotDay)

    def loadCodeInfo(self, code):
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
                curTime = int(dt[0])
                curPrice = float(dt[1])
                data['HX_curTime'] = curTime
                data['HX_curPrice'] = curPrice
                data['HX_prePrice'] = float(obj['pre'])
                pre = data['HX_prePrice']
                data['HX_zhangFu'] = (curPrice - pre) / pre * 100
            else:
                now = datetime.datetime.now()
                data['HX_curTime'] = now.hour * 100 + now.minute
            win32gui.InvalidateRect(self.hwnd, None, True)
        except Exception as e:
            print('[HotZHView.loadCodeInfo]', data, e)

    def getCodeInfo(self, code):
        if type(code) == int:
            code = f'{code :06d}'
        data = self.codeInfos.get(code, None)
        if not data or 'HX_curTime' not in data:
            self.thread.addTask(code, self.loadCodeInfo, (code, ))
            return data
        ct = data['HX_curTime']
        ds = datetime.datetime.now()
        ct2 = ds.hour * 100 + ds.minute
        if ct2 < ct:
            self.thread.addTask(code, self.loadCodeInfo, (code, ))
            return data
        if ct2 - ct >= 2: # 2分钟
            self.thread.addTask(code, self.loadCodeInfo, (code, ))
            return data
        return data
    
    def getColumnNum(self):
        rect = win32gui.GetClientRect(self.hwnd)
        return max(rect[2] // 200, 1)
    
    def getColumnWidth(self):
        n = self.getColumnNum()
        w = win32gui.GetClientRect(self.hwnd)[2]
        return w // n

    def getRowNum(self):
        rect = win32gui.GetClientRect(self.hwnd)
        h = rect[3] - rect[1]
        return h // HotZHView.ROW_HEIGHT
    
    def getPageSize(self):
        return self.getRowNum() * self.getColumnNum()

    def getMaxPageNum(self):
        if not self.data:
            return 0
        return (len(self.data) + self.getPageSize() - 1) // self.getPageSize()

    def getItemRect(self, showIdx):
        pz = self.getPageSize()
        if showIdx < 0 or showIdx >= pz:
            return None
        c = showIdx // self.getRowNum()
        cw = self.getColumnWidth()
        sx, ex = c * cw, (c + 1) * cw
        sy = (showIdx % self.getRowNum()) * self.ROW_HEIGHT
        ey = sy + self.ROW_HEIGHT
        return (sx, sy + 2, ex, ey + 2)

    def getItemIdx(self, x, y):
        c = x // self.getColumnWidth()
        r = y // self.ROW_HEIGHT
        idx = c * self.getRowNum() + r
        idx += self.getPageSize() * self.pageIdx
        return idx

    def drawItem(self, hdc, data, idx, idx2):
        rect = self.getItemRect(idx)
        code = f"{data['code'] :06d}"
        info = self.getCodeInfo(code)
        name = ''
        zf = ''
        if info:
            name = info.get('name', '')
            zf = info.get('HX_zhangFu', None)
            if zf != None:
                zf = f'{zf :.2f}% '
        txt = f"{data['zhHotOrder']:>3d} {code} {name}"
        win32gui.SetTextColor(hdc, 0xdddddd)
        win32gui.DrawText(hdc, txt, len(txt), rect, win32con.DT_LEFT)
        if zf:
            color = 0x00ff00 if  '-' in zf else 0x0000ff
            win32gui.SetTextColor(hdc, color)
            win32gui.DrawText(hdc, zf, len(zf), rect, win32con.DT_RIGHT)
        if self.selIdx == idx2:
            ps = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
            win32gui.SelectObject(hdc, ps)
            win32gui.MoveToEx(hdc, rect[0], rect[3] - 2)
            win32gui.LineTo(hdc, rect[2], rect[3] - 2)
            win32gui.DeleteObject(ps)

    def draw(self, hdc):
        self.uploadData()
        if not self.data:
            return
        rect = win32gui.GetClientRect(self.hwnd)
        vr = self.getVisibleRange()
        for i in range(*vr):
            self.drawItem(hdc, self.data[i], i - vr[0], i)

        for i in range(1, self.getColumnNum()):
            ps = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
            win32gui.SelectObject(hdc, ps)
            x = i * self.getColumnWidth()
            win32gui.MoveToEx(hdc, x, 0)
            win32gui.LineTo(hdc, x, rect[3])
            win32gui.DeleteObject(ps)

    def getVisibleRange(self):
        pz = self.getPageSize()
        start = pz * self.pageIdx
        end = (self.pageIdx + 1) * pz
        start = min(start, len(self.data) - 1)
        end = min(end, len(self.data) - 1)
        return start, end
    
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
        return False

class SimpleHotZHWindow(base_win.BaseWindow):
    MAX_SIZE = (220, 310)
    MIN_SIZE = (220, 60)
    TITLE_HEIGHT = 30

    def __init__(self) -> None:
        super().__init__()
        self.maxMode = True #  是否是最大化的窗口
        self.hotZHView = None

    def createWindow(self, parentWnd):
        style = (0x00800000 | 0x10000000 | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION) & ~win32con.WS_SYSMENU
        w = win32api.GetSystemMetrics(0) # desktop width
        rect = (w - self.MAX_SIZE[0], 300, *self.MAX_SIZE)
        super().createWindow(parentWnd, rect, style, title='HotZH')
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        win32gui.ShowWindow(self.hwnd, win32con.SW_NORMAL)
        self.hotZHView = HotZHView(self.hwnd)

    def draw(self, hdc):
        ps = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
        bk = win32gui.CreateSolidBrush(0x00)
        rect = self.getRect()
        win32gui.SelectObject(hdc, ps)
        win32gui.SelectObject(hdc, bk)
        win32gui.Rectangle(hdc, 0, 0, rect[2] - 1, rect[3] - 1)
        if self.maxMode:
            self.hotZHView.draw(hdc)
        win32gui.DeleteObject(ps)
        win32gui.DeleteObject(bk)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDBLCLK:
            self.maxMode = not self.maxMode
            if self.maxMode:
                win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, *self.MAX_SIZE, win32con.SWP_NOMOVE)
            else:
                win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, *self.MIN_SIZE, win32con.SWP_NOMOVE)
            return True
        if self.maxMode and self.hotZHView:
            if self.hotZHView.winProc(hwnd, msg, wParam, lParam):
                return True
        return super().winProc(hwnd, msg, wParam, lParam)
