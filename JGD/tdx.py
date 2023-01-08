import struct, peewee as pw

db = pw.SqliteDatabase('JGD.db') #交割单

class CodeInfo(pw.Model):
    code = pw.CharField(max_length=6)
    name = pw.CharField(max_length=16, null=True)
    day = pw.CharField(max_length=12)
    bs = pw.CharField(max_length=1) # 'B' is buy, 'S' is sell
    price = pw.IntegerField(default=0)
    remark = pw.CharField(null=True)

    class Meta:
        database = db
    
CodeInfo.create_table()

# code = 600256
# return [ (date, open, high, low, close, amount, vol, BBI, MA5, 换手率, 0, 0), ... ]
def readCodeFile(code : str):
    base = 'D:/Program Files/new_tdx2/T0002/dlls/'
    path = base + code + '-5'
    f = open(path, 'rb')
    data = f.read()
    f.close()
    num = len(data) // 48
    items = [None] * num
    for i in range(num):
        item = struct.unpack_from('<12I', data, i * 48)
        items[i] = (item[0] + 19000000, item[1], item[2], item[3], item[4], item[5], item[6], item[7], item[8], item[9])
        print(items[i])
    return data



readCodeFile('002591')