import ctypes, os, sys, requests, json

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
    print('[_c_digest]', r)
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
        raise Exception('Not Support code: ', code)
    
    def _signParams(self, params):
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
        url += self._signParams(params)
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        #print(js['data'])
        return js['data']
        
    # 基本信息
    def loadBasic(self, code):
        params = {
            'secu_code': self._getTagCode(code),
            'fields': 'open_px,av_px,high_px,low_px,change,change_px,down_price,change_3,change_5,qrr,entrust_rate,tr,amp,TotalShares,mc,NetAssetPS,NonRestrictedShares,cmc,business_amount,business_balance,pe,ttm_pe,pb,secu_name,secu_code,trade_status,secu_type,preclose_px,up_price,last_px',
            'app': 'CailianpressWeb',
            'os': 'web',
            'sv': '7.7.5'
        }
        url = f'https://x-quote.cls.cn/quote/stock/basic?' + self._signParams(params)
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        data = js['data']
        rt = {}
        rt['pre'] = data['preclose_px'] # 昨日收盘价
        rt['code'] = data['secu_code'][2 : ]
        rt['name'] = data['secu_name']
        rt['vol'] = int(data['business_amount']) // 100 # int 手
        rt['amount'] = int(data['business_balance']) # int 元
        rt['open'] = data['open_px']
        rt['high'] = data['high_px']
        rt['close'] = data['last_px']
        rt['low'] = data['low_px']
        pre = rt['pre'] or rt['open']
        rt['涨幅'] = (rt['close'] - pre) / pre * 100
        rt['委比'] = data['entrust_rate'] * 100 # 0 ~ 100%
        rt['总市值'] = int(data['mc']) # int 元
        rt['流通市值'] = int(data['cmc']) # int 元
        rt['每股净资产'] = data['NetAssetPS']
        rt['流通股本'] = int(data['NonRestrictedShares'])
        rt['总股本'] = int(data['TotalShares'])
        rt['市净率'] = data['pb']
        rt['市盈率_静'] = data['pe']
        rt['市盈率_TTM'] = data['ttm_pe']
        #print(rt)
        return rt
    
    # 近5日分时
    def loadHistory5FenShi(self, code):
        params = {
            'secu_code': self._getTagCode(code),
            'app': 'CailianpressWeb',
            'os': 'web',
            'sv': '7.7.5'
        }
        url = f'https://x-quote.cls.cn/quote/stock/tline_history?' + self._signParams(params)
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        data = js['data']
        print(data)
        return data
    
    # K线数据
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
        url = f'https://x-quote.cls.cn/quote/stock/kline?' + self._signParams(params)
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        data = js['data']
        print(data)
        pass


#signByStr('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz012')
#signByStr('app=CailianpressWeb&fields=date,minute,last_px,business_balance,business_amount,open_px,preclose_px,av_px&os=web&secu_code=sz301488&sv=7.7.5')
ClsUrl().loadKline('000506')