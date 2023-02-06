import peewee as pw


db = pw.SqliteDatabase('D:/vscode/GP/db/THS_F10.db')


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
    #公司亮点
    class Meta:
        database = db
        table_name = '最新动态'
    

# 同花顺--概念题材
class THS_GNTC(pw.Model):
    code = pw.CharField() #股票代码
    name = pw.CharField() #股票名称
    gn = pw.CharField(null=True) # 常规概念，每概概念之间用/分隔

    class Meta:
        database = db
        table_name = '概念题材'



db.create_tables([THS_JGCC, THS_HYDB, THS_GD, THS_Newest, THS_GNTC])