import os, json
from bs4 import BeautifulSoup
import orm

BASE_PATH = 'D:/VSCode/THS/'

# str to float, strip not numbers
def toFloat(s):
    s = str(s)
    try:
        return float(s)
    except:
        pass
    ss = ''
    for i in s:
        if (i >= '0' and i <= '9') or (i == '.'):
            ss += i
    if ss == '':
        return 0
    return float(ss)

# str to int, strip not numbers
def toInt(s):
    s = str(s)
    try:
        return int(s)
    except:
        pass
    ss = ''
    for i in s:
        if (i >= '0' and i <= '9') or (i == '.'):
            ss += i
    if ss == '':
        return 0
    return int(ss)

#-----------------------机构持仓---------------------------------
# 机构持仓 加载  
def loadJGCC(code):
    f = open(BASE_PATH + code + '主力持仓', 'r', encoding= 'utf8')
    txt = f.read()
    f.close()
    js = json.loads(txt)
    
    obj = orm.THS_Newest.get_or_none(orm.THS_Newest.code == code)
    name = obj.name if obj else None

    if ('status_code' not in js) or (js['status_code'] != 0 or ('data' not in js)):
        print('Load Error: ', '主力持仓', code, name)
        raise Exception()
    rs = { 'code' : code , 'name': name}
    idx = 0
    for it in js['data']:
        if it['is_updating']:
            continue
        idx += 1
        k = str(idx)
        rs['date' + k] = it['date']
        rs['orgNum' + k] = it['org_num']
        rs['totalRate' + k] = toFloat(it['total_rate'])
        rs['change' + k] = toInt(it['total_holder_change']) // 10000 #  万股
        
    idx += 1
    while idx <= 5:
        k = str(idx)
        rs['date' + k] = None
        rs['orgNum' + k] = None
        rs['totalRate' + k] = None
        rs['change' + k] = None
        idx += 1
    # print(rs)
    saveZLCQ(rs)
    print('Load 机构持仓: ', code, name)

def saveZLCQ(zlcq : dict):
    obj = orm.THS_JGCC.get_or_none(orm.THS_JGCC.code == zlcq['code'])
    if (obj):
        obj.__data__.update(**zlcq)
        obj.save()
    else:
        orm.THS_JGCC.create(**zlcq)

#------------------------行业对比-(排名)--------------------------------
def sortHYDB_PM(txt, cols):
    js = json.loads(txt)
    ks = sorted(js.keys())
    lastDate = ks[len(js) - 1]
    #print('lastDate=', lastDate)
    data = js[lastDate]
    for i in cols:
        kf = lambda x : float(x[i])
        data = sorted(data, reverse = True, key = kf)
        for idx, dt in enumerate(data):
            dt[i] = idx + 1
    return data

# 计算综合排名
def calcZH_PM(datas):
    kf = lambda d : d['mgsyPM'] * 0.4 + d['jlrPM'] * 0.6
    rs = sorted(datas, key = kf)
    for idx, dt in enumerate(rs):
        dt['zhPM'] = idx + 1

def saveHYDB(zlcq : dict):
    obj = orm.THS_HYDB.get_or_none((orm.THS_HYDB.code == zlcq['code']) & (orm.THS_HYDB.hyDJ == zlcq['hyDJ']))
    if (obj):
        obj.__data__.update(zlcq)
        obj.save()
    else:
        orm.THS_HYDB.create(**zlcq)

def buildHYDBList(datas, colInfos, hy):
    rs = []
    for data in datas:
        info = {}
        for name, idx  in colInfos:
            info[name] = data[idx]
        info['hyDJ'] = hy[0]
        info['hyName'] = hy[1]
        info['hyTotal'] = len(datas)
        rs.append(info)
    return rs

# 行业对比
def loadHYDB(code):
    f = open(BASE_PATH + code + '行业地位', 'r', encoding= 'gbk')
    txt = f.read()
    f.close()
    soup = BeautifulSoup(txt, 'html5lib')

    ps = soup.select('.threecate') # 三级、二级 行业分类 <p>
    hyNames = []
    for p in ps:
        nn = ''.join(p.stripped_strings) # 三级行业分类：纺织服饰 -- 服装家纺 -- 非运动服装 （共37家） |  二级行业分类：纺织服饰 -- 服装家纺 （共63家）
        dj = nn[0 : 2] # 三级 | 二级
        hy = nn[7 : nn.find('（')].strip() # 纺织服饰 -- 服装家纺 -- 非运动服装
        hyNames.append((dj, hy))
        #print((dj, hy))

    if len(hyNames) == 0:
        print('Load 行业对比: ', code, '未找到行业排名信息')
        return
    print('Load 行业对比: ', code, hyNames)

    childs = soup.select('#sortNav > li')
    titles = ('每股收益', '每股净资产', '每股现金流', '净利润', '营业总收入', '总资产', '净资产收益率', '股东权益比例', '销售毛利率', '总股本')
    if len(childs) != len(titles):
        print('行业对比 文件内容发生变更，请修改代码')
        raise BaseException()
    for i, it in enumerate(childs):
        if titles[i] != it.string.strip():
            print('行业对比 文件内容发生变更，请修改代码')
            raise BaseException()
    
    cols = range(2, 2 + 10) # 共12列数据，前2列为 股票代码, 股票名称，后10列为数据，顺序等于titles
    colInfos = [('code', 0), ('name', 1), ('mgsyPM', 2), ('mgjzcPM', 3), ('mgxjlPM', 4), ('jlrPM', 5), ('yyzslPM', 6), ('zgbPM', 11)]
    p1 = soup.select('#fieldsChartData') # 三级行业数据
    if len(p1) == 1:
        p1x = p1[0]
        data = p1x['value']
        d3 = sortHYDB_PM(data, cols)
        d3n = buildHYDBList(d3, colInfos, hyNames[0])
        calcZH_PM(d3n)
        #print('d3=', d3n)
        for it in d3n:
            saveHYDB(it)

    p2 = soup.select('#fieldsChart2Data') # 二级行业数据
    if len(p2) == 1:
        p2x = p2[0]
        data = p2x['value']
        d2 = sortHYDB_PM(data, cols)
        d2n = buildHYDBList(d2, colInfos, hyNames[len(hyNames) - 1])
        calcZH_PM(d2n)
        #print('d2=', d2n)
        for it in d2n:
            saveHYDB(it)

    if (len(p1) != 1) and (len(p2) != 1):
        print('Load Error: 行业对比 ', code, '未找到二级、二级行业数据')
        raise Exception()
    
#-------------------------股东---------------------------------
def loadGD(code):
    f = open(BASE_PATH + code + '股东研究', 'r', encoding= 'gbk')
    txt = f.read()
    f.close()
    tag = '流通股比：<em>'
    pos = txt.find(tag)
    if pos < 0:
        print('Load Error: 股东研究 ', code, '未找到占流通股比标识')
        raise Exception()
    pos += len(tag)
    rrs = txt[pos : pos + 10]
    rate = toFloat(rrs)

    tag = '<title>'
    pos = txt.index(tag)
    pos += len(tag)
    title = txt[pos : pos + 20]
    idx = title.index('(')
    name = title[0 : idx]
    code = title[idx + 1 : idx + 7]
    print('Load 股东研究：', code, name, '前十大流通股东点比', rate)
    obj = {'code' : code, 'name': name, 'ltgdTop10Rate' : rate}
    saveGD(obj)
    return obj

def saveGD(gd : dict):
    obj = orm.THS_GD.get_or_none(orm.THS_GD.code == gd['code'])
    if (obj):
        obj.__data__.update(gd)
        obj.save()
    else:
        orm.THS_GD.create(**gd)

#------------------------最新动态---------------------------------
def loadNewest(code):
    f = open(BASE_PATH + code + '最新动态', 'r', encoding= 'gbk')
    txt = f.read()
    f.close()
    tag = '<title>'
    pos = txt.index(tag)
    pos += len(tag)
    title = txt[pos : pos + 20]
    idx = title.index('(')
    name = title[0 : idx]
    code = title[idx + 1 : idx + 7]
    print('Load 最新动态：', code, name)
    obj = {'code' : code, 'name': name}
    saveNewest(obj)
    return obj
    
def saveNewest(gd : dict):
    obj = orm.THS_Newest.get_or_none(orm.THS_Newest.code == gd['code'])
    if (obj):
        obj.__data__.update(gd)
        obj.save()
    else:
        orm.THS_Newest.create(**gd)
        
#------------------------概念题材---------------------------------
def loadGNTC(code):
    f = open(BASE_PATH + code + '概念题材', 'r', encoding= 'gbk')
    txt = f.read()
    f.close()
    tag = '<title>'
    pos = txt.index(tag)
    pos += len(tag)
    title = txt[pos : pos + 20]
    idx = title.index('(')
    name = title[0 : idx]
    code = title[idx + 1 : idx + 7]
    print('Load 概念题材：', code, name)
    obj = {'code' : code, 'name': name}
    saveGNTC(obj)
    return obj
    
def saveGNTC(gd : dict):
    obj = orm.THS_GNTC.get_or_none(orm.THS_GNTC.code == gd['code'])
    if (obj):
        obj.__data__.update(gd)
        obj.save()
    else:
        orm.THS_GNTC.create(**gd)
        
#---------------------------------------------------------------------
        
#---------------------------------------------------------------------
#info = loadHYDB('002762')
#gd = loadGD('002762')
#loadJGCC('002762', info['name'])

def listFiles(tag = None):
    fs = os.listdir(BASE_PATH)
    fs = sorted(fs)
    if not tag:
        return fs
    ff = lambda n : tag in n
    return filter(ff, fs)
    
def loadOneFile(fileName):
    code = fileName[0 : 6]
    tag = fileName[6 : ]
    
    if tag == '股东研究':
        obj = orm.THS_GD.get_or_none(orm.THS_GD.code == code)
        if not obj:
            gd = loadGD(code)
    elif tag == '行业对比':
        obj = orm.THS_HYDB.get_or_none(orm.THS_HYDB.code == code)
        if not obj:
            loadHYDB(code)
    elif tag == '主力持仓':
        obj = orm.THS_JGCC.get_or_none(orm.THS_JGCC.code == code)
        if not obj:
            loadJGCC(code)
    elif tag == '最新动态':
        obj = orm.THS_Newest.get_or_none(orm.THS_Newest.code == code)
        if not obj:
            loadNewest(code)


fs = listFiles('最新动态')
for idx, fn in enumerate(fs):
    try:
        print('[%04d]' % (idx + 1))
        loadOneFile(fn)
    except:
        print('Load Exception: ', fn)