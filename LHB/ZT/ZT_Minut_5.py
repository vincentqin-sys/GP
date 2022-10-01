import os, struct
import ZT_Day

for v in ZT_Day.DS:
    DB_CACHE_N[f'{v.code}-{v.next_day}'] = v

def loadOneDay(buf, offset):
    vals = []
    maxval = 0
    for i in range(0, 5):
        item = struct.unpack_from('2s7f', bs, ofs + i * 32) # 时间, 开盘价, 最高价, 最低价, 收盘价, 成交额 成交量（股）, ??
        if maxval < item[3]:
            maxval = item[3]
        vals.append(item[5])
    tm = struct.unpack_from('s')[0]
    year = tm // 2048 + 2004
    md = tm % 2048
    day = year * 10000 + md
    return day, maxval, sum(vals)/len(vals)
    
def findByNextDay(code, next_day):
    k = f'{code}-{next_day}'
    v = DB_CACHE_N.get(k, None)
    return v

def loadOneFile(absPath):
    global count
    code = ZT_Day.getCode(absPath)
    if not code:
        return
    f = open(absPath, 'rb')
    bs = f.read()
    size = f.tell()
    f.close()
    ofs = 0
    while ofs < size:
        day, zfh_m30, zfavg_m30 = loadOneDay(bs, ofs)
        info = findByNextDay(code, day)
        if info and info.complete_m30 == 0:
            info.zfh_m30 = zfh_m30
            info.zfavg_m30 = zfavg_m30
            info.complete_m30 = 1
            info.save()
        ofs += 32 * 12 * 4
        

def loadDirFiles(basePath):
    if not os.path.exists(basePath):
        return
    bp = os.path.join(basePath, r'sh\fzday')
    for g in os.listdir(bp):
        f = os.path.join(bp, g)
        loadOneFile(f)
    bp = os.path.join(basePath, r'sz\fzday')
    for g in os.listdir(bp):
        f = os.path.join(bp, g)
        loadOneFile(f)

if __name__ == '__main__':
    BASE_PATH = r'D:\Program Files\new_tdx2\vipdoc'
    BASE_PATH2 = r'D:\Program Files (x86)\new_tdx\vipdoc'
    loadDirFiles(BASE_PATH2)
    db.close()
    #loadOneFile(BASE_PATH + r'\sz\lday\sz003027.day')