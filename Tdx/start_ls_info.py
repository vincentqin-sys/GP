import sys, os
import peewee as pw
from datafile import *
import orm

class TdxVolPMTools:
    def __init__(self):
        fromDay = 20230101
        v = orm.TdxVolPMModel.select(pw.fn.max(orm.TdxVolPMModel.day)).scalar()
        if v: fromDay = v
        self.fromDay = fromDay
        self.codes = None
        self.codeNames = None
        self.days = None
        
    # 加载所有股标代码（上证、深证股），不含指数、北证股票
    def loadAllCodes(self):
        self.codes = DataFileUtils.listAllCodes()
    
    def calcDays(self):
        self.days = DataFileUtils.calcDays(self.fromDay)

    def initCodeName(self):
        ths_db = pw.SqliteDatabase(f'{orm.path}GP/db/THS_F10.db')
        sql = 'select code, name from 最新动态'
        csr = ths_db.cursor()
        csr.execute(sql)
        rs = csr.fetchall()
        codeNames = {}
        for r in rs:
            codeNames[r[0]] = r[1]
        self.codeNames = codeNames
        csr.close()
        ths_db.close()
    
    def save(self, datas):
        orm.TdxVolPMModel.bulk_create(datas, 50)
    
    def calcVolOrder_Top500(self):
        self.loadAllCodes()
        self.calcDays()
        self.initCodeName()
        dfs = [DataFile(c, DataFile.DT_DAY, False) for c in self.codes]
        bpd = 0
        def sortKey(df):
            idx = df.getItemIdx(bpd)
            if idx < 0:
                return 0
            return df.data[idx].amount

        for day in self.days:
            bpd = day
            newdfs = sorted(dfs, key = sortKey, reverse=True)
            top500 = []
            for i in range(1000):
                nf = newdfs[i]
                code = nf.code
                di = nf.getItemData(day)
                amount =  (di.amount if di else 0) / 100000000
                name = self.codeNames.get(code)
                if not name:
                    name = 'N'
                d = {'code': code, 'name': name, 'day': day, 'amount': amount, 'pm': i + 1}
                top500.append(orm.TdxVolPMModel(**d))
                #print(d)
            self.save(top500)

    # 计算两市成交总额
    def calcSHSZVol(self):
        sh = DataFile('999999', DataFile.DT_DAY, False)
        sz = DataFile('399001', DataFile.DT_DAY, False)
        zs = []
        for day in self.days:
            d1 = sh.getItemData(day)
            d2 = sz.getItemData(day)
            amount = (d1.amount + d2.amount) // 100000000
            zs.append(orm.TdxVolPMModel(**{'code': '999999', 'name': '上证指数', 'day': day, 'amount': d1.amount // 100000000, 'pm': 0}))
            zs.append(orm.TdxVolPMModel(**{'code': '399001', 'name': '深证指数', 'day': day, 'amount': d2.amount // 100000000, 'pm': 0}))
            zs.append(orm.TdxVolPMModel(**{'code': '000000', 'name': '两市成交', 'day': day, 'amount': amount, 'pm': 0}))
        self.save(zs)


class TdxLSTools:
    def __init__(self) -> None:
        fromDay = 20230101
        v = orm.TdxLSModel.select(pw.fn.max(orm.TdxLSModel.day)).scalar()
        if v: fromDay = v
        self.fromDay = fromDay
        self.codes = None
        self.days = None

    def calcOneDayInfo(self, day, sz, sh, dfs):
        item = orm.TdxLSModel()
        item.day = day
        item.amount = (sz.getItemData(day).amount + sh.getItemData(day).amount) // 100000000 # 亿元
        for df in dfs:
            idx = df.getItemIdx(day)
            if idx <= 0:
                continue
            dt = df.data[idx]
            if dt.close > df.data[idx - 1].close:
                item.upNum += 1
            elif dt.close < df.data[idx - 1].close:
                item.downNum += 1
            zdt = getattr(dt, 'zdt', '')
            if zdt == 'ZT':
                item.ztNum += 1
            elif zdt == 'DT':
                item.dtNum += 1
            lbs = getattr(dt, 'lbs', 0)
            if lbs >= 2:
                item.lbNum += 1
            if item.zgb < lbs:
                item.zgb = lbs
        return item

    def calcInfo(self):
        self.codes = DataFileUtils.listAllCodes()
        self.days = DataFileUtils.calcDays(self.fromDay)
        sh = DataFile('999999', DataFile.DT_DAY, True)
        sz = DataFile('399001', DataFile.DT_DAY, True)
        dfs = [DataFile(c, DataFile.DT_DAY, True) for c in self.codes]
        rs = []
        for df in dfs:
            df.calcZDT()
        for day in self.days:
            item = self.calcOneDayInfo(day, sz, sh, dfs)
            rs.append(item)
            print(item)
        orm.TdxLSModel.bulk_create(rs, 50)

if __name__ == '__main__':
    t = TdxVolPMTools()
    t.calcVolOrder_Top500()
    t.calcSHSZVol()
    #-----------------------------
    t = TdxLSTools()
    t.calcInfo()