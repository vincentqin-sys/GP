import sys, os
import peewee as pw
from data_parser import *
import orm

class TdxVolOrderTools:
    def __init__(self):
        fromDay = 20230101
        v = orm.TdxVolOrderModel.select(pw.fn.max(orm.TdxVolOrderModel.day)).scalar()
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
        df = DataFile('880081', DataFile.DT_DAY)
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
        orm.TdxVolOrderModel.bulk_create(datas, 50)
    
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
                top500.append(orm.TdxVolOrderModel(**d))
                print(d)
            self._save(top500)


if __name__ == '__main__':
    t = TdxVolOrderTools()
    t.calcVolOrder_Top500()
