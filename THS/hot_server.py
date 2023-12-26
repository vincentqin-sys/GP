from flask import Flask, url_for, views, abort, make_response, request
# pip install  psutil
import psutil, time, os, threading, datetime
import flask, peewee as pw
import json, os, sys
from flask_cors import CORS 
import traceback
import logging
from multiprocessing import Process

#sys.path.append(os.getcwd())
cwd = os.getcwd()
w = cwd.index('GP')
cwd = cwd[0 : w + 2]
sys.path.append(cwd)
from THS import hot_utils, orm


# 热点股票信息
def saveHot():
    hotDay = request.json.get('hotDay')
    hotTime = request.json.get('hotTime')
    hotInfos = request.json.get('hotInfo')
    for hi in hotInfos:
        hi['day'] = int(hotDay.replace('-', ''))
        hi['time'] = int(hotTime.replace(':', ''))
        hi['code'] = int(hi['code'])
        del hi['name']

    with orm.db2.atomic():
        for i in range(0, len(hotInfos), 20):
            orm.THS_Hot.insert_many(hotInfos[i : i + 20]).execute()
    lt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    print(f'[{lt}] saveHot success, insert {hotDay} {hotTime} num:{len(hotInfos)}')
    return {"status": "OK"}

# 热点股票信息
def getHot(code): 
    datas = orm.THS_Hot.select(orm.THS_Hot.day, orm.THS_Hot.time, orm.THS_Hot.hotValue, orm.THS_Hot.hotOrder).where(orm.THS_Hot.code == code)
    nd = [d.__data__ for d in datas]
    return nd

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
        checkRunCalcHotZH()

def checkRunCalcHotZH():
    now = datetime.datetime.now()
    ts = now.strftime('%H:%M')
    if ts <= '15:05' or ts >= '16:00':
        return
    hot_utils.calcAllHotZHAndSave()

def startup(app : Flask):
    print('[hot-server]功能: 启动服务, 保存同花顺热点; 保持Chrome始终都启动了。')
    #p = Process(target = sub_process, daemon = True)
    #p.start()
    #print('open check chrome deamon, pid=', p.pid)
    p = threading.Thread(target=sub_process, daemon=True)
    p.start()

    app.add_url_rule('/saveHot', view_func=saveHot, methods=['POST'])
    app.add_url_rule('/getHot/<code>', view_func=getHot,  methods = ['GET'])