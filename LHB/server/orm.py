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

# 游资营业部介绍
class YouZi(mcore.BaseModel):
    yyb = pw.CharField()  # 营业部
    yybDesc = pw.CharField() # 名称介绍
    
    @staticmethod
    def saveInfo(yyb, yybDesc):
        val = YouZi.get_or_none(YouZi.yyb == yyb)
        if not val:
            YouZi.create(yyb = yyb, yybDesc = yybDesc)
        else:
            if val.yybDesc != yybDesc:
                print(f'Error YouZi info: find {yyb} in db is {val.yybDesc}, but not is {yybDesc} ')
    
def init():
    mcore.db.create_tables([LHB, YouZi])
