import os, json, sys
from bs4 import BeautifulSoup
import pyautogui as pa
import time

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

from Download import fiddler
from THS import orm

BASE_PATH = 'D:/ths/f10/'

if not os.path.exists(BASE_PATH):
    os.makedirs(BASE_PATH)

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

def saveDB(ormCls, zlcq : dict):
    obj = ormCls.get_or_none(ormCls.code == zlcq['code'])
    if (obj):
        obj.__data__.update(**zlcq)
        obj.save()
    else:
        ormCls.create(**zlcq)

#机构持仓
class LoadJGCC:
    def load(code):
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
        saveDB(orm.THS_JGCC, rs)
        print('Load 机构持仓: ', code, name)

#股东
class LoadGD:
    def load(code):
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
        saveDB(orm.THS_GD, obj)
        return obj

#最新动态
class LoadNewest:
    def load(code):
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
        obj = {'code' : code, 'name': name}

        tag = '总市值：'
        pos = txt.index(tag) + len(tag)
        zszTxt = txt[pos : pos + 100]
        if 'stockzsz' not in zszTxt:
            print('Load 最新动态: Not find stockzsz')
            raise Exception()
        pos = zszTxt.index('stockzsz') + len('stockzsz')
        zszTxt = zszTxt[pos : ]
        zsz = toInt(zszTxt)
        obj['zsz'] = zsz

        idx = txt.find('公司亮点：')
        if idx < 0:
            print('Load 最新动态: Not find 公司亮点')
            raise Exception()
        idx = txt.find('title="', idx) + 7
        idx2 = txt.find('"', idx)
        liangDian = txt[idx : idx2]
        obj['liangDian'] = liangDian
        
        print('Load 最新动态：', obj)
        saveDB(orm.THS_Newest, obj)
        return obj

#加载行业对比数据
class LoadHYDB:
    def __init__(self) -> None:
        # 行业信息
        self.hyInfos = {} # {行业名称: [关联股票, ...] }
        self.hyInfosKey = {}

    def listHydbFiles(self):
        tag = '同行比较'
        fs = os.listdir(BASE_PATH)
        rs = [BASE_PATH + f for f in fs if tag in f ]
        return rs

    def loadDatas(self, txt, cols, hydj, hy):
        if hy in self.hyInfos:
            return
        js = json.loads(txt)
        ks = sorted(js.keys())
        lastDate = ks[len(js) - 1]
        data = js[lastDate]
        self.hyInfos[hy] = []
        # 生成一级行业
        hy1 = hy.split('--')[0].strip()
        if hy1 in self.hyInfos:
            hy1Info = self.hyInfos[hy1]
            hy1InfoKey = self.hyInfosKey[hy1]
        else:
            hy1Info = self.hyInfos[hy1] = []
            hy1InfoKey = self.hyInfosKey[hy1] = {}
        for d in data:
            obj = { 'hy': hy, 'hydj': hydj }
            for c in cols:
                obj[c[0]] = d[c[1]] if c[1] <= 1  else float(d[c[1]])
            #print(obj)
            self.hyInfos[hy].append(obj)
            if obj['code'] not in hy1InfoKey:
                obj1 = obj.copy()
                obj1['hy'] = hy1
                obj1['hydj'] = '一级'
                hy1InfoKey[obj['code'] ] = obj1
                hy1Info.append(obj1)
                #print(obj1)

    # 行业对比
    def loadFile(self, fileName):
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
            self.loadDatas(txt, colInfos, *hyNames[0])
        p2 = soup.select('#fieldsChart2Data') # 二级行业数据
        if len(p2) == 1:
            p2x = p2[0]
            txt = p2x['value']
            self.loadDatas(txt, colInfos, *hyNames[len(hyNames) - 1])
        
        if len(p1) != 1 and len(p2) != 1:
            print('Load Error: 行业对比 ', fileName, '未找到二级、三级行业数据')
            raise Exception()

    #计算综合排名
    def calcHyPM(self, datas):
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

    def calcAllPM(self):
        keys = sorted(self.hyInfos.keys())
        for k in keys:
            datas = self.hyInfos[k]
            #计算数量
            for d in datas:
                d['hysl'] = len(datas)
            self.calcHyPM(datas)

    def saveDB(self):
        keys = sorted(self.hyInfos.keys())
        for hy in keys:
            datas = self.hyInfos[hy]
            with orm.db.atomic():
                existsNum = orm.THS_HYDB_2.select().where(orm.THS_HYDB_2.hy == hy).count()
                if existsNum == 0:
                    orm.THS_HYDB_2.insert_many(datas).execute()

    def loadAllFiles(self):
        files =  self.listHydbFiles()
        for f in files:
            self.loadFile(f)
        self.calcAllPM()
        self.saveDB()

    def loadOneFile(self, code):
        f = BASE_PATH + code + '-同行比较.html'
        self.loadFile(f)
        self.calcAllPM()
        self.saveDB()
        
#---------------------------------------------------------------------
def listFiles(tag = None):
    fs = os.listdir(BASE_PATH)
    fs = sorted(fs)
    if not tag:
        return fs
    ff = lambda n : tag in n
    return filter(ff, fs)
    
def loadOneFile(fileName, forceLoad = False):
    code = fileName[0 : 6]
    tag = fileName[6 : ]
    ops = {'股东研究': (orm.THS_GD, LoadGD), '主力持仓':(orm.THS_JGCC, LoadJGCC),  '最新动态':(orm.THS_Newest, LoadNewest)}
    
    ormClass, loadClass = ops[tag]
    load = forceLoad
    if (not forceLoad):
        obj = ormClass.get_or_none(ormClass.code == code)
        load = not obj
    if load:
        loadClass().load(code)


def loadAllFile(tag = None):
    fs = listFiles(tag)
    for idx, fn in enumerate(fs):
        loadOneFile(fn)
        try:
            #print('[%04d]' % (idx + 1))
            # loadOneFile(fn)
            pass
        except:
            print('Load Exception: ', fn)
            raise Exception()

#------------------------------自动下载数据---------------------------------------
# 最新动态 股东研究  主力持仓
class Download_3:
    def __init__(self) -> None:
        self.posList = [(700, 150), (923, 148), (923, 176)]
        self.posIdx = 0
        self.WAIT_TIME = 1.5

    def nextPos(self):
        pos = self.posList[ self.posIdx % 3]
        self.posIdx += 1
        return pos

    #下一个
    def clickNext(self):
        pa.moveTo(1183, 113)
        pa.click()
        time.sleep(self.WAIT_TIME)

    def download(self, num = 4900):
        for i in range(num):
            for k in range(len(self.posList) - 1):
                pos = self.nextPos()
                pa.moveTo(pos[0], pos[1])
                pa.click()
                time.sleep(self.WAIT_TIME)

#下载所有的行业对比
class Download_HYDB:
    def download(self):
        codes = ['000166', '000004', '000034', '000002', '000031', '600082', '000417', '000056', '601888', '000829', '001209', '002634', '002293', '000030', '000572', '000868', '000550', '000055', '000401', '002372', '002066', '000012', '002094', '300896', '000523', '000560', '000060', '000630', '000612', '002115', '000617', '601318', '002807', '001227', '000001', '601288', '002022', '002382', '002223', '000028', '001211', '000910', '001222', '000017', '001323', '000726', '000955', '002003', '600448', '000639', '000716', '001318', '002495', '000529', '002689', '000856', '002209', '000852', '002890', '000157', '002722', '000010', '000779', '000032', '000498', '000628', '000881', '002211', '002562', '002615', '002326', '000902', '002054', '002037', '000408', '000565', '000553', '000422', '000731', '002717', '000035', '000544', '002549', '000890', '000096', '000698', '002093', '002280', '000504', '002821', '002035', '002403', '002584', '001223', '000988', '001266', '002527', '000762', '000831', '000657', '000506', '603612', '000547', '600072', '000519', '000638', '002829', '000025', '000681', '002174', '000607', '000802', '000719', '000156', '000721', '000428', '000524', '000430', '600706', '000151', '000906', '000875', '000040', '001210', '000601', '000027', '000423', '000153', '000756', '000659', '000695', '000488', '000729', '000568', '000848', '000869', '000801', '000016', '000404', '000333', '000521', '000066', '300183', '002017', '000070', '000063', '000757', '000913', '000008', '002045', '000021', '000062', '001373', '000541', '000020', '002371', '002077', '300456', '002049', '000636', '000823', '002119', '002079', '002227', '000009', '002202', '000821', '000720', '000533', '000400', '000922', '002058', '000039', '001696', '000530', '002046', '000410', '000795', '000633', '000629', '000708', '000709', '000859', '001255', '001207', '002224', '002768', '002108', '000949', '000782', '000420', '000301', '000723', '000552']    
        for c in codes:
            pa.typewrite(c, interval = 0.25)
            pa.press("enter")
            time.sleep(2.5)


if __name__ == '__main__':
    fd = fiddler.Fiddler()
    fd.open()
    # 自动下载数据
    time.sleep(10)
    # Download_HYDB().download()
    # Download_3().download()

    # 解析下载的数据文件，并保存
    loadAllFile('股东研究')
    loadAllFile('主力持仓')
    loadAllFile('最新动态')
    LoadHYDB().loadAllFiles()
    fd.close()
    



