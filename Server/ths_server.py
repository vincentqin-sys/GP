import peewee as pw
import threading
import requests, json, flask, traceback
import datetime, time, sys, os, re
from flask import Flask, url_for, views, abort, make_response, request
import flask, peewee
from flask_cors import CORS 
import functools


sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tck import orm as tck_orm
from Download import henxin, console

def formatZtTime(ds):
    if not ds:
        return None
    ds = float(ds)
    sc = time.localtime(ds)
    f = f'{sc.tm_hour :02d}:{sc.tm_min :02d}:{sc.tm_sec :02d}'
    return f

# day = YYYYMMDD
# pageIdx = 1, 2 ....
def downloadOnePage(day, pageIdx):
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

# day = int, str, date, datetime
def downloadOneDay(day):
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
        rs = downloadOnePage(day, curPage)
        datas.update(rs['data'])
        pageCount = rs['pageCount']
        curPage += 1
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
        if obj.ztTime != it['ztTime'] or obj.status != it['status'] or obj.ztReason != it['ztReason']:
            obj.ztTime = it['ztTime']
            if it['status']:
                obj.status = it['status']
            if it['ztReason']:
                obj.ztReason = it['ztReason']
            obj.save()
            updateNum += 1
    if insertNum or updateNum:
        console.write_1(console.YELLOW, f'[ths_zt_downloader] ')
        print(f'{day} insert {insertNum}, update {updateNum}')

def downloadOneDayTry(day):
    try:
        downloadOneDay(day)
    except Exception as e:
        pass

def acceptDay(day):
    if type(day) == str:
        day = day.replace('-', '')
        day = int(day)
    if type(day) == int:
        day = datetime.date(day // 10000, day // 100 % 100, day % 100)
    if day.weekday() >= 5:
        return False
    return True

def autoLoadHistory():
    fromDay = datetime.date(2023, 3, 1)
    one = datetime.timedelta(days = 1)
    today = datetime.date.today()
    while fromDay <= today:
        if acceptDay(fromDay):
             downloadOneDayTry(fromDay.year * 10000 + fromDay.month * 100 + fromDay.day)
        fromDay += one
        time.sleep(2)

def run():
    while True:
        now = datetime.datetime.now()
        if not acceptDay(now):
            time.sleep(5 * 60)
            continue
        curTime = now.strftime('%H:%M')
        if curTime < '09:30' or curTime > '16:00':
            time.sleep(5 * 60)
            continue
        try:
            downloadOneDay(now)
        except Exception as e:
            traceback.print_exc()
        time.sleep(15 * 60)


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

# 查询个股涨跌信息
# day = YYYYMMDD
def queryAllCodeZD(day):
    hx = henxin.Henxin()
    hx.init()
    print(hx.update())
    url = 'https://www.iwencai.com/customized/chart/get-robot-data'
    headers = {'Content-Type': 'application/json', 'hexin-v': hx.update(), 'Origin': 'https://www.iwencai.com',
               'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
               'Referer': 'https://www.iwencai.com/unifiedwap/result?w=%E4%B8%AA%E8%82%A1%E6%B6%A8%E8%B7%8C%E6%8E%92%E5%90%8D,%20%E4%BB%B7%E6%A0%BC,%E6%88%90%E4%BA%A4%E9%A2%9D%E6%8E%92%E5%90%8D&querytype=stock'}
    params = {"source":"Ths_iwencai_Xuangu","version":"2.0","query_area":"","block_list":"","add_info":"{\"urp\":{\"scene\":1,\"company\":1,\"business\":1},\"contentType\":\"json\",\"searchInfo\":true}","question":"个股涨跌排名, 价格,成交额排名","perpage":"100","page":1,"secondary_intent":"stock","log_info":"{\"input_type\":\"click\"}","rsh":"Ths_iwencai_Xuangu_y07l4ove5pgc6l43kepxlr4j0f7uua81"}
    resp = requests.post(url, json = params , headers = headers) #
    txt = resp.content.decode('utf-8')
    print(txt)

if __name__ == '__main__':
    #autoLoadHistory()
    #downloadOneDay(20240409)
    queryAllCodeZD(0)