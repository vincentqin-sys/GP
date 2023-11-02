import peewee as pw
import threading
import requests, json, flask
import datetime, time, sys, os
import mcore, orm

# yyyy-mm-dd
# return [ {code, name}, ... ]
def loadOneDayTotal(day):
    url = 'http://page2.tdx.com.cn:7615/TQLEX?Entry=CWServ.tdxsj_lhbd_lhbzl'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': 'http://page2.tdx.com.cn:7615/site/tdxsj/html/tdxsj_lhbd.html'}
    params = '{' + f"'Params': ['0', '{day}', '1']" + '}'
    orgRes = requests.post(url, data=params, headers = headers)
    txt = orgRes.text
    rs = json.loads(txt)
    if ('ErrorCode' not in rs) or (rs['ErrorCode'] != 0):
        print('Error[loadOneDayTotal]: load tdx long hu bang error. day=', day)
        return None
    infos = rs['ResultSets'][0]['Content']
    v = []
    for it in infos:
        v.append({'code': it[0], 'name': it[1]})
    return v

def getColInfo(colNames : list, cnt : list, name : str):
    idx = colNames.index(name)
    return cnt[idx]

def isExsitsCnt(idx, colNames, title, cnt, cols):
    titleIdx = colNames.index(title)
    cols = [ colNames.index(c) for c in cols ]
    org = cnt[idx]
    for i in range(0, idx):
        cur = cnt[i]
        if cur[titleIdx] != org[titleIdx]:
            continue
        flag = True
        for c in cols:
            if cur[c] != org[c]:
                flag = False
                break
        if flag:
            return True
    return False
    
def loadOneGP(code, day, name):
    url = 'http://page2.tdx.com.cn:7615/TQLEX?Entry=CWServ.tdxsj_lhbd_ggxq'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
    params = {'Params': ['1', code, day] }
    orgRes = requests.post(url, data=json.dumps(params), headers = headers)
    txt = orgRes.text
    rs = json.loads(txt)
    if ('ErrorCode' not in rs) or (rs['ErrorCode'] != 0):
        print('Error[loadOneGP]: load tdx long hu bang error. day=', day)
        return None
        
    totalInfo = rs['ResultSets'][0]
    # T004(代码), T012（上榜原因）, cjl（成交量）, cje（成交额）, closepri（收盘价）, zdf（涨跌幅）
    totalColNames = totalInfo['ColName']
    totalInfoCnt = totalInfo['Content']

    results = {}
    for r in totalInfoCnt:
        title = getColInfo(totalColNames, r, 'T012')
        obj = {'day': day, 'code': code, 'name': name, 
               'price': getColInfo(totalColNames, r, 'closepri'), 
               'zd': getColInfo(totalColNames, r, 'zdf'),
               #'vol': getColInfo(totalColNames, r, 'cjl'),
               'cjje': getColInfo(totalColNames, r, 'cje'), 
               'title': title,
               'mrje': 0, 'mcje': 0, 'jme': 0, 'famous': '', 'famousBuy':'', 'famousSell': ''} # 'mrjeRate': 0, 'mcjeRate': 0,
        results[ title ] = obj

    infos = rs['ResultSets'][1]
    infosColNames = infos['ColName']
    infosCnt = infos['Content']

    for idx, it in enumerate(infosCnt):
        # 'yz': it[2],
        # ["T007", "T004", "T008", "T009", "T010", "je", "T012", "T006", "T011", "T015", "yxyz", "gsd", "bq1", "bq2", "bq3", "bq4"]
        title = getColInfo(infosColNames, it, 'T012')
        curInfo = results[title]

        if isExsitsCnt(idx, infosColNames, 'T012', infosCnt, ('T008', 'T009', 'T010')):
            continue

        yzDesc = getColInfo(infosColNames, it, 'bq1') or ''
        mrje = getColInfo(infosColNames, it, 'T009') or 0
        mcje = getColInfo(infosColNames, it, 'T010') or 0
        jme = getColInfo(infosColNames, it, 'je') or 0
        bs = getColInfo(infosColNames, it, 'T006') # 'B' or 'S'
        curInfo['mrje'] += mrje
        curInfo['mcje'] += mcje
        curInfo['jme'] += jme

        if not yzDesc:
            continue
        jme /= 10000
        if bs == 'B':
            famousBuy = f'{yzDesc}(+{jme:.1f}); '
            curInfo['famousBuy'] += famousBuy
        elif bs == 'S':
            famousSell = f'{yzDesc}({jme:.1f}); '
            curInfo['famousSell'] += famousSell

    for k, v in results.items():
        if v['famousBuy'] or v['famousSell']:
            v['famous'] = v['famousBuy'] + ' // ' + v['famousSell']
        del v['famousBuy']
        del v['famousSell']
        #print(curInfo['title'], curInfo['mrje'], curInfo['mcje'], curInfo['jme'], curInfo['famous'], sep=' / ')

    datas = []
    for k in results:
        rs = results[k]
        #rs['mrjeRate'] = int(rs['mrje'] * 100 / rs['cjje'])
        #rs['mcjeRate'] = int(rs['mcje'] * 100 / rs['cjje'])
        rs['mrje'] /= 10000 # 万 -> 亿
        rs['mcje'] /= 10000
        rs['jme'] /= 10000
        rs['cjje'] /= 10000
        datas.append(rs)
    return datas

# yyyy-mm-dd
def loadOneDayLHB(day):
    cc = orm.TdxLHB.select().where(orm.TdxLHB.day == day).count()
    result = []
    gps = loadOneDayTotal(day)
    if ((not gps) or (cc == len(gps))):
        return True

    q = orm.TdxLHB.select().where(orm.TdxLHB.day == day)
    oldDatas = [d.code for d in q]
    
    for gp in gps:
        if gp['code'] in oldDatas:
            continue
        scode = gp['code'][0]
        if scode != '3' and scode != '0' and scode != '6':
            continue
        r = loadOneGP(gp['code'], day, gp['name'])
        result.extend(r)
    with orm.db.atomic():
        for batch in pw.chunked(result, 10):
            dd = orm.TdxLHB.insert_many(batch)
            dd.execute()
    if len(result) > 0:
        lt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        print(f'{lt} Success insert  {len(result)} rows for day {day}')
    return True

runLock = threading.RLock()
def loadTdxLHB():
    dayFrom = datetime.date(2023, 1, 1)
    cursor = orm.db.cursor()
    rs = cursor.execute('select min(日期), max(日期) from tdxlhb').fetchall()
    rs = rs[0]
    if rs[0]:
        minDay = datetime.datetime.strptime(rs[0], '%Y-%m-%d').date()
        maxDay = datetime.datetime.strptime(rs[1], '%Y-%m-%d').date()
    else:
        minDay = datetime.date(2023, 1, 1)
        maxDay = datetime.date(2023, 1, 1)

    today = datetime.date.today()
    delta = datetime.timedelta(days=1)
    while dayFrom  <= today:
        if dayFrom.isoweekday() >= 6:
            dayFrom = dayFrom + delta
            continue
        if dayFrom <= maxDay:
            #print('Skip ' + str(dayFrom))
            pass
        else:
            #print('Load day ' + str(dayFrom))
            loadOneDayLHB(dayFrom.strftime('%Y-%m-%d'))
            time.sleep(12)
        dayFrom = dayFrom + delta

def run():
    time.sleep(10)
    th = threading.currentThread()
    while True:
        now = datetime.datetime.now()
        if now.isoweekday() < 6 and now.hour == 20: # 周一至周五, 晚上8点
            loadTdxLHB()
        time.sleep(30 * 60) # 30 minutes

flagAuto = False
lock = threading.RLock()
def autoLoadTdxLHB():
    th = threading.currentThread()
    lock.acquire()
    global flagAuto
    if flagAuto:
        return
    flagAuto = True
    th = threading.Thread(target = run)
    th.start()
    lock.release()
    
if __name__ == '__main__':
    orm.init()
    loadTdxLHB()

    # test
    #loadOneGP('002241', '2022-11-10', '歌尔股份')
    


