import struct, peewee as pw

db = pw.SqliteDatabase('D:/vscode/GP/db/JGD.db') #交割单

class JGD(pw.Model):
    code = pw.CharField(max_length=6)
    name = pw.CharField(max_length=20, null=True)
    buyDay = pw.IntegerField(null=True)
    buyPrice = pw.FloatField(default=0, null=True)
    sellDay = pw.IntegerField(null=True)
    sellPrice = pw.FloatField(default=0, null=True)
    remark = pw.CharField(null=True)
    
    class Meta:
        database = db
        table_name = '交割单'

class ZTDT(pw.Model):
    code = pw.CharField(max_length=6)
    name = pw.CharField(max_length=20, null=True)
    day = pw.IntegerField(null=True)
    lianBan = pw.IntegerField(null=True)
    tag = pw.CharField(null=True) # ZT or DT or ZTZB
    remark = pw.CharField(null=True)
    
    class Meta:
        database = db
        table_name = '涨跌停'
    
JGD.create_table()
ZTDT.create_table()

# code = 600256  period = 'day' or 'week'
# fuQuan = FQ or CQ or LASTEST
# return [ (date, open, high, low, close, amount, vol, BBI, MA5, 换手率, 0, 0), ... ]
def read_code_File(code : str, period : str, fuQuan : str):
    #base = 'D:/Program Files/new_tdx2/T0002/dlls/'
    if 'LASTEST' == fuQuan:
        base = base = f'D:/Program Files (x86)/new_tdx/T0002/dlls/cache/'
    else:
        base = f'D:/Program Files (x86)/new_tdx/T0002/dlls/cache-{fuQuan}/'
    path = base + code
    dd = 1
    if period == 'week':
        path += '-6'
        dd = 5
    else:
        path += '-5'
    f = open(path, 'rb')
    data = f.read()
    f.close()
    num = len(data) // 48
    items = [None] * num
    for i in range(num):
        item = struct.unpack_from('<12I', data, i * 48)
        items[i] = (item[0] + 19000000, item[1], item[2], item[3], item[4], item[5], item[6], item[7], item[8], item[9] // dd)
        #print(items[i])
    return items

# period = 'day' or 'week'
# fuQuan = 'FQ' or 'CQ' or 'LASTEST'
def load_code(code : str, day : int, period : str, fuQuan : str, maxNum: int = 100 ):
    print('load_code:', code, day, period, fuQuan, maxNum)
    datas = read_code_File(code, period, fuQuan)
    if len(datas) > 0:
        print('load code:', code, period, len(datas), datas[0][0])
    idx = 0
    for i in range(len(datas)):
        if datas[i][0] >= day:
            idx = i
            print('find start day: ', datas[i][0], day)
            break
    beginIdx = 0
    endIdx = len(datas)
    if idx >= maxNum // 2:
        beginIdx = idx - maxNum // 2
    endIdx = beginIdx + maxNum
    if endIdx > len(datas):
        endIdx = len(datas)
    result = []
    for i in range(beginIdx, endIdx):
        it = datas[i]
        vv = {'date': it[0], 'open': it[1], 'high': it[2], 'low': it[3], 'close': it[4], 'amount': it[5], 'vol': it[6], 'bbi': it[7], 'ma5': it[8], 'rate': it[9] }
        result.append(vv)
        
    #print(result)
    return result

#load_code('002591', 20220824, 'day', 5)