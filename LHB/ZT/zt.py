import os, struct
import peewee as pw

db = pw.SqliteDatabase('ZT.db')

class ZTZB(pw.Model):
    code = pw.CharField()
    day = pw.IntegerField()
    tag = pw.CharField() # 'ZT' or 'ZB'
    zfc_1 = pw.FloatField(null = True) # 1日收盘涨幅
    zfh_1 = pw.FloatField(null = True) # 1日最高涨幅
    dnb = pw.IntegerField() # 这是第几板/炸板
    complete = pw.IntegerField(default = 0) # 数据是否完整
    
    class Meta:
        database = db
    
db.create_tables([ZTZB])
dbdatas = ZTZB.select().order_by(ZTZB.code.asc(), ZTZB.day.asc()).execute()
print(dbdatas)


# 涨停或炸板
def isZTOrZB(code, v1, v2):
    tag = code[0 : 2]
    zf = 0.1
    if tag == '68' or tag == '30':
        zf = 0.2
    v1c, v2c, v2h = v1[4], v2[4], v2[2]
    v1cb = int(v1c * (1 + zf) + 0.5)
    v1ce = int(v1c * (1 + zf + 0.004) + 0.5)
    if v1cb <= v2h and v2h <= v1ce:
        return 'ZT' if v2c == v2h else 'ZB'
    return False

def getCode(absPath):
    name = os.path.basename(absPath)
    cc = name[2 : 4]
    tag = name[0 : 2]
    if tag == 'sh' and (cc == '60' or cc == '68'):
        return name[2 : 8]
    if tag == 'sz' and (cc == '30' or cc == '00'):
        return name[2 : 8]
    return None
    
def loadOneFile(absPath):
    code = getCode(absPath)
    if not code:
        return
    f = open(absPath, 'rb')
    bs = f.read()
    size = f.tell()
    f.close()
    ofs = 0
    datas = []
    while ofs < size:
        item = struct.unpack_from('8i', bs, ofs) # 日期, 开盘价, 最高价, 最低价, 收盘价, ??, 成交量（股）, ??
        ofs += 8 * 4
        datas.append(item)
        # print(item)
    for i in range(1, len(datas)):
        zt = isZTOrZB(code, datas[i - 1], datas[i])
        if not zt:
            continue
        print(zt, ' -->', datas[i])
        ZTZB.create(code = code, day = datas[i][0], tag = zt, )

def loadDirFiles(basePath):
    if not os.path.exists(basePath):
        return
    bp = os.path.join(basePath, r'sh\lday')
    for g in os.listdir(bp):
        f = os.path.join(bp, g)
        loadOneFile(f)
    bp = os.path.join(basePath, r'sz\lday')
    for g in os.listdir(bp):
        f = os.path.join(bp, g)
        loadOneFile(f)
    

BASE_PATH = r'D:\Program Files\new_tdx2\vipdoc'

loadOneFile(BASE_PATH + r'\sz\lday\sz003027.day')