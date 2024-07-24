import peewee as pw
import threading
import requests, json, flask, traceback
import datetime, time, sys, os, re
from flask import Flask, url_for, views, abort, make_response, request
import flask, peewee
from flask_cors import CORS 
import functools


sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from db import tck_orm
from Download import henxin, console, ths_iwencai
from Common import holiday
from THS import hot_utils

def formatZtTime(ds):
    if not ds:
        return None
    ds = float(ds)
    sc = time.localtime(ds)
    f = f'{sc.tm_hour :02d}:{sc.tm_min :02d}:{sc.tm_sec :02d}'
    return f

# 下载同花顺涨停信息(分页下载)
# day = YYYYMMDD
# pageIdx = 1, 2 ....
def downloadOnePageZT(day, pageIdx):
    today = datetime.date.today()
    today = today.strftime('%Y%m%d')
    PAGE_SIZE = 50
    ct = int(time.time() * 1000)
    pday = "" if day == today else day
    url = f'https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?page={pageIdx}&limit={PAGE_SIZE}&field=199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003,9004&filter=HS,GEM2STAR&date={pday}&order_field=330324&order_type=0&_={ct}'
    hx = henxin.Henxin()
    hx.init()
    param = hx.update()
    session = requests.Session()
    session.headers = {
        'Accept': 'text/plain, */*; q=0.01',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html',
        'Cookie': 'v=' + param
    }
    resp = session.get(url)
    if resp.status_code != 200:
        print('[ths_zt_downloader.downloadOne] Error:', resp)
        raise Exception()
    txt = resp.content.decode('utf-8')
    js = json.loads(txt)
    if js['status_code'] != 0:
        print('[ths_zt_downloader.downloadOne] Json Fail 1: ', js, day)
        raise Exception()
    data = js['data']
    total = data['page']['total']
    curPage = data['page']['page']
    pageCount = data['page']['count']
    date = data['date']
    infos = data['info']
    date = date[0 : 4] + '-' + date[4 : 6] + '-' + date[6 : 8]
    ds = {}
    for it in infos:
        status = it['high_days'] or ''
        matchObj = re.match('^(\d+)天(\d+)板$', status)
        if matchObj:
            t = matchObj.group(1)
            b = matchObj.group(2)
            if t == b:
                status = t + '板'
        ds[it['code']] = {'code': it['code'], 'name': it['name'], 'ztReason': it['reason_type'],
                          'status': status, 'day': date, 'ztTime': formatZtTime(it['first_limit_up_time'])}
    rs = {'total': total, 'day': date, 'curPage':curPage, 'pageCount':pageCount, 'data': ds}
    return rs

# 下载同花顺涨停信息
# day = int, str, date, datetime
def downloadOneDayZT(day):
    datas = {}
    if type(day) == int:
        day = str(day)
    elif type(day) == str:
        day = day.replace('-', '')
    elif isinstance(day, datetime.date):
        day = day.year * 10000 + day.month * 100 + day.day
    curPage = 1
    pageCount = 1
    while curPage <= pageCount:
        rs = downloadOnePageZT(day, curPage)
        datas.update(rs['data'])
        pageCount = rs['pageCount']
        curPage += 1
    return datas

# 保存同花顺涨停信息
def saveZT(day, datas):
    insertNum, updateNum = 0, 0
    # save to db
    for k in datas:
        it = datas[k]
        if not it['ztReason'] or it['ztReason'] == '其它':
            continue
        obj = tck_orm.THS_ZT.get_or_none(day = it['day'], code=it['code'])
        if not obj:
            it['name'] = it['name'].replace(' ', '')
            tck_orm.THS_ZT.create(**it)
            insertNum += 1
            continue
        if obj.status != it['status'] or obj.ztReason != it['ztReason']:
            #print('old:', obj.status, obj.ztReason)
            #print('new:', it['status'], it['ztReason'])
            if it['status']:
                obj.status = it['status']
            if it['ztReason']:
                obj.ztReason = it['ztReason']
            obj.save()
            updateNum += 1
    if insertNum or updateNum:
        console.writeln_1(console.YELLOW, f'[ths-zt] ', f'{day} insert {insertNum}, update {updateNum}')

def downloadSaveOneDayTry(day):
    try:
        datas = downloadOneDayZT(day)
        saveZT(day, datas)
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

def autoLoadHistory(fromDay = 20230301):
    fromDay = datetime.date(fromDay // 10000, fromDay // 100 % 100, fromDay % 100)
    one = datetime.timedelta(days = 1)
    today = datetime.date.today()
    while fromDay <= today:
        if acceptDay(fromDay):
             downloadSaveOneDayTry(fromDay.year * 10000 + fromDay.month * 100 + fromDay.day)
        fromDay += one
        time.sleep(2)

def downloadSaveHot():
    try:
        rs = ths_iwencai.download_hot()
        num = ths_iwencai.save_hot(rs)
        console.write_1(console.RED, f'[hot-server] ')
        if num > 0:
            day = rs[0].day
            _time = f'{rs[0].time // 100}:{rs[0].time % 100 :02d}'
            console.writeln_1(console.RED, f'success, insert {day} {_time} num:{num}')
        else:
            console.writeln_1(console.RED, f'fail ')
        return num > 0
    except Exception as e:
        traceback.print_exc()
    return False

def downloadSaveZs():
    try:
        rs = ths_iwencai.download_zs_zd()
        num = ths_iwencai.save_zs_zd(rs)
        console.write_1(console.GREEN, f'[THS-ZS] ')
        if rs:
            console.writeln_1(console.GREEN, f"Save ZS success, insert {rs[0].day} num: {num} ")
        else:
            console.writeln_1(console.GREEN, f"Save ZS, no data ")
        return len(rs) > 0
    except Exception as e:
        traceback.print_exc()
    return False

def downloadSaveDde():
    try:
        rs = ths_iwencai.download_dde_money()
        ok = ths_iwencai.save_dde_money(rs)
        console.write_1(console.PURPLE, f'[THS-DDE] ')
        if ok:
            console.writeln_1(console.PURPLE, 'success, save num: ', len(rs))
        else:
            console.writeln_1(console.PURPLE, 'fail')
        return ok
    except Exception as e:
        traceback.print_exc()
    return False

def download_hygn():
    try:
        upd, ins = ths_iwencai.download_hygn()
        u, i = ths_iwencai.save_hygn(upd, ins)
        console.writeln_1(console.CYAN, f'[THS-HyGn]  update {u}, insert {i}')
        return True
    except Exception as e:
        traceback.print_exc()
    return False

def run():
    download_hygn_infos = {}
    last_zt_time = 0
    last_hotzh_time = 0
    last_hot_time = 0
    last_zs_time = 0
    last_dde_time = 0

    while True:
        time.sleep(10)
        now = datetime.datetime.now()
        day = now.strftime('%Y%m%d')
        if not acceptDay(now):
            continue
        curTime = now.strftime('%H:%M')

        # 下载热度信息
        if (curTime >= '09:30' and curTime <= '11:30') or (curTime >= '13:00' and curTime <= '15:00'):
            if (now.minute % 10 <= 2) and (time.time() - last_hot_time >= 5 * 60):
                downloadSaveHot()
                last_hot_time = time.time()

        # 下载同花顺涨停信息
        if curTime >= '09:30' and curTime < '17:30':
            if time.time() - last_zt_time >= 5 * 60: # 5分钟
                downloadSaveOneDayTry(day)
                last_zt_time = time.time()

        # 计算热度综合排名
        if curTime >= '15:05' and curTime < '16:00':
            if time.time() - last_hotzh_time >= 60 * 60:
                hot_utils.calcAllHotZHAndSave()
                last_hotzh_time = time.time()
        
        # 下载同花顺指数涨跌信息
        if curTime >= '15:10' and curTime < '16:00':
            if time.time() - last_zs_time >= 60 * 60:
                downloadSaveZs()
                last_zs_time = time.time()

        # 下载dde数据, 前100 + 后100
        if curTime >= '15:15' and curTime < '16:00':
            if time.time() - last_dde_time >= 60 * 60:
                downloadSaveDde()
                last_dde_time = time.time()

        # 下载个股板块概念信息
        if (curTime >= '15:20') and (day not in download_hygn_infos):
            download_hygn()
            download_hygn_infos[day] = True
            pass

def autoLoadThsZT():
    th = threading.Thread(target = run)
    th.start()

def load_ths_code(type_):
    code = request.args.get('code')
    if len(code) != 6:
        return {'status': 'Fail', 'msg': 'error code : ' + code, 'data': ''}
    hx = henxin.HexinUrl()
    if type_ == 'timeline':
        url = hx.getFenShiUrl(code)
    elif type_ == 'history':
        url = hx.getKLineUrl(code)
    elif type_ == 'today':
        url = hx.getTodayKLineUrl(code)
    data = hx.loadUrlData(url)
    return {'status': 'OK', 'msg': '', 'data': data}

def startup(app):
    load_ths_timeline = functools.partial(load_ths_code, 'timeline')
    load_ths_timeline.__name__ = 'load_ths_timeline'
    load_ths_today = functools.partial(load_ths_code, 'today')
    load_ths_today.__name__ = 'load_ths_today'
    load_ths_history = functools.partial(load_ths_code, 'history')
    load_ths_history.__name__ = 'load_ths_history'
    app.add_url_rule('/ths/load-timeline', view_func = load_ths_timeline, methods = ['GET'])
    app.add_url_rule('/ths/load-today-kline', view_func = load_ths_today, methods = ['GET'])
    app.add_url_rule('/ths/load-history-kline', view_func = load_ths_history, methods = ['GET'])

if __name__ == '__main__':
    #autoLoadHistory(20240708)
    #downloadOneDay(20240702)
    pass