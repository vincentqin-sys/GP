from flask import Flask, url_for, views, abort, make_response, request
import flask, peewee
from flask_cors import CORS 
import json, os, sys, datetime, threading, time
import traceback
import requests, json, logging

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tck import orm

def now():
    return datetime.datetime.now().strftime('%H:%M')

def saveCls_ZT_One(it):
    insertNum, updateNum = 0, 0
    obj = orm.CLS_ZT.get_or_none(code = it['code'], day = it['day'])
    if obj:
        if obj.ztReason != it['ztReason'] or obj.detail != it['detail']:
            obj.ztReason = it['ztReason']
            obj.detail = it['detail']
            updateNum += 1
            obj.save()
    else:
        insertNum += 1
        orm.CLS_ZT.create(**it)
    return insertNum, updateNum

def saveCls_ZT_List(its):
    day = None
    insertNum, updateNum = 0, 0
    for it in its:
        day = it['day']
        ins, upd = saveCls_ZT_One(it)
        insertNum += ins
        updateNum += upd
    if insertNum > 0 or updateNum > 0:
        print(f'[cls-server] {now()} save cls zt {day} insert({insertNum}) update({updateNum})')

def saveCLS_ZT():
    saveCls_ZT_List(request.json)
    return {'status': 'OK'}

def __downloadClsZT():
    url = 'https://x-quote.cls.cn/quote/index/up_down_analysis?app=CailianpressWeb&os=web&rever=1&sv=7.7.5&type=up_pool&way=last_px&sign=a820dce18412fac3775aa940d0b00dcb'
    resp = requests.get(url)
    txt = resp.content.decode('utf-8')
    js = json.loads(txt)
    if js['code'] != 200:
        return
    data = js['data']
    rs = []
    for item in data:
        if item['is_st'] != 0:
            continue
        obj = {'code' : item['secu_code'], 'name': item['secu_name'], 'lbs': item['limit_up_days'] }
        if not obj['code']:
            continue
        if len(obj['code']) == 8:
            obj['code'] = obj['code'][2 : ]
		# obj.ztTime = item.time.substring(11, 16);
        obj['day'] = item['time'][0 : 10]
        obj['ztReason'] = ''
        if item['up_reason'].find(' | ') > 0:
            idx = item['up_reason'].index('|')
            obj['ztReason'] = item['up_reason'][0 : idx].strip()
            obj['detail'] = item['up_reason'][idx + 1 : ].strip()
        else:
            obj['detail'] = item['up_reason']
        if obj['ztReason'] != '--':
            rs.append(obj)
    return rs

def downloadClsZT():
    try:
        rs = __downloadClsZT()
        saveCls_ZT_List(rs)
    except Exception as e:
        print('[cls_server] Exception: ', e)
        traceback.print_exc()

def acceptDay(day):
    if type(day) == str:
        day = day.replace('-', '')
        day = int(day)
    if type(day) == int:
        day = datetime.date(day // 10000, day // 100 % 100, day % 100)
    if day.weekday() >= 5:
        return False
    return True

def run():
    while True:
        now = datetime.datetime.now()
        if not acceptDay(now):
            continue
        curTime = now.strftime('%H:%M')
        if curTime < '09:30' or curTime > '16:00':
            time.sleep(60 * 3600) # 1 hour
        else:
            time.sleep(10 * 60)
        downloadClsZT()

def autoLoadClsZT():
    th = threading.Thread(target = run)
    th.start()        

def saveCLS_Degree():
    js = request.json
    day = js['day']
    zhqd = js['degree']
    obj = orm.CLS_SCQX.get_or_none(day = day)
    if obj:
        if obj.zhqd != zhqd:
            obj.zhqd = zhqd
            obj.save()
            print(f'[cls-server] {now()} update degree ok, {day} = {zhqd}')
    else:
        orm.CLS_SCQX.create(day = day, zhqd = zhqd)
        print(f'[cls-server] {now()} save degree ok, {day} = {zhqd}')
    return {'status': 'OK'}

def startup(app : Flask):
    print('[cls-server]功能: 启动财联社服务')
    app.add_url_rule('/save-CLS-ZT', view_func=saveCLS_ZT, methods = ['POST'])
    app.add_url_rule('/save-CLS-Degree', view_func=saveCLS_Degree, methods = ['POST'])
    autoLoadClsZT()