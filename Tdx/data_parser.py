import os, struct
from collections import namedtuple

BASE_PATH = r'D:\Program Files\new_tdx2\vipdoc'
DEST_MIN_LINE_PATH = r'D:\Program Files\new_tdx2\vipdoc2'

class ItemData:
    DS = ('day', 'open', 'high', 'low', 'close', 'money', 'vol') # vol(股)
    MLS = ('day', 'time', 'open', 'high', 'low', 'close', 'money', 'vol') # avgPrice 分时均价
    # MA5

    def __init__(self, *args):
        a = self.DS if len(args) == len(self.DS) else self.MLS
        for i, k in enumerate(a):
            setattr(self, k, args[i])

    def __repr__(self) -> str:
        d = self.__dict__
        a = self.DS if 'time' not in d else self.MLS
        s = 'ItemData('
        for k in a:
            s += f"{k}={str(d[k])}, "
        ks = d.keys() - set(a)
        for k in ks:
            s += f"{k}={str(d[k])}, "
        s = s[0 : -2]
        s += ')'
        return s

class DataFile:
    DT_DAY, DT_MINLINE = 1, 2

    # dataType = DT_DAY  |  DT_MINLINE
    def __init__(self, code, dataType):
        self.code = code
        self.dataType = dataType
        path = self._getPathByCode(self.code)
        self.data = self._loadDataFile(path)

    def getItemIdx(self, day):
        left, right = 0, len(self.data) - 1
        idx = -1
        while left <= right:
            mid = (left + right) // 2
            d = self.data[mid]
            if d.day == day:
                idx = mid
                break
            elif day > d.day:
                left = mid + 1
            else:
                right = mid - 1
        if idx == -1:
            return -1
        if self.dataType == self.DT_DAY:
            return idx
        t = self.data[idx].day
        while idx > 0:
            if self.data[idx - 1].day == t:
                idx -= 1
            else:
                break
        return idx

    def getItemData(self, day):
        idx = self.getItemIdx(day)
        if idx < 0:
            return None
        return self.data[idx]

    def _getPathByCode(self, code):
        tag = 'sh' if code[0] == '6' or code[0] == '8' else 'sz'
        if self.dataType == self.DT_DAY:
            return os.path.join(BASE_PATH, tag, 'lday', tag + code + '.day')
        return os.path.join(BASE_PATH, tag, 'minline', tag + code + '.lc1')

    def _loadDataFile(self, path):
        def T(fv): return int(fv * 100 + 0.5)
        rs = []
        f = open(path, 'rb')
        while f.readable():
            bs = f.read(32)
            if len(bs) != 32:
                break
            if self.dataType == self.DT_DAY:
                item = struct.unpack('5lf2l', bs)
                item = ItemData(item[0 : -1])
            else:
                item = struct.unpack('2H5f2l', bs)
                d0 = item[0]
                y = (int(d0 / 2048) + 2004)
                m = int((d0 % 2048 ) / 100)
                r = (d0 % 2048) % 100
                d0 = y * 10000 + m * 100 + r
                d1 = (item[1] // 60) * 100 + (item[1] % 60)
                item = ItemData(d0, d1, T(item[2]), T(item[3]), T(item[4]), T(item[5]), item[6], item[7])
            rs.append(item)
        f.close()
        # check minute line number
        if self.dataType == self.DT_MINLINE and (len(rs) % 240) != 0:
            raise Exception('Minute Line number error:', len(rs))
        return rs

    # 分时均线
    def calcAvgPriceOfDay(self, day):
        if not self.data or len(self.data) == 0:
            return 0
        if self.dataType != self.DT_MINLINE:
            return 0
        fromIdx = self.getItemIdx(day)
        if fromIdx < 0:
            return 0
        idx = fromIdx
        sumMoney, sumVol = 0, 0
        while idx < len(self.data) and self.data[idx].day == day:
            d = self.data[idx]
            sumMoney += d.money
            sumVol += d.vol
            d.avgPrice = sumMoney / sumVol
            idx += 1

    def calcMA(self, N):
        name = 'MA' + str(N)
        for i in range(N - 1, len(self.data)):
            ap = 0
            for j in range(i + 1 - N, i + 1):
                ap += self.data[j].close
            setattr(self.data[i], name, ap / N)
    
    def _calcZDTInfo(self, pre, c):
        is20p = (self.code[0:3] == '688') or (self.code[0:2] == '30')
        is20p = is20p and c.day >= 20200824
        ZT = 20 if is20p else 10
        iszt = int(pre * (100 + ZT) / 100 + 0.5) <= c.close
        isztzb = (int(pre * (100 + ZT) / 100 + 0.5) <= c.high) and (c.high != c.close)
        isdt = int(pre * (100 - ZT) / 100 + 0.5) >= c.close
        isdtzb = (int(pre * (100 - ZT) / 100 + 0.5) >= c.low) and (c.low != c.close)
        if isztzb: c.ZDT = 'ZTZB'
        if isdtzb: c.ZDT = 'DTZB'
        if iszt: c.ZDT = 'ZT'
        if isdt: c.ZDT = 'DT'

    # 计算涨跌停信息
    def calcZDT(self):
        if self.dataType == self.DT_DAY:
            for i in range(1, len(self.data)):
                self._calcZDTInfo(self.data[i - 1].close, self.data[i])
        else:
            ONE_DAY_NUM = 240
            for i in range(1, len(self.data) // ONE_DAY_NUM):
                pre = self.data[i * ONE_DAY_NUM - 1].close
                lc = 0
                for j in range(0, ONE_DAY_NUM):
                    cur = self.data[i * ONE_DAY_NUM + j]
                    if lc != cur.close:
                        self._calcZDTInfo(pre, cur)
                    lc = cur.close

    # 获得涨停板
    # param includeZTZB  是否含涨停炸板
    def getItemsByZT(self, includeZTZB : bool):
        rs = []
        for d in self.data:
            if getattr(d, 'ZDT', None) == 'ZT':
                rs.append(d)
            if includeZTZB and getattr(d, 'ZDT', None) == 'ZTZB':
                rs.append(d)
        return rs

if __name__ == '__main__':
    df = DataFile('300364', DataFile.DT_MINLINE)
    df.calcMA(5)
    df.calcZDT()
    zt = df.getItemsByZT(True)
    for d in zt:
        print(d, sep= '\n')
    