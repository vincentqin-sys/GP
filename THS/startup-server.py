from flask import Flask, url_for, views, abort, make_response, request
# pip install  psutil
import psutil, time, os, threading
import flask, peewee
import json, os
from flask_cors import CORS 
import traceback
import logging
from multiprocessing import Process

import orm
import query


app = Flask(__name__, static_folder='ui/el', template_folder='ui')
cors = CORS(app)

logging.basicConfig(level = logging.ERROR)
log = logging.getLogger('werkzeug')
log.disabled = True

@app.route('/', methods = ['GET'])
def home():
    return flask.render_template('query.html')

@app.route('/my-select.js', methods = ['GET'])
def myselect():
    return flask.render_template('my-select.js')
    
@app.route('/queryByCode/<codes>', methods = ['GET'])
def queryByCodes(codes): # codes = 'code, code....' 股票代码
    cs = codes.split(',')
    data = query.queryManyFlatFullInfo(cs)
    #print('queryByCodes=', data, cs)
    return json.dumps(data, ensure_ascii=False)
    
@app.route('/queryByGN/<cndType>/<gns>', methods = ['GET'])
def queryByGN(gns, cndType): # gns = 'gn, gn....' 概念  cndType='AND' | 'OR'
    cs = gns.split(',')
    data = query.queryByGN(cs, cndType)
    codes = (d.code for d in data)
    rs = query.queryManyFlatFullInfo(codes)
    #print('queryByGN=', rs, data)
    return json.dumps(rs, ensure_ascii=False)

@app.route('/queryByHY/<hyName>', methods = ['GET'])
def queryByHY(hyName): # gns = 'gn, gn....' 概念  cndType='AND' | 'OR'
    data = query.queryByHY(hyName)
    codes = (d.code for d in data)
    rs = query.queryManyFlatFullInfo(codes)
    #print('queryByGN=', rs, data)
    return json.dumps(rs, ensure_ascii=False)

@app.route('/saveHot', methods = ['POST'])
def saveHot(): # 热点股票信息
    hotDay = request.json.get('hotDay')
    hotTime = request.json.get('hotTime')
    hotInfos = request.json.get('hotInfo')
    for hi in hotInfos:
        hi['day'] = int(hotDay.replace('-', ''))
        hi['time'] = int(hotTime.replace(':', ''))
        hi['code'] = int(hi['code'])
        del hi['name']

    with orm.db.atomic():
        for i in range(0, len(hotInfos), 20):
            orm.THS_Hot.insert_many(hotInfos[i : i + 20]).execute()
    lt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    print(f'[{lt}] saveHot success, insert {hotDay} {hotTime} num:{len(hotInfos)}')
    return {"status": "OK"}

@app.route('/getHot/<code>', methods = ['GET'])
def getHot(code): # 热点股票信息
    datas = orm.THS_Hot.select(orm.THS_Hot.day, orm.THS_Hot.time, orm.THS_Hot.hotValue, orm.THS_Hot.hotOrder).where(orm.THS_Hot.code == code)
    nd = [d.__data__ for d in datas]
    return nd

# 查询淘股吧remark信息
@app.route('/query_taoguba_remark', methods = ['GET'])
def query_taoguba_remark(): 
    datas = orm.TaoGuBa_Remark.select()
    nd = [d.__data__ for d in datas]
    return nd

# 保存淘股吧remark信息
@app.route('/save_taoguba_remark', methods = ['POST'])
def save_taoguba_remark(): 
    tid = request.json.get('id')
    if tid and tid > 0:
        data = orm.TaoGuBa_Remark.get_or_none(orm.TaoGuBa_Remark.id == tid)
        if data:
            data.info = request.json.get('info')
            data.save()
            return {'status' : 'success', 'msg' : 'Update success', 'id': tid}
    obj = orm.TaoGuBa_Remark.create(info = request.json.get('info'))
    return {'status' : 'success', 'msg' : 'Insert success', 'id': obj.id}
    

def check_chrome_open():
    for pid in psutil.pids():
        p = psutil.Process(pid)
        if p.name() == 'chrome.exe':
            return True
    return False

def sub_process():
    print('in sub_process')
    while True:
        if not check_chrome_open():
            os.startfile('https://cn.bing.com/')
        time.sleep(60 * 5) # 5 minutes

if __name__ == '__main__':
    print('功能：启动8071服务，保存同花顺热点；保持Chrome始终都启动了。')
    #p = Process(target = sub_process, daemon = True)
    #p.start()
    #print('open check chrome deamon, pid=', p.pid)
    p = threading.Thread(target=sub_process, daemon=True)
    p.start()
    print('----- Start Server THS at port 8071 -----')
    app.run(host = '0.0.0.0', port=8071) #, debug=True 