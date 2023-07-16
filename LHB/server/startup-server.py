from flask import Flask, url_for, views, abort, make_response, request
import flask, peewee
from flask_cors import CORS 
import json, os, sys
import traceback
import requests, json, logging

import orm, mcore, proxy, tdx_lhb

app = Flask(__name__, static_folder='ui/static', template_folder='ui/templates')

logging.basicConfig(level = logging.ERROR)
log = logging.getLogger('werkzeug')
log.disabled = True

cors = CORS(app)

# https://www.cnblogs.com/cxygg/p/12419502.html 设置cors
# pip install -U flask-cors 
# https://blog.csdn.net/qq_42778001/article/details/101436742


#@app.after_request
def after(resp):
    resp = make_response(resp)
    resp.headers[''] = ''

@app.route('/')
def root():
    return flask.render_template('index.html')
    
def toJE(s):
    if '万' in s:
        s = s.replace('万', '')
        return float(s)
    if '亿' in s:
        s = s.replace('亿', '')
        return float(s) * 10000
    return float(s)
    
"""
@app.route('/writeThsLHBDataList', methods = ['POST'])
def writeThsLHBDataList():
    try:
        params = request.data
        params = json.loads(params)
        print(params['day'], len(params['data']))
        
        cs = mcore.db.cursor()
        cs.execute('select count(*) from LHB where day = ? ', [ params['day'] ])
        rows = cs.fetchall()
        count = rows[0][0]
        cs.close()
        print('count = ', count)
        if count > 0:
            return '{"status": "Exists", "msg" : "Alreay Exists"}'
        
        for it in params['data']:
            it['day'] = params['day']
            it['title'] = it['detail']['title']
            it['detail'] = json.dumps(it['detail'], ensure_ascii=False)
            it['price'] = float(it['price'])
            it['zd'] = float(it['zd'].replace('%', ''))
            it['cjje'] = toJE(it['cjje'])
            it['jme'] = toJE(it['jme'])
            it['mrje'] = (it['cjje'] + it['jme']) / 2
            it['mcje'] = (it['cjje'] - it['jme']) / 2
            orm.ThsLHB.create(**it)
        return '{"status": "OK", "msg" : "success"}'
    except Exception as e:
        traceback.print_exc()
        m = {"status": "Fail", "msg": str(e)}
        return json.dumps(m)
"""
     
@app.route('/getLHBInfo', methods = ['POST'])
def getLHBInfo():
    params = request.data
    params = json.loads(params)
    cs = orm.db.cursor()
    cs.execute(params['sql'])
    data = cs.fetchall()
    txt = json.dumps(data, ensure_ascii = False) # ensure_ascii = False
    cs.close()
    return txt
    
@app.route('/getZTZBInfo', methods = ['POST'])
def getZTZBInfo():
    zdb = peewee.SqliteDatabase('../ZT/ZT.db')
    cs = zdb.cursor()
    params = request.data
    params = json.loads(params)
    cs.execute(params['sql'])
    data = cs.fetchall()
    txt = json.dumps(data, ensure_ascii = False) # ensure_ascii = False
    cs.close()
    zdb.close()
    return txt
    

doingTag = False

@app.route('/fetchTdxLHB', methods = ['GET'])
def fetchTdxLHB():
    global doingTag
    if doingTag:
        return
    doingTag = True
    tdx_lhb.loadTdxLHB()
    doingTag = False
    
@app.route('/show-lhb.html', methods = ['GET'])
def showLhbDB():
    return flask.render_template('show-lhb.html')

@app.route('/queryBySql', methods = ['POST'])
def queryBySql():
    try:
        cs = orm.db.cursor()
        params = json.loads(request.data)
        cs.execute(params['sql'])
        cols = [c[0] for c in cs.description]
        data = cs.fetchall()
        rs = {'status': 'success', 'cols': cols, 'data' : data}
        #txt = json.dumps(rs, ensure_ascii = False) # ensure_ascii = False
    except Exception as e:
        print(e)
        rs = {'status': 'fail', 'msg' : str(e)}
    finally:
        if cs:
            cs.close()
    return rs

"""
@app.before_request
def _open_db(*args):
    if mcore.db.is_closed():
        mcore.db.connect(reuse_if_open=True)
    
@app.teardown_request
def _close_db(*args):
    if not mcore.db.is_closed():
        mcore.db.close()
"""

def startup():
    print('功能：启动8050服务，将同花顺龙虎榜关联到通达信龙虎榜；自动下载通达信龙虎榜')
    print('-----Start Server LHB at port 8050 ------')
    orm.init()
    proxy.init(app)
    tdx_lhb.loadTdxLHB()
    tdx_lhb.autoLoadTdxLHB()
    app.run(host = '0.0.0.0', port=8050, debug=True) # , debug=True
    
    
if __name__ == '__main__':
    #if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    startup()