#加载行业对比数据

import os, json
import orm
from bs4 import BeautifulSoup

BASE_PATH = 'D:/ths/'

# 行业信息
hyInfos = {} # {行业名称: [关联股票, ...] }
hyInfosKey = {}

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
    f = toFloat(s)
    return int(f)

def listHydbFiles():
    tag = '同行比较'
    fs = os.listdir(BASE_PATH)
    rs = [BASE_PATH + f for f in fs if tag in f ]
    return rs

def loadDatas(txt, cols, hydj, hy):
    global hyInfos
    if hy in hyInfos:
        return
    js = json.loads(txt)
    ks = sorted(js.keys())
    lastDate = ks[len(js) - 1]
    data = js[lastDate]
    hyInfos[hy] = []
    # 生成一级行业
    hy1 = hy.split('--')[0].strip()
    if hy1 in hyInfos:
        hy1Info = hyInfos[hy1]
        hy1InfoKey = hyInfosKey[hy1]
    else:
        hy1Info = hyInfos[hy1] = []
        hy1InfoKey = hyInfosKey[hy1] = {}
    for d in data:
        obj = { 'hy': hy, 'hydj': hydj }
        for c in cols:
            obj[c[0]] = d[c[1]] if c[1] <= 1  else float(d[c[1]])
        #print(obj)
        hyInfos[hy].append(obj)
        if obj['code'] not in hy1InfoKey:
            obj1 = obj.copy()
            obj1['hy'] = hy1
            obj1['hydj'] = '一级'
            hy1InfoKey[obj['code'] ] = obj1
            hy1Info.append(obj1)
            #print(obj1)

# 行业对比
def loadFile(fileName):
    f = open(fileName, 'r', encoding= 'gbk')
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

    if len(hyNames) == 0:
        print('Load 行业对比: ', fileName, '未找到行业排名信息')
        return
    print('Load 行业对比: ', fileName, hyNames)

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
    colInfos = [('code', 0), ('name', 1), ('mgsy', 2), ('mgjzc', 3), ('mgxjl', 4), ('jlr', 5), ('yyzsl', 6), ('zgb', 11)]
    
    p1 = soup.select('#fieldsChartData') # 三级行业数据
    if len(p1) == 1:
        p1x = p1[0]
        txt = p1x['value']
        loadDatas(txt, colInfos, *hyNames[0])
    p2 = soup.select('#fieldsChart2Data') # 二级行业数据
    if len(p2) == 1:
        p2x = p2[0]
        txt = p2x['value']
        loadDatas(txt, colInfos, *hyNames[len(hyNames) - 1])
    
    if len(p1) != 1 and len(p2) != 1:
        print('Load Error: 行业对比 ', fileName, '未找到二级、三级行业数据')
        raise Exception()

#计算综合排名
def calcHyPM(datas):
    rs = sorted(datas, key = lambda d : d['mgsy'], reverse=True)
    for idx, dt in enumerate(rs):
        dt['mgsyPM'] = idx + 1
    rs = sorted(datas, key = lambda d : d['jlr'], reverse=True)
    for idx, dt in enumerate(rs):
        dt['jlrPM'] = idx + 1
    kf = lambda d : d['mgsyPM'] * 0.4 + d['jlrPM'] * 0.6
    rs = sorted(datas, key = kf)
    for idx, dt in enumerate(rs):
        dt['zhpm'] = idx + 1
    for d in datas:
        del d['mgsyPM']
        del d['jlrPM']

#计算综合排名
def calcAllPM():
    keys = sorted(hyInfos.keys())
    for k in keys:
        datas = hyInfos[k]
        #计算数量
        for d in datas:
            d['hysl'] = len(datas)
        calcHyPM(datas)

def saveDB():
    keys = sorted(hyInfos.keys())
    for k in keys:
        datas = hyInfos[k]
        with orm.db.atomic():
            orm.THS_HYDB_2.insert_many(datas).execute()

def loadAllFiles():
    files =  listHydbFiles()
    for f in files:
        loadFile(f)
    calcAllPM()
    saveDB()

def loadOneFile(code):
    f = BASE_PATH + code + '-同行比较.html'
    loadFile(f)
    calcAllPM()
    saveDB()

if __name__ == '__main__':
    loadAllFiles()
    #loadOneFile('002080')