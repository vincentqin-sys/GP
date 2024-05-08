import ctypes, os, sys, requests, json, traceback

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile

PX = os.path.join(os.path.dirname(__file__), 'cls-sign.dll')
mydll = ctypes.CDLL(PX)

def signByStr(s : str):
    return _c_digest(s)

def signByDict(params : dict):
    if not params:
        return signByStr('')
    ks = list(params.keys()).sort()
    sl = []
    for k in ks:
        sl.append(f'{k}={ks[k]}')
    s = '&'.join(sl)
    rs = _c_digest(s)
    return rs

def _c_digest(s : str):
    digest = mydll.digest # 
    digest.restype = ctypes.c_char_p
    digest.argtypes = [ctypes.c_char_p]

    bs = s.encode('utf-8')
    rs : bytes = digest(bs) # ctypes.c_char_p(bs)
    r = rs.decode('utf-8')
    #print('[_c_digest]', r)
    return r

class ClsUrl:
    def __init__(self) -> None:
        pass

    def _getTagCode(self, code):
        if type(code) == int:
            code = f'{code :06d}'
        if code[0] == '6':
            return 'sh' + code
        if code[0] == '0' or code[0] == '3':
            return 'sz' + code
        return code
    
    def signParams(self, params):
        if isinstance(params, str):
            sign = signByStr(params)
            return params + '&sign=' + sign
        if isinstance(params, dict):
            ks = list(params.keys())
            ks.sort()
            sl = []
            for k in ks:
                sl.append(f'{k}={params[k]}')
            sparams = '&'.join(sl)
            sign = signByStr(sparams)
            return sparams + '&sign=' + sign
        return None # error params

    # 当日分时
    def loadFenShi(self, code):
        url = 'https://x-quote.cls.cn/quote/stock/tline?'
        scode = self._getTagCode(code)
        params = f'app=CailianpressWeb&fields=date,minute,last_px,business_balance,business_amount,open_px,preclose_px,av_px&os=web&secu_code={scode}&sv=7.7.5'
        url += self.signParams(params)
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        #print(js['data'])
        return js['data']
    
    def getVal(self, data, name, _type, default):
        if name not in data:
            return default
        val = data[name]
        if val == None:
            return default
        return _type(val)

    # 基本信息
    def loadBasic(self, code):
        try:
            params = {
                'secu_code': self._getTagCode(code),
                'fields': 'open_px,av_px,high_px,low_px,change,change_px,down_price,change_3,change_5,qrr,entrust_rate,tr,amp,TotalShares,mc,NetAssetPS,NonRestrictedShares,cmc,business_amount,business_balance,pe,ttm_pe,pb,secu_name,secu_code,trade_status,secu_type,preclose_px,up_price,last_px',
                'app': 'CailianpressWeb',
                'os': 'web',
                'sv': '7.7.5'
            }
            url = f'https://x-quote.cls.cn/quote/stock/basic?' + self.signParams(params)
            resp = requests.get(url)
            txt = resp.content.decode('utf-8')
            js = json.loads(txt)
            data = js['data']
            rt = {}
            rt['pre'] = self.getVal(data, 'preclose_px', float, 0) # 昨日收盘价
            rt['code'] = data['secu_code'][2 : ]
            rt['name'] = data['secu_name']
            rt['vol'] = self.getVal(data, 'business_amount', int, 0) # int 股
            rt['amount'] = self.getVal(data, 'business_balance', int, 0) # int 元
            rt['open'] = self.getVal(data, 'open_px', float, 0)
            rt['high'] = self.getVal(data, 'high_px', float, 0)
            rt['close'] = self.getVal(data, 'last_px', float, 0)
            rt['low'] = self.getVal(data, 'low_px', float, 0)
            #pre = rt['pre'] or rt['open']
            #if pre != 0:
            #    rt['涨幅'] = (rt['close'] - pre) / pre * 100
            rt['涨幅'] = self.getVal(data, 'change', float, 0) * 100
            rt['委比'] = self.getVal(data, 'entrust_rate', float, 0) * 100 # 0 ~ 100%
            rt['总市值'] = self.getVal(data, 'mc', int, 0) # int 元
            rt['流通市值'] = self.getVal(data, 'cmc', int, 0) # int 元
            rt['每股净资产'] = self.getVal(data, 'NetAssetPS', float, 0)
            rt['流通股本'] = self.getVal(data, 'NonRestrictedShares', int, 0)
            rt['总股本'] = self.getVal(data, 'TotalShares', int, 0)
            rt['市净率'] = self.getVal(data, 'pb', float, 0)
            rt['市盈率_静'] = self.getVal(data, 'pe', float, 0)
            rt['市盈率_TTM'] = self.getVal(data, 'ttm_pe', float, 0)
            #print(rt)
            return rt
        except Exception as e:
            traceback.print_exc()
    
    # 近5日分时
    def loadHistory5FenShi(self, code):
        params = {
            'secu_code': self._getTagCode(code),
            'app': 'CailianpressWeb',
            'os': 'web',
            'sv': '7.7.5'
        }
        url = f'https://x-quote.cls.cn/quote/stock/tline_history?' + self.signParams(params)
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        data = js['data']
        #print(data)
        return data
    
    def _toStd(self, data):
        data['day'] = data['date']
        sc = data['secu_code']
        if ('cls' in sc) or ('sh0' in sc):
            data['code'] = sc
        else:
            data['code'] = sc[2 : ]
        if 'open_px' in data: data['open'] = data['open_px']
        if 'close_px' in data: data['close'] = data['close_px']
        if 'low_px' in data: data['low'] = data['low_px']
        if 'high_px' in data: data['high'] = data['high_px']
        if 'preclose_px' in data: data['pre'] = data['preclose_px']
        if 'change' in data: data['zf'] = data['change'] * 100 # %  zf = 涨幅
        if 'tr' in data: data['rate'] = data['tr'] * 100 # %
        if 'business_amount' in data: data['vol'] = data['business_amount']
        if 'business_balance' in data: data['amount'] = data['business_balance']

    # K线数据
    # limit : K线数量
    def loadKline(self, code, limit = 100):
        params = {
            'secu_code': self._getTagCode(code),
            'app': 'CailianpressWeb',
            'os': 'web',
            'sv': '7.7.5',
            'offset': 0,
            'limit': limit,
            'type': 'fd1'
        }
        url = f'https://x-quote.cls.cn/quote/stock/kline?' + self.signParams(params)
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        data = js['data']
        for d in data:
            self._toStd(d)
        #print(data)
        return data

class ClsDataFile(datafile.DataFile):
    def __init__(self, code, dataType):
        #super().__init__(code, dataType, flag)
        if type(code) == int:
            code = f'{code :06d}'
        self.code = code
        self.dataType = dataType
        self.name = ''
        self.data = []

    def loadDataFile(self):
        if self.dataType == self.DT_DAY:
            self._loadDataFile_KLine()
        else:
            self._loadDataFile_FS()

    def _loadDataFile_KLine(self):
        datas = ClsUrl().loadKline(self.code, 500)
        for ds in datas:
            it = datafile.ItemData()
            it.day = ds['date']
            it.open = int(ds['open_px'] * 100 + 0.5)
            it.close = int(ds['close_px'] * 100 + 0.5)
            it.low = int(ds['low_px'] * 100 + 0.5)
            it.high = int(ds['high_px'] * 100 + 0.5)
            it.amount = int(ds['business_balance'])
            it.vol = int(ds['business_amount'])
            it.rate = ds.get('tr', 0) * 100
            self.data.append(it)
        
    def _loadDataFile_FS(self):
        datas = ClsUrl().loadHistory5FenShi(self.code)
        for ds in datas:
            it = datafile.ItemData()
            it.day = ds['date']
            it.time = ds['minute']
            it.open = int(ds['open_px'] * 100 + 0.5)
            it.close = int(ds['close_px'] * 100 + 0.5)
            it.low = int(ds['low_px'] * 100 + 0.5)
            it.high = int(ds['high_px'] * 100 + 0.5)
            it.amount = int(ds['business_balance'])
            it.vol = int(ds['business_amount'])
            self.data.append(it)


#signByStr('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz012')
#signByStr('app=CailianpressWeb&fields=date,minute,last_px,business_balance,business_amount,open_px,preclose_px,av_px&os=web&secu_code=sz301488&sv=7.7.5')
#ClsUrl().loadKline('603900') #cls80133