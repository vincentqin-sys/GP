import peewee as pw
import mcore

class User(mcore.BaseModel):
    name = pw.CharField()
    

class Dept(mcore.BaseModel):
    name = pw.CharField()

class LHB(mcore.BaseModel):
    day = pw.CharField()
    tag = pw.CharField()
    code = pw.CharField()
    name = pw.CharField()
    title = pw.CharField()
    price = pw.FloatField() # 当前价格
    zd = pw.FloatField() # 涨跌幅
    cjje = pw.FloatField() # 成交额 (万元)
    jme = pw.FloatField() # 净买额 (万元)
    mrje = pw.FloatField() # 买入金额 (万元)
    mcje = pw.FloatField() # 买出金额 (万元)
    detail = pw.CharField()

def init():
    mcore.db.create_tables([LHB])
