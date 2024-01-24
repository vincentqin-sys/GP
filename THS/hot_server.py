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

def getMoreHotOrders():
    lastDay = request.args.get('lastDay')
    num = request.args.get('num')
    if not lastDay or lastDay == '0':
        lastDay = datetime.date.today().strftime('%Y%m%d')
    lastDay = int(lastDay)
    num = 200 if not num else int(num)
    q = orm.THS_HotZH.select(orm.THS_HotZH.day).distinct().order_by(orm.THS_HotZH.day.desc()).tuples()
    existsDays = [d[0] for d in q]
    hotLastDay = orm.THS_Hot.select(pw.fn.max(orm.THS_Hot.day)).scalar()
    rs = []
    if (lastDay >= hotLastDay) and (hotLastDay not in existsDays):
        nn = hot_utils.calcHotZHOnDay(hotLastDay)[0 : num]
        news = []
        for d in nn:
            name = hot_utils.getNameByCode(d['code'])
            if not name:
                name = f"{d['code'] :06d}"
            news.append(name)
        rs.append({'day': hotLastDay, 'codes': news})
    DAYS_NUM = 5
    for fromIdx, d in enumerate(existsDays):
        if d <= lastDay:
            break
    for i in range(0, DAYS_NUM - len(rs)):
        if i + fromIdx >= len(existsDays):
            break
        day = existsDays[i + fromIdx]
        news = []
        qd = orm.THS_HotZH.select(orm.THS_HotZH.code).where(orm.THS_HotZH.day == day).order_by(orm.THS_HotZH.zhHotOrder.asc()).limit(num).tuples()
        for d in qd:
            name = hot_utils.getNameByCode(d[0])
            if not name:
                name = f"{d[0] :06d}"
            news.append(name)
        rs.append({'day': day, 'codes': news})
    return rs

def saveZS():
    data = request.json
    if len(data) > 0:
        datas = [orm.THS_ZS_ZD(**d) for d in data]
        orm.THS_ZS_ZD.bulk_create(datas, 100)
        print(f"Save ZS success, insert {data[0]['day']} {len(data)} num")
    else:
        print(f"Save ZS, no data ")
    return {"status": "OK"}

def startup(app : Flask):
    print('[hot-server]功能: 启动服务, 保存同花顺热点; 保持Chrome始终都启动了。')
    #p = Process(target = sub_process, daemon = True)
    #p.start()
    #print('open check chrome deamon, pid=', p.pid)
    p = threading.Thread(target=sub_process, daemon=True)
    p.start()

    app.add_url_rule('/saveHot', view_func=saveHot, methods=['POST'])
    app.add_url_rule('/getHot/<code>', view_func=getHot,  methods = ['GET'])
    app.add_url_rule('/moreHotOrders', view_func=getMoreHotOrders,  methods = ['GET'])
    app.add_url_rule('/saveZS', view_func=saveZS, methods=['POST'])