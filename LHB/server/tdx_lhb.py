import peewee as pw
import requests, json, flask
import datetime, time
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
    totalInfoCnt = totalInfo['Content'][0]
    result = {'day': day, 'code': code, 'name': name, 'title': totalInfoCnt[1], 'price': totalInfoCnt[4], 'zd': totalInfoCnt[5], 'vol': totalInfoCnt[2], 'cjje': totalInfoCnt[3], 
                'detail': [], 'mrje': 0, 'mrjeRate': 0, 'mcje': 0, 'mcjeRate': 0, 'jme': 0, 'famous': ''}
    infos = rs['ResultSets'][1]
    infosCnt = infos['Content']
    for it in infosCnt:
        vv = {'yz': it[2], 'mrje': it[3], 'mcje': it[4], 'jme': it[5], 'yzDesc': it[12]}
        vv['mrje'] = vv['mrje'] if vv['mrje'] else 0
        vv['mcje'] = vv['mcje'] if vv['mcje'] else 0
        vv['yzDesc'] = vv['yzDesc'] if vv['yzDesc'] else ''
        vv['mrjeRate'] = vv['mrje'] * 100 / result['cjje']
        vv['mcjeRate'] = vv['mcje'] * 100 / result['cjje']
        result['mrje'] = result['mrje'] + vv['mrje']
        result['mcje'] = result['mcje'] + vv['mcje']
        result['detail'].append(vv)
        if vv['yzDesc'] not in result['famous']:
            result['famous'] = result['famous'] + vv['yzDesc'] + '; '
    result['mrjeRate'] = result['mrje'] * 100 / result['cjje']
    result['mcjeRate'] = result['mcje'] * 100 / result['cjje']
    result['detail'] = json.dumps(result['detail'], ensure_ascii = False)
    result['jme'] = result['mrje'] - result['mcje']
    #print(result['detail'])
    return result

# yyyy-mm-dd
def loadOneDayLHB(day):
    cc = orm.TdxLHB.select().where(orm.TdxLHB.day == day).count()
    if cc > 0:
        print(f'Alreay Exists:  {day} exsits {cc} rows')
        return True

    result = []
    gps = loadOneDayTotal(day)
    for gp in gps:
        r = loadOneGP(gp['code'], day, gp['name'])
        result.append(r)
    with mcore.db.atomic():
        for batch in pw.chunked(result, 10):
            dd = orm.TdxLHB.insert_many(batch)
            dd.execute()
    print(f'Success insert  {len(result)} rows for day {day}')
    return True


def loadTdxLHB():
    dayFrom = datetime.datetime(2022, 1, 4)
    cursor = mcore.db.cursor()
    rs = cursor.execute('select min(日期), max(日期) from tdxlhb').fetchall()
    if len(rs) > 0:
        minDay = datetime.datetime.strptime(rs[0][0], '%Y-%m-%d')
        maxDay = datetime.datetime.strptime(rs[0][1], '%Y-%m-%d')
    else:
        minDay = datetime.datetime(2022, 1, 1)
        maxDay = datetime.datetime(2022, 1, 1)

    now = datetime.datetime.now()
    delta = datetime.timedelta(days=1)
    while dayFrom  < now:
        if dayFrom >= minDay and dayFrom <= maxDay:
            print('Skip ' + str(dayFrom))
        else:
            print('Load day ' + str(dayFrom))
            loadOneDayLHB(dayFrom.strftime('%Y-%m-%d'))
            time.sleep(12.35)
        dayFrom = dayFrom + delta

if __name__ == '__main__':
    orm.init()
    loadTdxLHB()

