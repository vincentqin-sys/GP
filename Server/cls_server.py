from flask import Flask, url_for, views, abort, make_response, request
import flask, peewee
from flask_cors import CORS 
import json, os, sys, datetime, threading, time
import traceback
import requests, json, logging

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from db import tck_orm
from Download import console

def now():
    return datetime.datetime.now().strftime('%H:%M')

def saveCls_ZT_One(it):
    insertNum, updateNum = 0, 0
    obj = tck_orm.CLS_ZT.get_or_none(code = it['code'], day = it['day'])
    if obj:
        if obj.ztReason != it['ztReason'] or obj.detail != it['detail']:
            obj.ztReason = it['ztReason']
            obj.detail = it['detail']
            updateNum += 1
            obj.save()
    else:
        insertNum += 1
        tck_orm.CLS_ZT.create(**it)
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
        console.write_1(console.CYAN, '[cls-server] ')
        print(f' {now()} save cls zt {day} insert({insertNum}) update({updateNum})')

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
        idx = item['up_reason'].find('|')
        if idx > 0 and idx < 40:
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

def tryDownloadDegree():
    try:
        now = datetime.datetime.now()
        today = now.strftime('%Y-%m-%d')
        obj = tck_orm.CLS_SCQX.get_or_none(day = today)
        if obj:
            return
        url = 'https://x-quote.cls.cn/quote/stock/emotion_options?app=CailianpressWeb&fields=up_performance&os=web&sv=7.7.5&sign=5f473c4d9440e4722f5dc29950aa3597'
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        day = js['data']['date']
        degree = js['data']['market_degree']
        degree = int(float(degree) * 100)
        obj = tck_orm.CLS_SCQX.get_or_none(day = day)
        if not obj:
            tck_orm.CLS_SCQX.create(day = day, zhqd = degree)
            console.write_1(console.CYAN, '[cls-server] ')
            print(' load degree: ', day, ' -> ', degree)
        return True
    except Exception as e:
        traceback.print_exc()
        return False

def run():
    runInfo = {}
    while True:
        now = datetime.datetime.now()
        if not acceptDay(now):
            time.sleep(5 * 60)
            continue
        curTime = now.strftime('%H:%M')
        day = now.strftime('%Y-%m-%d')
        if curTime > '15:00' and (day not in runInfo):
            ok = tryDownloadDegree()
            if ok:
                runInfo[day] = True
        if curTime < '09:30' or curTime > '16:00':
            time.sleep(5 * 60)
            continue
        downloadClsZT()
        time.sleep(10 * 60)

def autoLoadClsZT():
    th = threading.Thread(target = run)
    th.start()

def saveCLS_Degree():
    js = request.json
    day = js['day']
    zhqd = js['degree']
    obj = tck_orm.CLS_SCQX.get_or_none(day = day)
    if obj:
        if obj.zhqd != zhqd:
            obj.zhqd = zhqd
            obj.save()
            print(f'[cls-server] {now()} update degree ok, {day} = {zhqd}')
    else:
        tck_orm.CLS_SCQX.create(day = day, zhqd = zhqd)
        console.write_1(console.CYAN, '[cls-server] ')
        print(f'{now()} save degree ok, {day} = {zhqd}')
    return {'status': 'OK'}

def startup(app : Flask):
    print('[cls-server]功能: 启动财联社服务')
    app.add_url_rule('/save-CLS-ZT', view_func=saveCLS_ZT, methods = ['POST'])
    app.add_url_rule('/save-CLS-Degree', view_func=saveCLS_Degree, methods = ['POST'])
    autoLoadClsZT()

if __name__ == '__main__':
    downloadClsZT()
    #tryDownloadDegree()