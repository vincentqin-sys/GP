import sys, os
import peewee as pw
from data_parser import *
import orm

class TdxVolPMTools:
    def __init__(self):
        fromDay = 20230101
        v = orm.TdxVolPMModel.select(pw.fn.max(orm.TdxVolPMModel.day)).scalar()
        if v: fromDay = v
        self.fromDay = fromDay
        
    def _loadAllCodes(self):
        sh = os.path.join(VIPDOC_BASE_PATH, 'sh/lday')
        codes = os.listdir(sh)
        rtSH = [c for c in codes if c[2] == '6']
        sz = os.path.join(VIPDOC_BASE_PATH, 'sz/lday')
        codes = os.listdir(sz)
        rtSZ = [c for c in codes if c[2] == '0' or c[2] == '3']
        self.codes = rtSH + rtSZ
    
    def _calcDays(self):
        df = DataFile('999999', DataFile.DT_DAY)
        days = []
        for i in range(len(df.data)):
            if df.data[i].day > self.fromDay:
                days.append(df.data[i].day)
        self.days = days

    def _initCodeName(self):
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
    
    def _save(self, datas):
        orm.TdxVolPMModel.bulk_create(datas, 50)
    
    def calcVolOrder_Top500(self):
        self._loadAllCodes()
        self._calcDays()
        self._initCodeName()
        dfs = [DataFile(c[2:8], DataFile.DT_DAY) for c in self.codes]
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
                d = {'code': code, 'name': self.codeNames.get(code), 'day': day, 'amount': amount, 'pm': i + 1}
                top500.append(orm.TdxVolPMModel(**d))
                print(d)
            self._save(top500)

    # 计算两市成交总额
    def calcSHSZVol(self):
        sh = DataFile('999999', DataFile.DT_DAY)
        sz = DataFile('399001', DataFile.DT_DAY)
        zs = []
        for day in self.days:
            d1 = sh.getItemData(day)
            d2 = sz.getItemData(day)
            amount = (d1.amount + d2.amount) // 100000000
            zs.append(orm.TdxVolPMModel(**{'code': '999999', 'name': '上证指数', 'day': day, 'amount': d1.amount // 100000000, 'pm': 0}))
            zs.append(orm.TdxVolPMModel(**{'code': '399001', 'name': '深证指数', 'day': day, 'amount': d2.amount // 100000000, 'pm': 0}))
            zs.append(orm.TdxVolPMModel(**{'code': '000000', 'name': '两市成交', 'day': day, 'amount': amount, 'pm': 0}))
        self._save(zs)

if __name__ == '__main__':
    t = TdxVolPMTools()
    t.calcVolOrder_Top500()
    t.calcSHSZVol()
