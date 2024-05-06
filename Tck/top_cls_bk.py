import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, json
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr, cls
from THS import orm as ths_orm, ths_win, hot_utils
from Common import base_win, timeline, kline, table
import ddlr_detail, orm as tck_orm, kline_utils, cache

# code = 'cls00000'
def loadBkInfo(code : str):
    if not code:
        return None
    rs = {}
    if 'cls' not in code:
        code = 'cls' + code
    code = code.strip()
    if len(code) != 8:
        return None
    curl = cls.ClsUrl()
    url = 'https://x-quote.cls.cn/web_quote/plate/info?' + curl.signParams(f'app=CailianpressWeb&os=web&secu_code={code}&sv=7.7.5')
    resp = requests.get(url)
    txt = resp.content.decode('utf-8')
    js = json.loads(txt)
    basic = js['data']
    rs['basic'] = basic

    url = 'https://x-quote.cls.cn/web_quote/plate/stocks?' + curl.signParams(f'app=CailianpressWeb&os=web&rever=1&secu_code={code}&sv=7.7.5&way=last_px')
    resp = requests.get(url)
    txt = resp.content.decode('utf-8')
    js = json.loads(txt)
    codes = js['data']['stocks']
    rs['codes'] = codes
    codesMap = {}
    for c in codes:
        codesMap[c['secu_code']] = c

    rs['industry'] = None
    rs['industry_codes'] = []
    if basic['has_industry']:
        url = 'https://x-quote.cls.cn/web_quote/plate/industry?' + curl.signParams(f'app=CailianpressWeb&os=web&rever=1&secu_code={code}&sv=7.7.5&way=last_px')
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        industry = js['data']
        rs['industry'] = industry # [ {industry_name': '空域管理', 'stocks' = []}, .... ]
        rs['industry_codes'] = ic = []
        for i, rds in enumerate(industry):
            for cc in rds['stocks']:
                cc['_industry_name'] = rds['industry_name']
                cc['_industry_idx'] = i
                cc['_industry_num'] = len(industry)
                ic.append(cc)
                cp = codesMap.get(cc['secu_code'], None)
                if cp:
                    cp['_industry_name'] = rds['industry_name']
    return rs

class CodesTableModel:
    GREEN = 0xA3C252
    RED = 0x2204de
    
    def __init__(self, bkInfo) -> None:
        self.headers = [{'name': '#idx', 'width': 40, 'title': ''},
                        {'name': 'secu_name', 'title': '名称', 'width' : 80},
                        {'name': 'zhHotOrder', 'title': '热度',  'width':80, 'sortable' :True, 'sorter': self.sortZhHot},
                        {'name': 'change', 'title': '涨幅', 'width': 80, 'sortable' :True, 'render': cache.renderZF, 'sorter': self.sorter},
                        {'name': 'head_num', 'title': '领涨', 'width': 50, 'sortable' :True, 'sorter': self.sorter },
                        {'name': 'cmc', 'title': '流通市值', 'width': 80, 'sortable' :True , 'render': self.renderZJ, 'sorter': self.sorter},
                        {'name': 'is_core', 'title': '核心', 'width': 50, 'sortable' :True , 'render': self.renderCore, 'sorter': self.sorter},
                        {'name': 'fundflow', 'title': '资金', 'width': 80, 'sortable' :True , 'render': self.renderZJ, 'sorter': self.sorter},
                        {'name': '_industry_name', 'title': '产业链', 'width': 120},
                        {'name': 'secu_code', 'title': '分时图', 'width': 250, 'render': cache.renderTimeline},
                        {'name': 'assoc_desc', 'title': '简介', 'width': 0, 'stretch' : 1, 'fontSize': 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER}
                        ]
        self.bkInfo = bkInfo or {'basic': None, 'codes': [], 'industry_codes': []}
        self.mode = None
        
    def sortZhHot(self, colName, val, rowData, allDatas, asc):
        if val == None:
            return 10000
        return val

    def sorter(self, colName, val, rowData, allDatas, asc):
        if self.mode == 'codes':
            return val
        if asc:
            idx = rowData['_industry_idx'] * 100000000000
        else:
            idx = (rowData['_industry_num'] - rowData['_industry_idx']) * 100000000000
        return idx + val

    def _getHeader(self, colName):
        for c in self.headers:
            if c['name'] == colName:
                return c
        return None
    
    def _loadHotZH(self, datas):
        hots = hot_utils.calcHotZHOnLastDay()
        mhots = {}
        for d in hots:
            code = f'{d["code"] :06d}'
            mhots[code] = d['zhHotOrder']
        for d in datas:
            code = d['secu_code'][2 : ]
            d['zhHotOrder'] = mhots.get(code, None)

    # codes or industry mode
    def setMode(self, tabWin, mode):
        self.mode = mode
        tabWin.headers = self.headers
        industry_name = self._getHeader('_industry_name')
        if mode == 'codes':
            data = self.bkInfo['codes']
            industry_name['sortable'] = True
        else:
            data = self.bkInfo['industry_codes']
            industry_name['sortable'] = False
        self._loadHotZH(data)
        tabWin.setData(data)
        tabWin.invalidWindow()
    
    def renderZJ(self, win : base_win.TableWindow, hdc, row, col, colName, value, rowData, rect):
        if value == None:
            return
        value /= 100000000
        color = 0x00
        if colName == 'fundflow':
            if value > 0: color = self.RED
            elif value < 0: color = self.GREEN
            value = f'{value :.2f} 亿'
        else:
            value = f'{int(value)} 亿'
        win.drawer.drawText(hdc, value, rect, color, win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

    def renderCore(self, win : base_win.TableWindow, hdc, row, col, colName, value, rowData, rect):
        value = '是' if value == 1 else '否'
        win.drawer.drawText(hdc, value, rect, 0x0, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

class ClsBkWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, '1fr')
        self.cols = ('1fr', )
        self.layout = base_win.GridLayout(rows, self.cols, (5, 10))
        self.tableWin = table.EditTableWindow()
        self.tableWin.css['selBgColor'] = 0xEAD6D6
        self.editorWin = base_win.Editor()
        self.editorWin.placeHolder = '板块概念代码'
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.industryCheckBox = base_win.CheckBox({'title': '仅显示产业链'})
        self.clsData = None
        self.searchText = ''
        self.model = None
        
        #base_win.ThreadPool.addTask('CLS_BK', self.runTask)
    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)

        flowLayout = base_win.FlowLayout(lineHeight = 30)
        self.checkBox.createWindow(self.hwnd, (0, 0, 150, 25))
        flowLayout.addContent(self.checkBox)
        self.editorWin.createWindow(self.hwnd, (0, 0, 200, 25))
        flowLayout.addContent(self.editorWin)
        self.industryCheckBox.createWindow(self.hwnd, (0, 0, 150, 25))
        flowLayout.addContent(self.industryCheckBox)
        self.industryCheckBox.addNamedListener('Checked', self.industryChecked)

        self.tableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.rowHeight = 50

        self.layout.setContent(0, 0, flowLayout)
        self.layout.setContent(1, 0, self.tableWin, {'horExpand': -1})
        def onPressEnter(evt, args):
            q = evt.text.strip()
            self.onQuery(q)
        self.editorWin.addNamedListener('PressEnter', onPressEnter, None)
        self.editorWin.addNamedListener('DbClick', self.onDbClickEditor, None)
        self.tableWin.addListener(self.onDbClickTable)
        #self.tableWin.addListener(self.onEditCell, None)

    def onDbClickTable(self, evt, args):
        if evt.name != 'RowEnter' and evt.name != 'DbClick':
            return
        data = evt.data
        if not data:
            return
        rdata = {'code': data['secu_code'][2 : ], 'day': None}
        if self.checkBox.isChecked():
            kline_utils.openInThsWindow(rdata)
        else:
            kline_utils.openInCurWindow_Code(self, rdata)

    def onQuery(self, text):
        text = text.strip()
        self.tableWin.setData(None)
        self.tableWin.invalidWindow()
        if not text or (len(text) != 5 and len(text) != 8):
            return
        self.updateBk(text)

    def onDbClickEditor(self, evt, args):
        model = [
            {'title': '高速连接器', 'value': 'cls82502'},
            {'title': '固态电池', 'value': 'cls81936'},
            {'title': '证券', 'value': 'cls81985'},
            {'title': '低空经济', 'value': 'cls82437'},
            {'title': '有色金属概念', 'value': 'cls82406'},
        ]
        def onSelMenu(evt, args):
            self.editorWin.setText(evt.item['title'] + '(' + evt.item['value'] + ')')
            self.editorWin.invalidWindow()
            self.onQuery(evt.item['value'])
        menu = base_win.PopupMenuHelper.create(self.editorWin.hwnd, model)
        menu.addNamedListener('Select', onSelMenu)
        menu.show()

    def industryChecked(self, evt, args):
        if not self.model:
            return
        if evt.info['checked']:
            self.model.setMode(self.tableWin, 'industry')
        else:
            self.model.setMode(self.tableWin, 'codes')

    def updateBk(self, bkCode):
        bkInfo = loadBkInfo(bkCode)
        ccs = []
        for c in bkInfo['codes']:
            if '000099' in c['secu_code']:
                ccs.append(c)
        #bkInfo['codes'] = ccs
        self.model = CodesTableModel(bkInfo)
        if self.industryCheckBox.isChecked():
            self.model.setMode(self.tableWin, 'industry')
        else:
            self.model.setMode(self.tableWin, 'codes')

class ClsBkZS:
    def __init__(self) -> None:
        self.codes = []

    # codes = '600000' or 600000
    #         ['600000', ...]
    #         [600000, ...]
    #         [ {'code': '600000', }, ....]
    #         [ {'secu_code': '600000', }, ....]
    def addCodes(self, codes):
        if not codes:
            return
        if type(codes) == str:
            self.codes.append(codes)
        elif type(codes) == int:
            self.codes.append(f'{codes :06d}')
        elif type(codes) == list:
            item = codes[0]
            if type(item) == int:
                self.codes.extend([f'{d: 06d}' for d in codes])
            if type(item) == str:
                self.codes.extend(codes)
            elif 'code' in item:
                self.codes.extend([d['code'] for d in codes])
            elif 'secu_code' in item:
                self.codes.extend([d['secu_code'] for d in codes])
    
    def buildZS(self, fromDay : int):
        days = set()
        for i in range(0, min(3, len(self.codes))):
            cx = self.codes[i]
            df = datafile.DataFile(cx, datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL)
            for d in df.data:
                if d.day not in days:
                    days.add(d)
        days = list(days)
        days.sort()
        dfs = [datafile.DataFile(cx, datafile.DataFile.DT_MINLINE, datafile.DataFile.FLAG_ALL) for cx in self.codes]
        for i in range(len(days)):
            if fromDay <= days[i]:
                fromDay = days[i]
            else:
                break
        fromIdx = days.index(fromDay)
        basePrice = self._calcZSBase(dfs, fromDay)
        dayItems = []
        fsItems = []
        for i in range(fromIdx, len(days)):
            di, fs = self._calcOneDay(dfs, days[i], basePrice)
            dayItems.append(di)
            fsItems.extend(fs)
        return dayItems, fsItems

    def save(self, dayItems, fsItems):
        pass

    def _calcZSBase(self, dfs, fromDay):
        ddfs = []
        for df in dfs:
            idx = df.getItemIdx(fromDay)
            if idx < 240 * 5: # 忽略上市5天内的股
                continue
            idx -= 1
            da = df.data[idx]
            ddfs.append(da)
        base = self._calcZSPrice(ddfs, 'close')
        return base

    def _calcZSPrice(self, datas, name):
        p  = 0
        for d in datas:
            p += getattr(d, name)
        if name in ('open', 'close', 'low', 'high'):
            p /= len(datas)
        return p

    def _calcOneDay(self, dfs, day, basePrice):
        fsDatas = []
        datas = []
        ONE_DAY_ITEM_NUM = 240
        for df in dfs:
            idx = df.getItemIdx(day)
            if idx < 240 * 5: # 忽略上市5天内的股
                continue
            datas.append(df.data[idx : idx + ONE_DAY_ITEM_NUM])

        for ms in range(ONE_DAY_ITEM_NUM):
            ds = []
            it = datafile.ItemData()
            fsDatas.append(it)
            for d in datas:
                ds.append(d[ms])
            it.day = day
            it.time = ds[0].time
            it.open = self._calcZSPrice(ds, 'open') / basePrice * 1000
            it.close = self._calcZSPrice(ds, 'close') / basePrice * 1000
            it.low = min(it.open, it.close)
            it.high = max(it.open, it.close)
            it.amount = self._calcZSPrice(ds, 'amount')
            it.vol = self._calcZSPrice(ds, 'vol')
        cur = datafile.ItemData()
        cur.day = day
        cur.open = fsDatas[0].open
        cur.close = fsDatas[-1].close
        cur.low = cur.high = 0
        cur.amount = cur.vol = 0
        for fs in fsDatas:
            if cur.low == 0:
                cur.low = fs.low
                cur.high = fs.high
            else:
                cur.low = min(fs.low, cur.low)
                cur.high = max(fs.high, cur.high)
            cur.amount += fs.amount
            cur.vol += fs.vol
        cur.amount = cur.amount // 100000000 #亿元
        cur.vol = cur.vol // 100000000 # 亿股
        return cur, fsDatas
            
if __name__ == '__main__':
    win = ClsBkWindow()
    win.createWindow(None, (100, 100, 1200, 600), win32con.WS_OVERLAPPEDWINDOW  | win32con.WS_VISIBLE)
    #win.updateBk('cls82437')
    win.layout.resize(0, 0, *win.getClientSize())
    win32gui.PumpMessages()
