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


voldb.create_tables([TdxVolPMModel])
