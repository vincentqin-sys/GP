from orm import *
from peewee import Expression
import pyperclip
import os, sys, platform
import win32api, win32gui, win32clipboard 
# pip install pyperclip

# 按题材概念查找
# gns: 多个或单个概念
# conditionType: 查询并集或交集 ('AND' 'OR')
# return list of THS_GNTC
def queryByGN(gns, conditionType = None):
    cnd = None
    if type(gns) == str:
        gns = (gns,)
    if not conditionType:
        conditionType = 'AND'
    conditionType = conditionType.upper()
    for i, g in enumerate(gns):
        c = THS_GNTC.gn.contains(g.strip())
        if i == 0:
            cnd = c
            continue
        if conditionType == 'AND':
            cnd = cnd & c
        elif conditionType == 'OR':
            cnd = cnd | c

    q = THS_GNTC.select().where(cnd)
    #print(q.sql())
    rs = [it for it in q]
    #for i, r in enumerate(rs):
    #    print(i, r.code, r.name)
    return rs

#按行业名称查找    
def queryByHY(hyName):
    q = THS_HYDB.select(THS_HYDB.code.distinct()).where(THS_HYDB.hyName.contains(hyName))
    print(q.sql())
    rs = [it for it in q]
    print(rs)
    return rs

#查询指字的股票代码的详细信息 
# return a dict of : {THS_Newest:最新动态、THS_GNTC:概念题材、THS_GD:股东、THS_JGCC:机构持仓、THS_HYDB_2:行业对比(二级)、THS_HYDB_3:行业对比(三级)}
def queryFullInfo(code):
    code = code.strip()
    rs = {'code' : code}
    rs['THS_Newest'] = THS_Newest.get_or_none(THS_Newest.code == code)
    rs['THS_GNTC'] = THS_GNTC.get_or_none(THS_GNTC.code == code)
    rs['THS_GD'] = THS_GD.get_or_none(THS_GD.code == code)
    rs['THS_JGCC'] = THS_JGCC.get_or_none(THS_JGCC.code == code)
    rs['THS_HYDB_2'] = THS_HYDB.get_or_none((THS_HYDB.code == code) & (THS_HYDB.hyDJ == '二级'))
    rs['THS_HYDB_3'] = THS_HYDB.get_or_none((THS_HYDB.code == code) & (THS_HYDB.hyDJ == '三级'))
    #print(rs)
    return rs

def _mergeInfo(target, ormObj, prefix = None):
    if not ormObj:
        return
    data = ormObj.__data__
    if not prefix:
        prefix = ormObj.__class__.__name__
    for k in data:
        if k == 'id':
            continue
        if (k == 'code') or (k == 'name'):
            target[k] = data[k]
        else:
            target[prefix + '-' + k] = data[k]

def flatFullInfo(info):
    rs = {}
    _mergeInfo(rs, info['THS_Newest'])
    _mergeInfo(rs, info['THS_GNTC'])
    _mergeInfo(rs, info['THS_GD'])
    _mergeInfo(rs, info['THS_JGCC'])
    _mergeInfo(rs, info['THS_HYDB_2'], 'THS_HYDB_2')
    _mergeInfo(rs, info['THS_HYDB_3'], 'THS_HYDB_3')
    #print(rs)
    return rs
    
#查询指字的股票代码的详细信息
def queryManyFullInfo(codes):
    rs = []
    for code in codes:
        rs.append(queryFullInfo(code))
    return rs
    
def queryManyFlatFullInfo(codes):
    rs = []
    for code in codes:
        info = queryFullInfo(code)
        if not info:
            continue
        flatInfo = flatFullInfo(info)
        rs.append(flatInfo)
    return rs    
    
# queryByGN(('数字经济', '信创'), 'AND')
#flatFullInfo(queryFullInfo('600536'))

def getPMTag(v):
    if (v < 0.2): return '优秀'
    if (v < 0.4): return '良好'
    if (v < 0.6): return '一般'
    if (v < 0.8): return '较差'
    return '垃圾'

def calcZhPMTag(info):
    if info.get('THS_HYDB_2-zhPM') and info.get('THS_HYDB_2-hyTotal'):
        info['THS_HYDB_2-zhPM-Tag'] = getPMTag(info.get('THS_HYDB_2-zhPM') / info.get('THS_HYDB_2-hyTotal'))
    if info.get('THS_HYDB_3-zhPM') and info.get('THS_HYDB_3-hyTotal'):
        info['THS_HYDB_3-zhPM-Tag'] = getPMTag(info.get('THS_HYDB_3-zhPM') / info.get('THS_HYDB_3-hyTotal'))
    
def getCodeInfo(code):
    code = int(code)
    code = "%06d" % code
    info = queryFullInfo(code)
    info = flatFullInfo(info)
    line = code + ' ' + str(info.get('name'))
    zb = ''
    if not info.get('THS_JGCC-totalRate1'):
        zb = '--'
    elif int(info.get('THS_JGCC-totalRate1')) < 1:
        zb = '<1'
    else:
        zb = int(info.get('THS_JGCC-totalRate1'))
    calcZhPMTag(info)
    jgNum = info.get('THS_JGCC-orgNum1')
    if jgNum is None:
        jgNum = '--'
    jg = "机构: %s家, 持仓%s%%" % (jgNum, zb)
    xy = ''
    hyName = ''
    if info.get('THS_HYDB_2-zhPM'):
        xy += '  二级 ' + str(info.get('THS_HYDB_2-zhPM')) + '/' + str(info.get('THS_HYDB_2-hyTotal')) + f'[{info.get("THS_HYDB_2-zhPM-Tag")}]' + '\n'
        hyName = str(info.get('THS_HYDB_2-hyName'))
    if info.get('THS_HYDB_3-zhPM'):
        xy += '  三级 ' + str(info.get('THS_HYDB_3-zhPM')) + '/' + str(info.get('THS_HYDB_3-hyTotal')) + f'[{info.get("THS_HYDB_3-zhPM-Tag")}]'
        hyName = str(info.get('THS_HYDB_3-hyName'))
    txt = line + '\n' + hyName + '\n' + jg + '\n' + xy
    return txt
    

def getCodeInfo_THS(code):
    code = int(code)
    code = "%06d" % code
    gdInfo = THS_GD.get_or_none(THS_GD.code == code)
    jgccInfo = THS_JGCC.get_or_none(THS_JGCC.code == code)
    hydbInfo = THS_HYDB_2.select().where(THS_HYDB_2.code == code).order_by(THS_HYDB_2.hy).execute()

    name = ''
    zb = ''
    if not jgccInfo:
        zb = '--'
        jgNum = '--'
    else:
        jgNum = jgccInfo.orgNum1
        name = jgccInfo.name
        if not jgccInfo.totalRate1:
            zb = '--'
        elif jgccInfo.totalRate1 < 1:
            zb = '<1'
        else:
            zb = int(jgccInfo.totalRate1)
    jg = "机构 %s家, 持仓%s%%" % (jgNum, zb)

    if gdInfo:
        jg += f'   前十流通股东{int(gdInfo.ltgdTop10Rate)}%'
        name = gdInfo.name

    hy = ''
    hyName = ''
    for m in hydbInfo:
        hy += f'  {m.hydj} {m.zhpm} / {m.hysl} [{getPMTag(m.zhpm / m.hysl)}]\n'
        hyName = m.hy
        name = m.name
    
    line = code + ' ' + name
    txt = line + '\n' + hyName + '\n' + jg + '\n' + hy
    return txt
    
#打印并复制信息到剪贴板
def printCodeInfo(code):
    info = getCodeInfo(code)
    pyperclip.copy(info)
    print(info, '\n')

def printCodeInfoLoop():
    while True:
        try:
            code = input('Input Code:')
            printCodeInfo(code)
        except:
            pass

def copyToClipboard(txt : str):
    if 'Windows-10' not in platform.platform():
        pyperclip.copy(txt)
        return
    txt = txt.replace('机构', "Org")
    txt = txt.replace("持仓", "Rate ")
    txt = txt.replace("二级", "Level-2")
    txt = txt.replace("三级", "Level-3")
    txt = txt.replace("行业排名", "Ranking")
    txt = txt.replace("家", "")
    txt = txt.replace("优秀", "Very Good")
    txt = txt.replace("良好", "Good")
    txt = txt.replace("一般", "Ordinary")
    txt = txt.replace("较差", "Bad")
    txt = txt.replace("垃圾", "Very Bad")
    pyperclip.copy(txt)
    #print(txt)

if __name__ == '__main__':
    #奇怪的问题 win10:
    # 在复制到剪贴板上前(或在程序运行前)，必须先打开输入法，并设置到中文输入，不然粘贴时就是乱码
    printCodeInfoLoop()
    