import struct, peewee as pw

db = pw.SqliteDatabase('JGD.db') #交割单

class JGD(pw.Model):
    code = pw.CharField(max_length=6)
    name = pw.CharField(max_length=16, null=True)
    buyDay = pw.CharField(max_length=12)
    buyPrice = pw.IntegerField(default=0)
    sellDay = pw.CharField(max_length=12)
    sellPrice = pw.IntegerField(default=0)
    remark = pw.CharField(null=True)

    class Meta:
        database = db
        table_name = '交割单'
    
JGD.create_table()

# code = 600256
# return [ (date, open, high, low, close, amount, vol, BBI, MA5, 换手率, 0, 0), ... ]
def read_code_File(code : str):
    #base = 'D:/Program Files/new_tdx2/T0002/dlls/'
    base = 'D:/Program Files (x86)/new_tdx/T0002/dlls/'
    path = base + code + '-5'
    f = open(path, 'rb')
    data = f.read()
    f.close()
    num = len(data) // 48
    items = [None] * num
    for i in range(num):
        item = struct.unpack_from('<12I', data, i * 48)
        items[i] = (item[0] + 19000000, item[1], item[2], item[3], item[4], item[5], item[6], item[7], item[8], item[9])
        #print(items[i])
    return items

# 
def load_code(code : str, day : int, maxNum: int = 100 ):
    datas = read_code_File(code)
    idx = 0
    for i in range(len(datas)):
        if datas[i][0] == day:
            idx = i
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
        
    print(result)
    return result

load_code('002591', 20220824, 100)