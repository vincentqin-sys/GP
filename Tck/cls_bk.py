import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, json
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile
from Download import henxin, ths_ddlr, cls
from THS import orm as ths_orm, ths_win
from Common import base_win, timeline, kline, table
import ddlr_detail, orm, kline_utils

base_win.ThreadPool.start()

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
                ic.append(cc)
                cp = codesMap.get(cc['secu_code'], None)
                if cp:
                    cp['_industry_name'] = rds['industry_name']
    return rs

class CacheManager:
    def __init__(self) -> None:
        self.cache = {}
        self.win = None

    def _needUpdate(self, data):
        now = datetime.datetime.now()
        cc : datetime.datetime = data['_load_time']
        scc = cc.strftime('%H:%M')
        if scc > '15:00':
            return False
        delta : datetime.timedelta = now - cc
        if delta.seconds >= 180:
            return True
        return False

    def getData(self, code):
        if type(code) == int:
            code = f'{code :05d}'
        if code not in self.cache:
            self.download(code)
            return None
        data = self.cache[code]
        if self._needUpdate(data):
            self.cache.pop(code)
            self.download(code)
            return None
        return data
    
    def download(self, code):
        base_win.ThreadPool.addTask(code, self._download, code)

    def _download(self, code):
        hx = henxin.HexinUrl()
        ds = hx.loadUrlData( hx.getFenShiUrl(code) )
        ds['code'] = code
        render = TimelineRender()
        render.setData(ds)
        rs = {'_load_time': datetime.datetime.now(), 'render': render}
        self.cache[code] = rs
        self.win.invalidWindow()

_cache = CacheManager()

class CodesTableModel:
    GREEN = 0xA3C252
    RED = 0x2204de
    def __init__(self, bkInfo) -> None:
        self.headers = [{'name': '#idx', 'width': 40, 'title': ''},
                        {'name': 'secu_name', 'title': '名称', 'width' : 80},
                        #{'name': 'last_px', 'title': '最新价',  'width':80, 'sortable' :True, 'render': self.renderPrice},
                        {'name': 'change', 'title': '涨幅', 'width': 80, 'sortable' :True, 'render': self.cellChange, 'sorter': self.sorter},
                        {'name': 'head_num', 'title': '领涨', 'width': 50, 'sortable' :True, 'sorter': self.sorter },
                        {'name': 'cmc', 'title': '流通市值', 'width': 80, 'sortable' :True , 'render': self.renderZJ, 'sorter': self.sorter},
                        {'name': 'is_core', 'title': '核心', 'width': 50, 'sortable' :True , 'render': self.renderCore, 'sorter': self.sorter},
                        {'name': 'fundflow', 'title': '资金', 'width': 80, 'sortable' :True , 'render': self.renderZJ, 'sorter': self.sorter},
                        {'name': '_industry_name', 'title': '产业链', 'width': 120},
                        {'name': 'secu_code', 'title': '分时图', 'width': 250, 'render': self.renderTimeline},
                        {'name': 'assoc_desc', 'title': '简介', 'width': 0, 'stretch' : 1, 'fontSize': 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER}
                        ]
        self.bkInfo = bkInfo or {'basic': None, 'codes': [], 'industry_codes': []}
        self.mode = None

    def sorter(self, colName, val, rowData, allDatas, asc):
        if self.mode == 'codes':
            return val
        idx = rowData['_industry_idx'] * 100000000000
        return idx + val

    def _getHeader(self, colName):
        for c in self.headers:
            if c['name'] == colName:
                return c
        return None

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
        tabWin.setData(data)
        tabWin.invalidWindow()
    
    def renderTimeline(self, win : base_win.TableWindow, hdc, row, col, colName, value, rowData, rect):
        global _cache
        code = rowData['secu_code'][2 : ]
        data = _cache.getData(code)
        if not data:
            return
        data['render'].onDraw(hdc, win.drawer, rect)

    def renderPrice(self, win : base_win.TableWindow, hdc, row, col, colName, value, rowData, rect):
        if value == None:
            return
        zd = rowData['change']
        color = 0x00
        if zd > 0: color = self.RED
        elif zd < 0: color = self.GREEN
        win.drawer.drawText(hdc, f'{value :.2f}', rect, color, win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

    def cellChange(self, win : base_win.TableWindow, hdc, row, col, colName, value, rowData, rect):
        if value == None:
            return
        color = 0x00
        if value > 0: color = self.RED
        elif value < 0: color = self.GREEN
        value *= 100
        win.drawer.drawText(hdc, f'{value :.2f} %', rect, color, win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
    
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
        self.tableWin.enableListeners['ContextMenu'] = True
        self.editorWin = base_win.Editor()
        self.editorWin.placeHolder = '板块概念代码'
        self.editorWin.enableListeners['DbClick'] = True
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.industryCheckBox = base_win.CheckBox({'title': '仅显示产业链'})
        self.clsData = None
        self.searchText = ''
        self.model = None
        global _cache
        _cache.win = self.tableWin
        
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
            {'title': '低空经济', 'value': 'cls82437'},
            {'title': '有色金属概念', 'value': 'cls82406'},
            {'title': '家电', 'value': 'cls80051'},
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

class TimelineRender:
    def __init__(self) -> None:
        self.data = None
        self.paddings = (0, 5, 35, 5)
        self.priceRange = None
        self.maxPrice = None
        self.minPrice = None

    def calcPriceRange(self):
        minVal = 100000
        maxVal = -10000
        for d in self.data['dataArr']:
            minVal = min(d['price'], minVal)
            maxVal = max(d['price'], maxVal)
        self.maxPrice = maxVal
        self.minPrice = minVal
        minVal = min(self.data['pre'], minVal)
        maxVal = max(self.data['pre'], maxVal)
        self.priceRange = (minVal, maxVal)

    def setData(self, data):
        self.priceRange = None
        self.data = data
        if not data:
            return
        self.calcPriceRange()
    
    def getYAtPrice(self, price, height):
        ph = self.priceRange[1] - self.priceRange[0]
        if ph == 0:
            return 0
        height -= self.paddings[1] + self.paddings[3]
        y = (self.priceRange[1] - price) / ph * height + self.paddings[1]
        return int(y)
    
    def getPriceColor(self, price):
        color = 0x0
        GREEN = 0xA3C252
        RED = 0x2204de
        # check is zt
        code = self.data['code']
        zf = 0.1
        if code[0] == '3' or code[0 : 3] == '688':
            zf = 0.20
        pre = self.data['pre']
        ztPrice = int(int(pre * 100 + 0.5) * (1 + zf) + 0.5)
        if int(price * 100 + 0.5) >= ztPrice:
            return 0xdd0000
        dtPrice = int(int(pre * 100 + 0.5) * (1 - zf) + 0.5)
        if int(price * 100 + 0.5) <= dtPrice:
            return 0x00dddd
        if price > self.data['pre']:
            color = RED
        elif price < self.data['pre']:
            color = GREEN
        return color

    def onDraw(self, hdc, drawer : base_win.Drawer, rect):
        if not self.priceRange or self.priceRange[1] - self.priceRange[0] <= 0:
            return
        cwidth = rect[2] - rect[0] - self.paddings[0] - self.paddings[2]
        height = rect[3] - rect[1]
        da = self.data['dataArr']
        if not da:
            return
        dx = cwidth / 240
        drawer.use(hdc, drawer.getPen(self.getPriceColor(da[-1]['price'])))
        for i, d in enumerate(da):
            x = int(i * dx + self.paddings[0])
            y = self.getYAtPrice(d['price'], height)
            if i == 0:
                win32gui.MoveToEx(hdc, x + rect[0], y + rect[1])
            else:
                win32gui.LineTo(hdc, x + rect[0], y + rect[1])
        # draw zero line
        GREEY = 0x909090
        drawer.use(hdc, drawer.getPen(GREEY, win32con.PS_DOT))
        py = self.getYAtPrice(self.data['pre'], height)
        win32gui.MoveToEx(hdc, rect[0] + self.paddings[0], py + rect[1])
        win32gui.LineTo(hdc, rect[2] - self.paddings[2], py + rect[1])
        # draw max price
        mzf = (self.maxPrice - self.data['pre']) / self.data['pre'] * 100
        szf = (self.minPrice - self.data['pre']) / self.data['pre'] * 100
        ZFW = 50
        rc = [rect[2] - ZFW, rect[1], rect[2], rect[1] + 20]
        drawer.use(hdc, drawer.getFont(fontSize = 10))
        drawer.drawText(hdc, f'{mzf :.2f}%', rc, self.getPriceColor(self.maxPrice), win32con.DT_RIGHT | win32con.DT_TOP)
        rc = [rect[2] - ZFW, rect[3] - 12, rect[2], rect[3]]
        drawer.drawText(hdc, f'{szf :.2f}%', rc, self.getPriceColor(self.minPrice), win32con.DT_RIGHT | win32con.DT_BOTTOM)


#ds = cls.ClsUrl().loadFenShi('000099')


if __name__ == '__main__':
    win = ClsBkWindow()
    win.createWindow(None, (100, 100, 1500, 600), win32con.WS_OVERLAPPEDWINDOW  | win32con.WS_VISIBLE)
    #win.updateBk('cls82437')
    win.layout.resize(0, 0, *win.getClientSize())
    win32gui.PumpMessages()
