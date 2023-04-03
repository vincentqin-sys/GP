import peewee as pw
import mcore

class User(mcore.BaseModel):
    name = pw.CharField()
    

class Dept(mcore.BaseModel):
    name = pw.CharField()

# 同花顺龙虎榜
class ThsLHB(mcore.BaseModel):
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

# 通达信龙虎榜
class TdxLHB(mcore.BaseModel):
    day = pw.CharField(column_name = '日期' )
    code = pw.CharField()
    name = pw.CharField()
    title = pw.CharField(column_name = '上榜类型' )
    price = pw.FloatField(column_name = '收盘价' )
    zd = pw.FloatField(column_name = '涨跌幅' )
    vol = pw.IntegerField(column_name = '成交量' ) # 万股
    cjje = pw.IntegerField(column_name = '成交额' ) # 万元
    
    mrje = pw.IntegerField(column_name = '买入金额' ) #  (万元)
    mrjeRate = pw.IntegerField(column_name = '买入金额_占比' ) #  (占总成交比例%)
    mcje = pw.IntegerField(column_name = '卖出金额' ) #  (万元)
    mcjeRate = pw.IntegerField(column_name = '卖出金额_占比' ) #  (占总成交比例%)
    jme = pw.IntegerField(column_name = '净买额' ) #  (万元)
    detail = pw.CharField(column_name = '成交明细' )
    famous = pw.CharField(column_name = '知名游资' )
    
    
def init():
    mcore.db.create_tables([ThsLHB, YouZi, TdxLHB])
