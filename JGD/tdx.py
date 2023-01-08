import struct

# code = 600256
# return [ (date, open, high, low, close, amount:float, vol, reserse), ... ]
def readCodeFile(code : str):
    base = 'D:\\Program Files\\new_tdx2\\vipdoc\\'
    sh = 'sh\\lday\\sh'
    sz = 'sz\\lday\\sz'
    if code[0] == '6':
        path = base + sh + code + '.day'
    else:
        path = base + sz + code + '.day'
    f = open(path, 'rb')
    data = f.read()
    f.close()
    num = len(data) // 32
    items = [None] * num
    for i in range(num):
        item = struct.unpack_from('<5If2I', data, i * 32)
        items[i] = item
        print(item)
    return data



readCodeFile('600805')