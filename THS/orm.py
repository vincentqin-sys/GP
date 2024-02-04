import peewee as pw
import sys

path = sys.argv[0]
path = path[0 : path.index('GP') ]
db = pw.SqliteDatabase(f'{path}GP/db/THS_F10.db')

# 同花顺-- 机构持仓 (主力持仓)
class THS_JGCC(pw.Model):
    code = pw.CharField() #股票代码
    name = pw.CharField() #股票名称

    date1 = pw.CharField(null=True) # 日期(年报、季报、中报等)
    orgNum1 = pw.IntegerField(null=True) # 机构数量
    totalRate1 = pw.FloatField(null=True) #持仓比例
    change1 = pw.IntegerField(null=True) #较上期变化 (万股)

    date2 = pw.CharField(null=True) # 日期(年报、季报、中报等)
    orgNum2 = pw.IntegerField(null=True)
    totalRate2 = pw.FloatField(null=True) #持仓比例
    change2 = pw.IntegerField(null=True) #较上期变化 (万股)

    date3 = pw.CharField(null=True) # 日期(年报、季报、中报等)
    orgNum3 = pw.IntegerField(null=True)
    totalRate3 = pw.FloatField(null=True) #持仓比例
    change3 = pw.IntegerField(null=True) #较上期变化 (万股)

    date4 = pw.CharField(null=True) # 日期(年报、季报、中报等)
    orgNum4 = pw.IntegerField(null=True)
    totalRate4 = pw.FloatField(null=True) #持仓比例
    change4 = pw.IntegerField(null=True) #较上期变化 (万股)

    date5 = pw.CharField(null=True) # 日期(年报、季报、中报等)
    orgNum5 = pw.IntegerField(null=True)
    totalRate5 = pw.FloatField(null=True) #持仓比例
    change5 = pw.IntegerField(null=True) #较上期变化 (万股)

    class Meta:
        database = db
        table_name = '机构持仓'


# 同花顺--行业对比（排名）
class THS_HYDB(pw.Model):
    code = pw.CharField() #股票代码
    name = pw.CharField() #股票名称
    hyDJ = pw.CharField(null=True) # 行业等级（二级 、 三级）
    hyName = pw.CharField(null=True) # 行业名称
    hyTotal = pw.IntegerField(null=True) # 行业中股票总数量

    mgsyPM = pw.IntegerField(null=True) #每股收益排名
    mgjzcPM = pw.IntegerField(null=True) #每股净资产排名
    mgxjlPM = pw.IntegerField(null=True) #每股现金流排名
    jlrPM = pw.IntegerField(null=True) #净利润排名
    yyzslPM = pw.IntegerField(null=True) #营业总收入排名
    zgbPM = pw.IntegerField(null=True) #总股本排名

    zhPM = pw.IntegerField(null = True) #综合排名

    class Meta:
        database = db
        table_name = '行业对比'

# 同花顺--行业对比2（排名）
class THS_HYDB_2(pw.Model):
    code = pw.CharField() #股票代码
    name = pw.CharField() #股票名称
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
        table_name = '行业对比_2'        

# 同花顺--股东
class THS_GD(pw.Model):
    code = pw.CharField() #股票代码
    name = pw.CharField() #股票名称

    ltgdTop10Rate = pw.FloatField(null = True) #前十大流通股东占比 %

    class Meta:
        database = db
        table_name = '股东'
        
# 同花顺--最新动态
class THS_Newest(pw.Model):
    code = pw.CharField() #股票代码
    name = pw.CharField() #股票名称
    zsz = pw.IntegerField() #总市值 （亿元）
    liangDian = pw.CharField()  #公司亮点
    class Meta:
        database = db
        table_name = '最新动态'
    

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
    rs['THS_GD'] = THS_GD.get_or_none(THS_GD.code == code)
    rs['THS_JGCC'] = THS_JGCC.get_or_none(THS_JGCC.code == code)
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


db4 = pw.SqliteDatabase(f'{path}/GP/db/LHB.db')
class TdxLHB(pw.Model):
    day = pw.CharField(column_name = '日期' )
    code = pw.CharField()
    name = pw.CharField()
    title = pw.CharField(column_name = '上榜类型', null=True)
    price = pw.FloatField(column_name = '收盘价', null=True)
    zd = pw.FloatField(column_name = '涨跌幅' , null=True)
    #vol = pw.IntegerField(column_name = '成交量_万' , null=True) # 万股
    cjje = pw.DecimalField(column_name = '成交额_亿' , null=True, decimal_places = 1, max_digits = 10) # 亿元
    
    mrje = pw.DecimalField(column_name = '买入金额_亿' , null=True, decimal_places = 1, max_digits = 10) #  (亿元)
    #mrjeRate = pw.IntegerField(column_name = '买入金额_占比' , null=True) #  (占总成交比例%)
    mcje = pw.DecimalField(column_name = '卖出金额_亿' , null=True, decimal_places = 1, max_digits = 10) #  (亿元)
    #mcjeRate = pw.IntegerField(column_name = '卖出金额_占比' , null=True) #  (占总成交比例%)
    jme = pw.DecimalField(column_name = '净买额_亿' , null=True, decimal_places = 1, max_digits = 10) #  (亿元)
    famous = pw.CharField(column_name = '知名游资' , null=True)
    class Meta:
        database = db4


# 大单流入流出情况
db5 = pw.SqliteDatabase(f'{path}/GP/db/THS_DDBS.db')
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

voldb = pw.SqliteDatabase(f'{path}GP/db/TdxVolPM.db')
class TdxVolPMModel(pw.Model):
    code = pw.CharField() #股票代码
    name = pw.CharField() #股票名称
    day = pw.IntegerField() # 日期
    amount = pw.FloatField() #成交额 （亿元）
    pm = pw.IntegerField() #全市成交排名

    class Meta:
        database = voldb
        table_name = '成交额排名'

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

db_ztfupan = pw.SqliteDatabase(f'{path}GP/db/KPL_ZT_FuPan.db')
class KPL_ZT(pw.Model):
    code = pw.CharField()
    name = pw.CharField(null = True)
    day = pw.CharField()
    ztTime = pw.CharField(null = True, column_name='涨停时间')
    status = pw.CharField(null = True, column_name='状态')
    ztReason = pw.CharField(null = True, column_name='涨停原因')
    tag = pw.CharField(null=True)

    class Meta:
        database = db_ztfupan
        table_name = '开盘啦涨停复盘'

class KPL_SCQX(pw.Model):
    day = pw.CharField()
    zhqd = pw.IntegerField(column_name='综合强度')

    class Meta:
        database = db_ztfupan
        table_name = '开盘啦市场情绪'


db.create_tables([THS_JGCC, THS_HYDB, THS_GD, THS_GNTC, THS_Newest, THS_HYDB_2])
db2.create_tables([THS_Hot, THS_HotZH])
db3.create_tables([TaoGuBa_Remark])
db5.create_tables([THS_DDLR])
db_thszs.create_tables([THS_ZS, THS_ZS_ZD])
db_ztfupan.create_tables([KPL_ZT, KPL_SCQX])

    