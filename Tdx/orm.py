import peewee as pw
import sys

path = sys.argv[0]
path = path[0 : path.index('GP') ]
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

class TdxLSModel(pw.Model):
    day = pw.IntegerField(column_name='日期')
    amount = pw.FloatField(column_name='成交额') # （亿元）
    upNum = pw.IntegerField(column_name='上涨家数', default=0)
    downNum = pw.IntegerField(column_name = '下跌家数', default=0)
    ztNum = pw.IntegerField(column_name='涨停数', default=0)
    lbNum = pw.IntegerField(column_name='连板数', default=0) #二板以上家数
    zgb = pw.IntegerField(column_name='最高板', default=0)
    dtNum = pw.IntegerField(column_name='跌停数', default=0)
    down7Num = pw.IntegerField(column_name='跌幅超百分之7个股数', default=0)

    class Meta:
        database = voldb
        table_name = '两市总体情况'


class TdxZTLBModel(pw.Model):
    day = pw.IntegerField()
    code = pw.CharField()
    name = pw.CharField()
    lbs = pw.IntegerField(column_name='几连板', default=0)
    lbIdx = pw.IntegerField(column_name='连板序号', default=0)
    lbNum = pw.IntegerField(column_name='当日连板数量', default=0)

    class Meta:
        database = voldb
        table_name = '连板股票'

class TdxVolTop50ZSModel(pw.Model):
    day = pw.IntegerField()
    vol = pw.IntegerField()
    zhangFu = pw.FloatField(column_name='涨幅')
    avgZhangFu = pw.FloatField(column_name='平均涨幅')

    class Meta:
        database = voldb
        table_name = '成交额Top50指数'

voldb.create_tables([TdxVolPMModel, TdxLSModel, TdxVolTop50ZSModel])
