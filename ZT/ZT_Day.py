import os, struct
import peewee as pw

db = pw.SqliteDatabase('D:/vscode/GP/db/ZT.db')

class ZTZB(pw.Model):
    code = pw.CharField()
    day = pw.IntegerField()
    tag = pw.CharField() # 'ZT' or 'ZB'
    drzf = pw.FloatField(column_name = '当日涨幅')
    zfc_1 = pw.FloatField(column_name = '次日收盘涨幅', default = 0)
    zfh_1 = pw.FloatField(column_name = '次日最高涨幅', default = 0)
    dnb = pw.IntegerField(column_name = '第几板')
    next_day = pw.IntegerField(default = 0, column_name = '下一日期' )  # 下一日期
    complete = pw.IntegerField(default = 0) #  上面几列数据是否完整
    
    zfh_m30 = pw.FloatField(column_name = '次日30分钟内最高涨幅', default = 0)
    zfavg_m30 = pw.FloatField(column_name = '次日30分钟内平均涨幅', default = 0)  # 每5分钟收盘价平均值
    complete_m30 = pw.IntegerField(default = 0) #  上面两列数据是否完整
    class Meta:
        database = db
    
db.create_tables([ZTZB])
DS = ZTZB.select().order_by(ZTZB.code.asc(), ZTZB.day.asc())
DB_CACHE = {}
for v in DS:
    DB_CACHE[f'{v.code}-{v.day}'] = v
print('DB Cache Size:', len(DB_CACHE))


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
    
def save(info):
    if info['day'] < 20210901: # ingore old data
        return
    k = f'{info["code"]}-{info["day"]}'
    v = DB_CACHE.get(k, None)
    if not v:
      ZTZB.create(**info)
      return
    if v.complete or info['complete'] == 0:
        return
    v.complete = info['complete']
    v.drzf = info['drzf']
    v.zfc_1 = info['zfc_1']
    v.zfh_1 = info['zfh_1']
    v.dnb = info['dnb']
    v.next_day = info['next_day']
    v.save()
    
def findDnb(code, day):
    k = f'{code}-{day}'
    v = DB_CACHE.get(k, None)
    if not v:
        return (0, None);
    return (v.dnb, v.tag)

count = 0
    
def loadOneFile(absPath):
    global count
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
    dnbList = [ findDnb(code, datas[0][0]) ]
    for i in range(1, len(datas)):
        zt = isZTOrZB(code, datas[i - 1], datas[i])
        if not zt:
            dnbList.append((0, None,))
            continue
        count += 1
        print('[%05d]'%count, zt, code, datas[i][0])
        if dnbList[i - 1][1] == 'ZT':
            dnb = dnbList[i - 1][0] + 1
        else:
            dnb = 1
        dnbList.append((dnb, zt))
        drzf = (datas[i][4] - datas[i - 1][4]) * 100 / datas[i - 1][4]
        info = {"code" : code, 'day': datas[i][0], 'tag': zt, 'drzf': drzf, 'dnb': dnb, 'complete': 0, 'zfc_1': 0, 'zfh_1': 0}
        if i < len(datas) - 1:
            zfc_1 = (datas[i + 1][4] - datas[i][4]) * 100 / datas[i][4]
            zfh_1 = (datas[i + 1][2] - datas[i][4]) * 100 / datas[i][4]
            next_day = datas[i + 1][0]
            info['zfc_1'] = zfc_1
            info['zfh_1'] = zfh_1
            info['next_day'] = next_day
            info['complete'] = 1
        save(info)

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
    
if __name__ == '__main__':
    BASE_PATH = r'D:\Program Files\new_tdx2\vipdoc'
    BASE_PATH2 = r'D:\Program Files (x86)\new_tdx\vipdoc'
    #loadOneFile(BASE_PATH2 + r'\sh\lday\sh600006.day')

    loadDirFiles(BASE_PATH2)
    db.close()


