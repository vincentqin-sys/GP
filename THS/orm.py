import peewee as pw
import sys

path = __file__[0 : __file__.upper().index('GP')]
db = pw.SqliteDatabase(f'{path}GP/db/THS_F10.db')

# 同花顺--最新动态
class THS_Newest(pw.Model):
    code = pw.CharField() #股票代码
    name = pw.CharField() #股票名称
    zsz = pw.IntegerField(null=True, column_name='总市值') # （亿元）
    gsld = pw.CharField(null=True, column_name='公司亮点')
    kbgs = pw.CharField(null=True, column_name='可比公司')
    cwfx = pw.CharField(null=True, column_name='财务分析')

    class Meta:
        database = db
        table_name = '最新动态'

# 同花顺--前十大流通股东
class THS_Top10_LTGD(pw.Model):
    code = pw.CharField() #股票代码
    day = pw.CharField(null = True) # 日期 YYYY-MM-DD
    rate = pw.FloatField(null = True) # 前十大流通股东占比 %
    change = pw.FloatField(null=True, column_name='较上期变化') # 万股
    class Meta:
        database = db
        table_name = '前十大流通股东'

# 同花顺-- 机构持股 (主力持仓)
class THS_JGCG(pw.Model):
    code = pw.CharField() #股票代码
    day = pw.CharField(null=True) # 日期(年报、季报、中报等)   中报改为二季报， 年报改为四季报
    jjsl = pw.IntegerField(null=True, column_name='机构数量')
    rate = pw.FloatField(null=True, column_name='持仓比例')
    change = pw.FloatField(null=True, column_name='较上期变化') # (万股)
    day_sort = pw.CharField(null=True) # 日期，用于排序

    class Meta:
        database = db
        table_name = '机构持股'

# 同花顺--行业对比（排名）
class THS_HYDB(pw.Model):
    code = pw.CharField() #股票代码
    name = pw.CharField() #股票名称
    day = pw.CharField() # 报告日期
    hy = pw.CharField(null=True, column_name='行业')
    hydj = pw.IntegerField(null = True, column_name='行业等级') #
    hysl = pw.IntegerField(null=True, column_name='同行数量') # 行业中股票总数量

    mgsy = pw.FloatField(null=True, column_name='每股收益') #
    mgjzc = pw.FloatField(null=True, column_name='每股净资产') #
    mgxjl = pw.FloatField(null=True, column_name='每股现金流') #
    jlr = pw.FloatField(null=True, column_name='净利润') #
    yyzsl = pw.FloatField(null=True, column_name='营业总收入') #
    zgb = pw.FloatField(null=True, column_name='总股本') #

    zhpm = pw.IntegerField(null = True, column_name='综合排名')

    class Meta:
        database = db
        table_name = '行业对比'


# 同花顺--概念题材
class THS_GNTC(pw.Model):
    code = pw.CharField() #股票代码
    name = pw.CharField() #股票名称
    gn = pw.CharField(null=True) # 常规概念，每概概念之间用;分隔
    hy = pw.CharField(null=True) # 行业

    class Meta:
        database = db
        table_name = '概念题材'

#查询指字的股票代码的详细信息 
# return a dict of : {THS_Newest:最新动态、THS_GNTC:概念题材、THS_GD:股东、THS_JGCC:机构持仓、THS_HYDB_2:行业对比(二级)、THS_HYDB_3:行业对比(三级)}
def queryFullInfo(code):
    code = code.strip()
    rs = {'code' : code}
    rs['THS_Newest'] = THS_Newest.get_or_none(THS_Newest.code == code)
    rs['THS_GNTC'] = THS_GNTC.get_or_none(THS_GNTC.code == code)
    rs['THS_GD'] = THS_Top10_LTGD.get_or_none(THS_Top10_LTGD.code == code)
    rs['THS_JGCC'] = THS_JGCG.get_or_none(THS_JGCG.code == code)
    rs['THS_HYDB_2'] = THS_HYDB.get_or_none((THS_HYDB.code == code) & (THS_HYDB.hyDJ == '二级'))
    rs['THS_HYDB_3'] = THS_HYDB.get_or_none((THS_HYDB.code == code) & (THS_HYDB.hyDJ == '三级'))
    #print(rs)
    return rs

db2 = pw.SqliteDatabase(f'{path}GP/db/THS_Hot.db')

# 同花顺--个股热度排名
class THS_Hot(pw.Model):
    day = pw.IntegerField(column_name = '日期') # 刷新日期
    code = pw.IntegerField() #股票代码
    time = pw.IntegerField(column_name = '时间') # 刷新时间  HHMM
    hotValue = pw.IntegerField(column_name = '热度值_万' ) #
    hotOrder = pw.IntegerField(column_name = '热度排名' ) #

    class Meta:
        database = db2
        table_name = '个股热度排名'

# 同花顺--个股热度综合排名
class THS_HotZH(pw.Model):
    day = pw.IntegerField(column_name = '日期') # 刷新日期
    code = pw.IntegerField() #股票代码
    avgHotValue = pw.IntegerField(column_name = '平均热度值_万' )
    avgHotOrder = pw.FloatField(column_name = '平均热度排名' )
    zhHotOrder = pw.IntegerField(column_name = '综合热度排名' )

    class Meta:
        database = db2
        table_name = '个股热度综合排名'


db3 = pw.SqliteDatabase(f'{path}GP/db/TaoGuBa.db')

# 淘股吧 remark表 收藏表
class TaoGuBa_Remark(pw.Model):
    info = pw.TextField() # 收藏信息
    class Meta:
        database = db3

# 大单流入流出情况
db5 = pw.SqliteDatabase(f'{path}/GP/db/THS_DDLR.db')
class THS_DDLR(pw.Model):
    day = pw.CharField(max_length = 8) # YYYYMMDD
    code = pw.CharField(max_length = 6)
    name = pw.CharField(max_length= 24)
    activeIn = pw.DecimalField(column_name = '主动买入_亿' , null=True, decimal_places = 1, max_digits = 10) # 亿元
    activeOut = pw.DecimalField(column_name = '主动卖出_亿' , null=True, decimal_places = 1, max_digits = 10) #  (亿元)
    positiveIn = pw.DecimalField(column_name = '被动买入_亿' , null=True, decimal_places = 1, max_digits = 10) #  (亿元)
    positiveOut = pw.DecimalField(column_name = '被动卖出_亿' , null=True, decimal_places = 1, max_digits = 10) #  (亿元)
    total = pw.DecimalField(column_name = '净流入_亿' , null=True, decimal_places = 1, max_digits = 10) # 亿元
    amount = pw.DecimalField(column_name='成交额_亿', null=True, decimal_places = 1, max_digits = 10)
    class Meta:
        database = db5
        table_name = '个股大单买卖'

db_thszs = pw.SqliteDatabase(f'{path}GP/db/THS_ZS.db')
class THS_ZS(pw.Model):
    code = pw.CharField() #指数代码
    name = pw.CharField() #指数名称
    gnhy = pw.CharField() #概念、行业
    hydj = pw.CharField(null = True, default = None) #行业等级 二级、三级

    class Meta:
        database = db_thszs
        table_name = '同花顺指数'

class THS_ZS_ZD(pw.Model):
    day = pw.CharField()
    code = pw.CharField() #指数代码
    name = pw.CharField() #指数名称
    close = pw.FloatField()
    open = pw.FloatField()
    high = pw.FloatField()
    rate = pw.FloatField()
    money = pw.FloatField() #亿(元)
    vol = pw.FloatField() # 亿(股)
    zdf = pw.FloatField() #涨跌幅
    zdf_50PM = pw.IntegerField(default = 0) # 50亿以上排名
    zdf_PM = pw.IntegerField(default = 0) # 全部排名

    class Meta:
        database = db_thszs
        table_name = '同花顺指数涨跌信息'

db_kpl = pw.SqliteDatabase(f'{path}GP/db/KPL.db')
class KPL_ZT(pw.Model):
    code = pw.CharField()
    name = pw.CharField(null = True)
    day = pw.CharField() # YYYY-MM-DD
    ztTime = pw.CharField(null = True, column_name='涨停时间')
    status = pw.CharField(null = True, column_name='状态')
    ztReason = pw.CharField(null = True, column_name='涨停原因')
    ztNum = pw.CharField(null=True, column_name='涨停数量')
    remark = pw.CharField(null=True, column_name='备注')

    class Meta:
        database = db_kpl
        table_name = '开盘啦涨停'

class KPL_SCQX(pw.Model):
    day = pw.CharField()
    zhqd = pw.IntegerField(column_name='综合强度')

    class Meta:
        database = db_kpl
        table_name = '开盘啦市场情绪'

db_cls = pw.SqliteDatabase(f'{path}GP/db/CLS.db')
class CLS_ZT(pw.Model):
    day = pw.CharField() # YYYY-MM-DD
    code = pw.CharField()
    name = pw.CharField(null = True)
    lbs = pw.IntegerField(default = 0, column_name='连板数')
    ztReason = pw.CharField(null = True, column_name='涨停原因')
    detail = pw.CharField(null = True, column_name='详情')

    class Meta:
        database = db_cls
        table_name = '财联社涨停'


db.create_tables([THS_JGCG, THS_HYDB, THS_Top10_LTGD, THS_GNTC, THS_Newest])
db2.create_tables([THS_Hot, THS_HotZH])
db3.create_tables([TaoGuBa_Remark])
db5.create_tables([THS_DDLR])
db_thszs.create_tables([THS_ZS, THS_ZS_ZD])
db_kpl.create_tables([KPL_ZT, KPL_SCQX])
db_cls.create_tables([CLS_ZT])

    