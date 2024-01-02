import datetime, time, random, requests, re

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
        rs = []
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
    def __init__(self, httpSession):
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
        self.httpSession = httpSession

    def init(self):
        self.data[0] = self.ramdom()
        self.data[1] = self.serverTimeNow()
        self.data[3] = 1486178765; # strhash(navigator.userAgent)
        self.data[4] = 1 # getPlatform
        self.data[5] = 10 # getBrowserIndex
        self.data[6] = 5 # getPluginNum
        self.data[13] = 2724 # getBrowserFeature
        self.data[15] = 0
        self.data[16] = 0
        self.data[17] = 3

    def update(self):
        self.data[1] = self.serverTimeNow()
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

    def getMouseMove(self):
        self.mouseMove += int(random.random() * 15)
        return self.mouseMove

    def getMouseClick(self):
        self.mouseClick += int(random.random() * 15)
        return self.mouseClick

    def getMouseWhell(self):
        self.mouseWhell += int(random.random() * 15)
        return self.mouseWhell

    def getKeyDown(self):
        self.keyDown += int(random.random() * 10)
        return self.keyDown

    def getClickPosX(self):
        return int(random.random() * 1024)

    def getClickPosY(self):
        return int(random.random() * 720)

    def serverTimeNow(self):
        return self.timeNow() - 13
        diff = self.timeNow() - self.tokenServerTime
        if (diff > 20 * 60): # 20 minuts
            url = f'https://s.thsi.cn/js/chameleon/chameleon.min.{self.timeNow()}.js'
            reps = self.httpSession.get(url)
            txt = reps.content.decode()
            txt = txt[0 : 100]
            rs = re.findall('TOKEN_SERVER_TIME\s*=\s*(\d+)', txt)
            if not rs:
                print(txt)
                raise Exception('[Henxin.serverTimeNow] Not find TOKEN_SERVER_TIME')
            self.tokenServerTime = int(rs[0])
            #print('tokenTime = ', self.tokenServerTime)
        return int(self.tokenServerTime)

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

class HexinUrl(Henxin):
    def __init__(self, httpSession) -> None:
        super().__init__(httpSession)

    def getCodeSH(self, code):
        # 600xxx -> 17;  300xxx 000xxx 002xxx -> 33;   88xxxx -> 48
        if code[0] == '8': #指数
            return '48'
        if code[0] == '6':
            return '17'
        return '33'
    
    def _getUrlWithParam(self, url):
        param = self.update()
        url = url + '?hexin-v=' + param
        return url
    
    # 分时线 url
    def getFenShiUrl(self, code):
        sh = self.getCodeSH(code)
        url = 'http://d.10jqka.com.cn/v6/time/' + sh + '_' + code + '/last.js'
        url = self._getUrlWithParam(url)
        return url
    
    # 今日-日线 url
    def getTodayKLineUrl(self, code):
        sh = self.getCodeSH(code)
        url = 'http://d.10jqka.com.cn/v6/line/'+ sh + '_' + code + '/01/today.js'
        url = self._getUrlWithParam(url)
        return url
    
    # 日线 url
    def getKLineUrl(self, code):
        sh = self.getCodeSH(code)
        url = 'http://d.10jqka.com.cn/v6/line/'+ sh + '_' + code + '/01/last1800.js'
        url = self._getUrlWithParam(url)
        return url

class HenxinLoader:
    def __init__(self) -> None:
        pass

    def loadFenShiData(text):
        pass


if __name__ == '__main__':
    ss = requests.session()
    hx = HexinUrl(ss)
    hx.init()
    url = hx.getTodayKLineUrl('1A0001')
    url = hx.getFenShiUrl('002528')
    print(url)
    # javascript: window.location.href = 'https://s.thsi.cn/js/chameleon/time.1' + (new Date().getTime() / 1200000) + '.js'

# TOKEN_SERVER_TIME
# https://s.thsi.cn/js/chameleon/chameleon.min.1704188.js 