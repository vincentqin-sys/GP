import os, struct
import ZT_Day

DB_CACHE_N = {}
for v in ZT_Day.DS:
    DB_CACHE_N[f'{v.code}-{v.next_day}'] = v

def loadOneDay(buf, offset):
    vals = []
    maxval = 0
    tm = struct.unpack_from('H', buf, offset)[0]
    year = tm // 2048 + 2004
    md = tm % 2048
    day = year * 10000 + md
    for i in range(0, 5):
        item = struct.unpack_from('2H7f', buf, offset + i * 32) # 时间, 开盘价, 最高价, 最低价, 收盘价, 成交额 成交量（股）, ??
        if maxval < item[3]:
            maxval = item[3]
        vals.append(item[5])
    
    avg = sum(vals)/len(vals)
    complete_m30 = 0
    if offset - 32 > 0:
        cc = struct.unpack_from('2H7f', buf, offset - 32)[5] #上一日收盘价
        maxval = (maxval - cc) * 100 / cc
        avg = (avg - cc) * 100 / cc
        complete_m30 = 1
    else:
        maxval = avg = 0
    return day, maxval, avg, complete_m30
    
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
    # print(code)
    while ofs < size and size > 32 * 4 * 12:
        day, zfh_m30, zfavg_m30, complete_m30 = loadOneDay(bs, ofs)
        info = findByNextDay(code, day)
        if info and info.complete_m30 == 0:
            info.zfh_m30 = zfh_m30
            info.zfavg_m30 = zfavg_m30
            info.complete_m30 = complete_m30
            info.save()
        ofs += 32 * 12 * 4
        

def loadDirFiles(basePath):
    if not os.path.exists(basePath):
        return
    bp = os.path.join(basePath, r'sh\fzline')
    for g in os.listdir(bp):
        f = os.path.join(bp, g)
        loadOneFile(f)
    bp = os.path.join(basePath, r'sz\fzline')
    for g in os.listdir(bp):
        f = os.path.join(bp, g)
        loadOneFile(f)

if __name__ == '__main__':
    BASE_PATH = r'D:\Program Files\new_tdx2\vipdoc'
    BASE_PATH2 = r'D:\Program Files (x86)\new_tdx\vipdoc'
    #loadOneFile(BASE_PATH2 + r'\sh\fzline\sh600006.lc5')
    
    loadDirFiles(BASE_PATH2)
    ZT_Day.db.close()