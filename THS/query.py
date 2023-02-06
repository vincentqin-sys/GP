from orm import *
from peewee import Expression

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
    print(rs)
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