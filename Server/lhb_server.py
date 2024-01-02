from flask import Flask, url_for, views, abort, make_response, request
import flask, peewee
from flask_cors import CORS 
import json, os, sys
import traceback
import requests, json, logging

cwd = os.getcwd()
w = cwd.index('GP')
cwd = cwd[0 : w + 2]
sys.path.append(cwd)
from LHB import orm

def toJE(s):
    if '万' in s:
        s = s.replace('万', '')
        return float(s)
    if '亿' in s:
        s = s.replace('亿', '')
        return float(s) * 10000
    return float(s)

def getLHBInfo():
    params = request.data
    params = json.loads(params)
    cs = orm.db_lhb.cursor()
    cs.execute(params['sql'])
    data = cs.fetchall()
    txt = json.dumps(data, ensure_ascii = False) # ensure_ascii = False
    cs.close()
    return txt

def showLhbDB():
    cs = orm.db_lhb.cursor()
    cs.execute('select max(日期) from TdxLHB')
    data = cs.fetchone()
    day = data[0]
    cs.close()
    return flask.render_template('show-lhb.html', maxDay = day )

def queryBySql():
    try:
        cs = orm.db_lhb.cursor()
        cs2 = orm.db_ths.cursor()
        params = json.loads(request.data)
        cs.execute(params['sql'])
        cols = [c[0] for c in cs.description]
        data = cs.fetchall()
        for i, d in enumerate(data):
            data[i] = [x for x in d]
        rs = {'status': 'success', 'cols': cols, 'data' : data}
        if 'code' in cols:
            codeIdx = cols.index('code')
            codes = [d[codeIdx] for d in data]
            codesStr = '", "'.join(codes)
            sql = 'select code, max(行业) from 行业对比_2 where code in ("' + codesStr + '") group by code'
            cs2.execute(sql)
            hyList = cs2.fetchall()
            cols.append('行业')
            for i, d in enumerate(data):
                code = d[codeIdx]
                for m in hyList:
                    if m[0] == code:
                        d.append(m[1])
                        break
        #txt = json.dumps(rs, ensure_ascii = False) # ensure_ascii = False
    except Exception as e:
        print(e)
        rs = {'status': 'fail', 'msg' : str(e)}
    finally:
        if cs:
            cs.close()
        if cs2:
            cs2.close()
    return rs

def startup(app : Flask):
    print('[lhb-server]功能:启动通达信龙虎榜服务')
    app.add_url_rule('/LHB/getLHBInfo', view_func=getLHBInfo, methods = ['POST'])
    app.add_url_rule('/LHB/show-lhb.html', view_func=showLhbDB, methods = ['GET'])
    app.add_url_rule('/LHB/queryBySql', view_func=queryBySql, methods = ['POST'])
