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
    upNum = pw.IntegerField(column_name='上涨家数')
    downNum = pw.IntegerField(column_name = '下跌家数')
    zts = pw.IntegerField(column_name='涨停数')
    lbs = pw.IntegerField(column_name='连板数') #二板以上家数
    zgb = pw.IntegerField(column_name='最高板')
    dts = pw.IntegerField(column_name='跌停数')

    class Meta:
        database = voldb
        table_name = '两市总体情况'


voldb.create_tables([TdxVolPMModel, TdxLSModel])
