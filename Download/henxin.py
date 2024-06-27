import datetime, time, random, requests, re, json, os, sys

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

from Tdx import datafile

class Base64:
    def __init__(self):
        self.keys = {}
        self.M = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
        for i in range(len(self.M)):
            self.keys[self.M[i]] = i

    def base64Encode(self, e):
        f = []
        m = self.M
        i = 0
        while i < len(e):
            d = e[i + 0] << 16 | e[i + 1] << 8 | e[i + 2]
            i += 3
            f.extend((m[d >> 18], m[d >> 12 & 0x3f], m[d >> 6 & 0x3f], m[d & 0x3f]))
        f = ''.join(f)
        return f

    def base64Decode(self, s):
        d = []
        i = 0
        while i < len(s):
            h = self.keys[s[i + 0]] << 18 | self.keys[s[i + 1]] << 12 | self.keys[s[i + 2]] << 6 | self.keys[s[i + 3]]
            i += 4
            d.extend((h >> 16, h >> 8 & 0xff, h & 0xff))
        return d

    # data is Array of length 43
    def encode(self, data):
        e = 0
        for d in data:
            e = (e << 5) - e + d
        r = e & 0xff
        e = [3, r]
        i = 0
        j = 2
        while i < len(data):
            #e[j] = data[i] ^ r & 0xff
            e.append(data[i] ^ r & 0xff)
            r = ~(r * 131)
            j += 1
            i += 1
        f = self.base64Encode(e)
        return f

    def decode(self, s):
        t = self.base64Decode(s)
        if t[0] != 3:
            # error
            return 0
        u = t[1]
        rs = [0] * 43
        j = 2
        i = 0
        while j < len(t):
            rs[i] = t[j] ^ u & 0xff
            u = ~(u * 131)
            i += 1
            j += 1
        # check rs is OK
        e = 0
        i = 0
        while i < len(rs):
            e = (e << 5) - e + rs[i]
            i += 1
        e = e & 0xff
        if (e == t[1]):
            return rs
        return 0

class Henxin:
    def __init__(self):
        self.data = []
        self.base_fileds = [4, 4, 4, 4, 1, 1, 1, 3, 2, 2, 2, 2, 2, 2, 2, 4, 2, 1]
        for i in range(len(self.base_fileds)):
            self.data.append(0)
        self.base64 = Base64()
        # user params
        self.mouseMove = 0
        self.mouseClick = 0
        self.mouseWhell = 0
        self.keyDown = 0
        self.tokenServerTime = 0
        self.lastUpdateTime = 0

    def init(self):
        self.data[0] = self.ramdom()
        self.data[1] = self.serverTimeNow()
        self.data[3] = 3539863620 #1486178765; # strhash(navigator.userAgent)
        self.data[4] = 1 # getPlatform
        self.data[5] = 10 # getBrowserIndex
        self.data[6] = 5 # getPluginNum
        self.data[13] = 3748 #2724 # getBrowserFeature
        self.data[15] = 0
        self.data[16] = 0
        self.data[17] = 3
        self.lastUpdateTime = time.time()

    def update(self):
        self.lastUpdateTime = time.time()
        #self.data[1] = self.serverTimeNow()
        self.data[2] = self.timeNow()
        self.data[7] = self.getMouseMove()
        self.data[8] = self.getMouseClick()
        self.data[9] = self.getMouseWhell()
        self.data[10] = self.getKeyDown()
        self.data[11] = self.getClickPosX()
        self.data[12] = self.getClickPosY()
        self.data[15] = 0
        self.data[16] += 1

        n = self.toBuffer()
        rs = self.base64.encode(n)
        # console.log('encode:', rs);
        return rs

    def decodeBuffer(self, buf):
        r = 0
        bf = self.base_fileds
        j = 0
        i = 0
        while i < len(bf):
            v = bf[i]
            r = 0
            while True:
                r = (r << 8) + buf[j]
                j += 1
                v -= 1
                if v <= 0:
                    break
            self.data[i] = r >> 0
            i += 1
        
        return r

    def toBuffer(self):
        c = [0] * 43 # 长度43
        s = -1
        u = self.base_fileds
        for i in range(len(self.base_fileds)):
            l = self.data[i]
            p = u[i]
            s += p
            d = s
            c[d] = l & 0xff
            while True:
                p -= 1
                if p == 0:
                    break
                d -= 1
                l >>= 8
        return c

    def diffTime(self):
        return time.time() - self.lastUpdateTime

    def getMouseMove(self):
        if self.diffTime() >= 30:
            self.mouseMove += int(random.random() * 15)
            self.mouseMove %= 1300
        return self.mouseMove

    def getMouseClick(self):
        if self.diffTime() >= 30:
            self.mouseClick += int(random.random() * 15)
        self.mouseClick %= 1200
        return self.mouseClick

    def getMouseWhell(self):
        if self.diffTime() >= 30:
            self.mouseWhell += int(random.random() * 15)
        self.mouseWhell %= 1200
        return self.mouseWhell

    def getKeyDown(self):
        if self.diffTime() >= 30:
            self.keyDown += int(random.random() * 10)
        self.keyDown %= 1200
        return self.keyDown

    def getClickPosX(self):
        if self.diffTime() >= 30:
            return int(random.random() * 1024)
        return self.data[11]

    def getClickPosY(self):
        if self.diffTime() >= 30:
            return int(random.random() * 720)
        return self.data[12]

    def serverTimeNow(self):
        return self.timeNow() - 13

    def timeNow(self):
        return int(time.time())

    def ramdom(self):
        return int(random.random() * 4294967295)

    def write(self, file):
        f = open(file, 'w')
        txt = ','.join([str(d) for d in self.data])
        f.write(txt)
        f.close()

    def read(self, file):
        f = open(file, 'r')
        txt = f.read(1024)
        ds = txt.split(',')
        for i, d in enumerate(ds):
            self.data[i] = int(d)
        f.close()

    def copy(self, param):
        buf = self.base64.decode(param)
        self.decodeBuffer(buf)


class HexinUrl(Henxin):
    session = None

    class ItemData(object):
        def __init__(self):
            super().__init__()
            
        def __repr__(self) -> str:
            s = '<HexinUrl.ItemData> ' + str(self.__dict__)
            return s

    def __init__(self) -> None:
        super().__init__()
        if not HexinUrl.session:
            HexinUrl.session = requests.Session()
        self.setSessionHeaders(HexinUrl.session)

    def setSessionHeaders(self, session):
        headers = {'Accept': 'text/plain, */*; q=0.01',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Origin': 'http://www.iwencai.com',
                    'Referer': 'http://www.iwencai.com/',
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language': 'zh-CN,zh;q=0.9'}
        session.headers = headers

    def getCodeSH(self, code):
        # 600xxx -> 17;  300xxx 000xxx 002xxx -> 33;   88xxxx -> 48
        if code[0 : 2] == '88': #指数
            return '48'
        if code[0] == '6':
            return '17'
        if code[0] == '0' or code[0] == '3':
            return '33'
        #raise Exception('[HexinUrl.getCodeSH] unknow url for code :', code)
        print('[HexinUrl.getCodeSH] unknow url for code :', code)
        return None
    
    def _getUrlWithParam(self, url):
        param = self.update()
        url = url + '?hexin-v=' + param
        return url
    
    # 分时线 url
    def getFenShiUrl(self, code):
        sh = self.getCodeSH(code)
        if not sh:
            return None
        url = 'http://d.10jqka.com.cn/v6/time/' + sh + '_' + code + '/last.js'
        url = self._getUrlWithParam(url)
        return url
    
    # 今日-日线 url
    def getTodayKLineUrl(self, code):
        sh = self.getCodeSH(code)
        if not sh:
            return None
        url = 'http://d.10jqka.com.cn/v6/line/'+ sh + '_' + code + '/01/today.js'
        url = self._getUrlWithParam(url)
        return url
    
    # 日线 url
    def getKLineUrl(self, code):
        sh = self.getCodeSH(code)
        if not sh:
            return None
        url = 'http://d.10jqka.com.cn/v6/line/'+ sh + '_' + code + '/01/last1800.js'
        url = self._getUrlWithParam(url)
        return url
    
    # 周线 url
    def getKLineUrl_Week(self, code):
        sh = self.getCodeSH(code)
        if not sh:
            return None
        url = 'http://d.10jqka.com.cn/v6/line/'+ sh + '_' + code + '/11/last1800.js'
        url = self._getUrlWithParam(url)
        return url
    
    # 月线 url
    def getKLineUrl_Month(self, code):
        sh = self.getCodeSH(code)
        if not sh:
            return None
        url = 'http://d.10jqka.com.cn/v6/line/'+ sh + '_' + code + '/21/last1800.js'
        url = self._getUrlWithParam(url)
        return url

    # @return today:  {name:xx, data: HexinUrl.ItemData}
    #         kline:  {'name': xx, 'today': today,  'data': [HexinUrl.ItemData, ...]}
    #         fenshi: {name:xx, pre:xx, date:xxx, data: str;str;..., }  data: 时间，价格，成交额（元），分时均价，成交量（手）;
    def loadUrlData(self, url):
        if not url:
            return None
        resp = self.session.get(url)
        if resp.status_code != 200:
            print('[HexinUrl.loadUrlData] Error:', resp)
            raise Exception('[HexinUrl.loadUrlData]', resp)
        txt = resp.content.decode('utf-8')
        bi = txt.index('(')
        ei = txt.rindex(')')
        txt = txt[bi + 1 : ei]
        #print(txt)
        if '/last1800.js' in url:
            # dayly kline
            return self.parseDaylyData(txt)
        if '/today.js' in url:
            return self.parseTodayData(txt)
        if '/last.js' in url:
            return self.parseFenShiData(txt)
        return None
    
    def loadKLineData(self, code):
        url = self.getKLineUrl(code)
        klineRs = self.loadUrlData(url)
        if not klineRs:
            return None
        data = klineRs['data']
        url = self.getTodayKLineUrl(code)
        todayRs = self.loadUrlData(url)
        if data and todayRs['data'] and data[-1].day == todayRs['data'].day:
            data.pop(-1)
        if todayRs['data']:
            data.append(todayRs['data'])
        return klineRs
    
    def parseTodayData(self, txt : str):
        js = json.loads(txt)
        for k in js:
            js = js[k]
            break
        
        item = HexinUrl.ItemData()
        if js['1']:
            setattr(item, 'day', int(js['1']))
        if js['13']:
            setattr(item, 'vol', int(js['13']))
        if js['19']:
            setattr(item, 'amount', int(float(js['19'])))
        if js['1968584']:
            setattr(item, 'rate', float(js['1968584']))
        
        keys = { 'open': '7', 'high':'8', 'low':'9', 'close':'11'} # vol: 单位股, amount:单位元 'amount':'19', 'rate':'1968584'  'vol':'13'  'day': '1',
        for k in keys:
            v = js[keys[k]]
            if type(v) == str:
                if not v:
                    del item
                    item = None
                    break
                if '.' in v and v.index('.') == len(v) - 3:
                    v = v.replace('.', '')
                else:
                    v = float(v) * 100
            setattr(item, k, int(v))
        rs = {'name': js['name'], 'data': item}
        return rs

    # 解析日线数据
    def parseDaylyData(self, txt):
        js = json.loads(txt)
        name, today = js['name'], js['today']
        ds = js['data'].split(';')
        keys = ['day', 'open', 'high', 'low', 'close', 'vol', 'amount', 'rate']; # vol: 单位股, amount:单位元
        rs = []
        for m, d in enumerate(ds):
            obj = HexinUrl.ItemData()
            row = d.split(',')
            #if m == len(ds) - 1: 
            #    print('[henxin.parseDaylyData]', name, row) # last row
            for i, k in enumerate(keys):
                if row[i] == '':
                    row[i] = '0' # fix bug
                if i == 0 or i == 5:
                    setattr(obj, keys[i], int(row[i]))
                elif i >= 1 and i <= 4:
                    if row[i] == '0':
                        del obj
                        obj = None
                        break
                    if len(row[i]) > 3 and row[i][-3] == '.':
                        d = int(row[i].replace('.', ''))
                    else:
                        d = int(float(row[i]) * 100)
                    setattr(obj, keys[i], d)
                elif i == 6:
                    setattr(obj, keys[i], int(float(row[i])))
                elif i == 7:
                    setattr(obj, keys[i], float(row[i]))
            if obj:
                rs.append(obj)
        rv = {'name': name, 'today': today,  'data': rs}
        #print('[henxin.parseDaylyData ] rs[-1]=', rs[-1].__dict__)
        return rv

    def parseFenShiData(self, txt):
        js = json.loads(txt)
        for k in js:
            js = js[k]
            break
        js['pre'] = float(js['pre'])
        js['dataArr'] = []
        iv = js['data'].split(';')
        for item in iv:
            # 时间，价格，成交额（元），分时均价，成交量（手）
            its = item.split(',')
            row = {}
            row['time'] = int(its[0])
            row['price'] = float(its[1])
            row['money'] = float(its[2])
            row['avgPrice'] = float(its[3])
            row['vol'] = float(its[4] if its[4] else '0')
            js['dataArr'].append(row)
        return js

class ThsDataFile(datafile.DataFile):
    def __init__(self, code, dataType):
        #super().__init__(code, datafile.DataFile.DT_DAY, 0)
        if type(code) == int:
            code = f'{code :06d}'
        self.code = code
        self.dataType = dataType
        self.data = []
        self.name = ''

    def loadDataFile(self):
        if self.dataType == datafile.DataFile.DT_DAY:
            hx = HexinUrl()
            rs = hx.loadKLineData(self.code)
            self.data = rs['data']
            self.name = rs['name']
            
if __name__ == '__main__':
    hx = HexinUrl()
    hx.copy('AwMp0DU6YrbvwS5CE1sd7MFgksyoeJf-0Q3b_zXiW0LYRy2yvUgnCuHca35G')
    
    url = hx.getFenShiUrl('603628')
    #url = hx.getTodayKLineUrl('603628')
    #url = hx.getKLineUrl('603628')
    rs = hx.loadUrlData(url)
    print(rs)

if __name__ == '__main__x':
    # javascript: window.location.href = 'https://s.thsi.cn/js/chameleon/time.1' + (new Date().getTime() / 1200000) + '.js'
    pass

# TOKEN_SERVER_TIME
# https://s.thsi.cn/js/chameleon/chameleon.min.1704188.js 