import os, struct, platform
from collections import namedtuple

VIPDOC_BASE_PATH = r'D:\Program Files\new_tdx2\vipdoc'

class ItemData:
    DS = ('day', 'open', 'high', 'low', 'close', 'amount', 'vol') # vol(股), lbs(连板数), zdt(涨跌停), zhangFu(涨幅)
    MLS = ('day', 'time', 'open', 'high', 'low', 'close', 'amount', 'vol') # avgPrice 分时均价
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
    FROM_DAY = 20230101 # 仅计算由此开始的日期数据
    FLAG_NEWEST, FLAG_OLDEST, FLAG_ALL = -1, -2, -3 # 最新、最早、全部

    # @param dataType = DT_DAY  |  DT_MINLINE
    # @param flag = FLAG_NEWEST | FLAG_OLDEST | FLAG_ALL
    def __init__(self, code, dataType, flag):
        self.code = code
        self.dataType = dataType
        paths = self._getPathByCode(self.code, flag)
        self.data = self._loadDataFiles(paths)

    @staticmethod
    def loadFromFile(filePath):
        name = os.path.basename(filePath)
        code = name[2 : 8]
        dataType = DataFile.DT_DAY if name[-4 : ] == '.day' else DataFile.DT_MINLINE
        datafile = DataFile(code, dataType, False)
        datafile.data = datafile._loadDataFile(filePath)
        return datafile

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

    def _getByFlag(self, arr, flag):
        if flag == self.FLAG_ALL:
            return arr
        if flag == self.FLAG_NEWEST:
            return arr[-1]
        if flag == self.FLAG_OLDEST:
            return arr[0]
        raise Exception('Error flag, flag=', flag)

    def _getPathByCode(self, code, flag):
        tag = 'sh' if code[0] == '6' or code[0] == '8' or code[0] == '9' else 'sz'
        bp = os.path.join(VIPDOC_BASE_PATH, tag)
        fs = os.listdir(bp)
        fs = sorted(fs)
        rt = []
        if self.dataType == self.DT_DAY:
            rt = sorted([f for f in fs if 'lday-' in f])
            rt.append('lday')
            rt = self._getByFlag(rt, flag)
            rt = [os.path.join(bp, r, tag + code + '.day') for r in rt]
        else:
            rt = [f for f in fs if 'minline-' in f]
            rt.append('minline')
            rt = self._getByFlag(rt, flag)
            rt = [os.path.join(bp, r, tag + code + '.lc1') for r in rt]
        rs = [r for r in rt if os.path.exists(r)]
        return rs

    def _loadDataFiles(self, paths):
        rt = None
        for p in paths:
            data = self._loadDataFile(p)
            if not rt:
                rt = data
                continue
            lastDay = rt[-1].day
            for d in data:
                if d.day > lastDay:
                    rt.append(d)
        return rt

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
                item = ItemData(*item[0 : -1])
            else:
                item = struct.unpack('2H5f2l', bs)
                d0 = item[0]
                y = (int(d0 / 2048) + 2004)
                m = int((d0 % 2048 ) / 100)
                r = (d0 % 2048) % 100
                d0 = y * 10000 + m * 100 + r
                d1 = (item[1] // 60) * 100 + (item[1] % 60)
                item = ItemData(d0, d1, T(item[2]), T(item[3]), T(item[4]), T(item[5]), item[6], item[7])
            if item.day >= self.FROM_DAY:
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
        sumamount, sumVol = 0, 0
        while idx < len(self.data) and self.data[idx].day == day:
            d = self.data[idx]
            sumamount += d.amount
            sumVol += d.vol
            d.avgPrice = sumamount / sumVol
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
        if isztzb: c.zdt = 'ZTZB'
        if isdtzb: c.zdt = 'DTZB'
        if iszt: c.zdt = 'ZT'
        if isdt: c.zdt = 'DT'

    # 计算涨跌停信息
    def calcZDT(self):
        if self.dataType == self.DT_DAY:
            for i in range(1, len(self.data)):
                self._calcZDTInfo(self.data[i - 1].close, self.data[i])
                if getattr(self.data[i], 'zdt', '') == 'ZT':
                    nowLbs = getattr(self.data[i - 1], 'lbs', 0)
                    self.data[i].lbs = nowLbs + 1
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

    #计算涨幅
    def calcZhangFu(self):
        if self.dataType != self.DT_DAY:
            return
        for i in range(1, len(self.data)):
            pc = self.data[i - 1].close
            cc = self.data[i].close
            zhangFu = (cc - pc) / pc * 100
            setattr(self.data[i], 'zhangFu', zhangFu)

    # 获得涨停板
    # param includeZTZB  是否含涨停炸板
    def getItemsByZT(self, includeZTZB : bool):
        rs = []
        for d in self.data:
            if getattr(d, 'zdt', None) == 'ZT':
                rs.append(d)
            if includeZTZB and getattr(d, 'zdt', None) == 'ZTZB':
                rs.append(d)
        return rs

class DataFileUtils:

    # 所有股标代码（上证、深证股），不含指数、北证股票
    # @return list[code, ...]
    @staticmethod
    def listAllCodes():
        allDirs = []
        for tag in ('sh', 'sz'):
            sh = os.path.join(VIPDOC_BASE_PATH, tag)
            for ld in os.listdir(sh):
                if 'lday' in ld:
                    allDirs.append(os.path.join(sh, ld))
        rs = set()
        for d in allDirs:
            codes = os.listdir(d)
            rt = [c[2:8] for c in codes if (c[2] == '6' or c[2] == '0' or c[2] == '3') and (c[2:5] != '399')]
            rs = rs.union(rt)
        rs = sorted(rs, reverse=True)
        return rs
    
    # 计算fromDay开始的所有日期
    # @return list[day, ...]
    @staticmethod
    def calcDays(fromDay, inclueFromDay = False):
        df = DataFile('999999', DataFile.DT_DAY, DataFile.FLAG_ALL)
        days = []
        for i in range(len(df.data)):
            if inclueFromDay and df.data[i].day == fromDay:
                days.append(df.data[i].day)
            if df.data[i].day > fromDay:
                days.append(df.data[i].day)
        return days
    
if __name__ == '__main__':
    pass
    