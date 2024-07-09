"""
同花顺 个股行业概念信息

https://www.iwencai.com/unifiedwap/result?w=%E4%B8%AA%E8%82%A1%E5%8F%8A%E8%A1%8C%E4%B8%9A%E6%9D%BF%E5%9D%97&querytype=stock

function nextPage() {
	let np = $('ul.pcwencai-pagination > li:last');
	np.find('a').get(0).click();
}

function loadPageData() {
	trs = $('.iwc-table-body.scroll-style2.big-mark > table tr');
	for (let i = 0; i < trs.length; i++) {
		let tds = trs.eq(i).find('td');
		let code = tds.eq(2).text();
		let name = tds.eq(3).text();
		let gn = tds.eq(7).text().trim();
        let hy = tds.eq(6).text().trim();
		console.log(code + '\t' + name + '\t' +  hy + '\t' +  gn);
	}
}

var lp = 0;
_lpID = setInterval(function() {
    loadPageData(); nextPage();
    lp++;
    if (lp > 53) {
        clearInterval(_lpID);
    }
}, 3000);


"""
import sys, peewee as pw, requests, json, re, traceback, time, datetime

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from db import ths_orm
from Common import holiday
from Download import henxin, console

# 在 i问财搜索结果，(第一面的数据)
# 例： question = '个股及行业板块' -->  http://www.iwencai.com/unifiedwap/result?w=个股及行业板块&querytype=stock
# @return 数据:list, more-url: str, 结果数量: int
# intent = 'stock' | 'zhishu' 用于指明是个股还是指数
# input_type = 'typewrite' | 'click'   typewrite: 点击搜索的方式查询   click:在url地址上附加查询参数的方式查询
def iwencai_search_page_1(question, intent = 'stock', input_type = 'typewrite'):
    url = 'http://www.iwencai.com/customized/chart/get-robot-data'
    data = {
        'source': 'Ths_iwencai_Xuangu',
        'version': '2.0',
        'query_area': '',
        'block_list': '',
        'add_info' : '{"urp":{"scene":1,"company":1,"business":1},"contentType":"json","searchInfo":true}',
        'question': question,
        'perpage': '100',
        'page': 1,
        'secondary_intent': intent,
        'log_info': '{"input_type":"' + input_type + '"}',
    }
    hx = henxin.Henxin()
    hx.init()
    hexin_v = hx.update()
    headers = {'Accept': 'application/json, text/plain, */*',
                'hexin-v': hexin_v,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Encoding': 'gzip, deflate',
                'Content-Type': 'application/json',
                'Pragma': 'no-cache',
                'Cache-control': 'no-cache',
                'Origin': 'http://www.iwencai.com',
                #'Referer': 'http://www.iwencai.com/unifiedwap/result?w=%E4%B8%AA%E8%82%A1%E5%8F%8A%E8%A1%8C%E4%B8%9A%E6%9D%BF%E5%9D%97&querytype=stock',
                }
    #pstr = json.dumps(data, ensure_ascii = False)
    resp = requests.post(url, json = data, headers = headers)
    txt = resp.text
    js = json.loads(txt)
    answer = js['data']['answer'][0]
    components = answer['txt'][0]['content']['components'][0]
    data = components['data']
    meta = data['meta']
    count = meta['extra']['code_count']
    #info = {'ret': meta['ret'], 'sessionid': meta['sessionid'], 'source': meta['source'], 'logid': js['logid'],
    #        }
    moreUrl = components['config']['other_info']['footer_info']['url']
    moreUrl = 'http://www.iwencai.com' + moreUrl
    ma = re.match('^(.*?perpage=)\d+(.*)$', moreUrl)
    moreUrl = ma.group(1) + '100' + ma.group(2)
    ma = re.match('^(.*?[&?]page=)\d+(.*)$', moreUrl)
    moreUrl = ma.group(1) + '###' + ma.group(2)
    return data['datas'], moreUrl, count

# 按页下载个股数据，每页100个（共5400余个股票）
# page = [2...54] 从第二页开始
def iwencai_load_page_n(page : int, moreUrl):
    url = moreUrl.replace('###', str(page))
    hx = henxin.Henxin()
    hx.init()
    headers = {'Accept': 'application/json, text/plain, */*',
                'hexin-v': hx.update(),
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Encoding': 'gzip, deflate',
                'Pragma': 'no-cache',
                'Cache-control': 'no-cache',
                'Origin': 'http://www.iwencai.com',
                }
    resp = requests.get(url, headers = headers)
    txt = resp.text
    js = json.loads(txt)
    data = js['answer']['components'][0]['data']
    columns = data['columns']
    datas = data['datas']
    return datas

# 在 i问财搜索结果，返回所有页的数据
# 例： question = '个股及行业板块' -->  http://www.iwencai.com/unifiedwap/result?w=个股及行业板块&querytype=stock
# intent = 'stock' | 'zhishu' 用于指明是个股还是指数
# input_type = 'typewrite' | 'click'
# @return list
def iwencai_search(question, intent = 'stock', input_type = 'typewrite'):
    rs = []
    try:
        data1, urlMore, count = iwencai_search_page_1(question, intent, input_type)
        rs.extend(data1)
        maxPage = (count + 99) // 100
        for i in range(2, maxPage + 1):
            datas = iwencai_load_page_n(i, urlMore)
            rs.extend(datas)
            time.sleep(1)
    except Exception as e:
        traceback.print_exc()
    return rs

def modify_hygn(obj : ths_orm.THS_GNTC, zsInfos):
    gn_code = []
    for g in obj.gn.split(';'):
        gcode = zsInfos.get(g, '')
        gn_code.append(gcode)
    gn_code = ';'.join(gn_code)
    hys = obj.hy.split('-')
    hy_2_code = zsInfos.get(hys[1], '')
    hy_3_code = zsInfos.get(hys[2], '')
    obj.gn_code = gn_code
    obj.hy_2_code = hy_2_code
    obj.hy_3_code = hy_3_code
    obj.hy_2_name = hys[1]
    obj.hy_3_name = hys[2]

# 个股行业概念
# @return update-datas, insert-datas
def download_hygn():
    # 下载所有的 个股行业概念（含当日涨跌信息）
    # code 市盈率(pe)[20240708],  总股本[20240708]  所属概念  所属同花顺行业  最新涨跌幅  最新价 股票简称
    rs = iwencai_search(question = '个股及行业板块')
    zsInfos = {}
    qr = ths_orm.THS_ZS.select()
    for q in qr:
        zsInfos[q.name] = q.code
    updates = []
    inserts = []
    for idx, line in enumerate(rs):
        code, name, hy, gn = line['code'], line['股票简称'], line['所属同花顺行业'], line['所属概念']
        hy = hy.strip()
        gn = gn.strip()
        gns = gn.split(';')
        gn = ';'.join(gns)
        obj = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == code)
        if obj:
            if obj.hy != hy or obj.gn != gn or obj.name != name:
                obj.hy = hy
                obj.name = name
                obj.gn = gn
                modify_hygn(obj, zsInfos)
                updates.append(obj)
        else:
            obj = ths_orm.THS_GNTC(code = code, name = name, gn = gn, hy = hy)
            modify_hygn(obj, zsInfos)
            inserts.append(obj)
    return updates, inserts

# @return (update-num, insert-num)
def save_hygn(updateDatas, insertDatas):
    for it in updateDatas:
        it.save()
    for it in insertDatas:
        it.save()
    return len(updateDatas), len(insertDatas)


# dde大单净额
# @return data : list (前100 + 后100)
def download_dde_money():
    亿 = 100000000
    rs = iwencai_search('个股及行业板块, 最新dde大单净额')
    datas = []
    for row in rs:
        obj = ths_orm.THS_DDE()
        datas.append(obj)
        for k in row:
            v = row[k]
            if k == 'code': obj.code = v
            elif k == '股票简称': obj.name = v
            elif k.startswith('dde大单净额'):
                obj.dde = float(v) / 亿
                day = k[8 : 16]
                obj.day = day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
            elif 'dde大单卖出金额' in k: obj.dde_sell = float(v) / 亿
            elif 'dde大单买入金额' in k: obj.dde_buy = float(v) / 亿

    datas.sort(key = lambda d: d.dde, reverse = True)
    ndatas = []
    for i in range(100):
        datas[i].dde_pm = i + 1
        ndatas.append(datas[i])
    for i in range(-1, -101, -1):
        datas[i].dde_pm = i
        ndatas.append(datas[i])
    return ndatas

def save_dde_money(rs):
    if not rs:
        return False
    day = rs[0].day
    count = ths_orm.THS_DDE.select(pw.fn.count()).where(ths_orm.THS_DDE.day == day).scalar()
    if count > 0:
        return False # alreay exists
    ths_orm.THS_DDE.bulk_create(rs, 50)
    return True

# 个股热度排名
# http://www.iwencai.com/unifiedwap/result?w=个股热度排名<%3D200且个股热度从大到小排名&querytype=stock
# code, 股票简称, 个股热度[20240709], 个股热度排名[20240709]
def download_hot():
    rs = iwencai_search('个股热度排名<=200且个股热度从大到小排名')
    now = datetime.datetime.now()
    _time = now.hour * 100 + now.minute
    hots = []
    for row in rs:
        obj = ths_orm.THS_Hot()
        obj.time = _time
        for k in row:
            if k == 'code': obj.code = int(row[k])
            elif '个股热度排名[' in k:
                obj.day = int(k[7 : 15])
                v = row[k]
                obj.hotOrder = int(v[0 : v.index('/')])
            elif '个股热度[' in k:
                obj.hotValue = int(row[k]) // 10000
        hots.append(obj)
    return hots

# @return 数量
def save_hot(hots):
    ths_orm.THS_Hot.bulk_create(hots, 50)
    return len(hots)

# 指数涨跌信息
# http://www.iwencai.com/unifiedwap/result?w=同花顺概念指数或同花顺行业指数按涨跌幅排序&querytype=zhishu
# @return  data : list
# code, 指数简称, 指数@涨跌幅:前复权[20240709]
def download_zs_zd():
    rs = iwencai_search('同花顺概念指数或同花顺行业指数按涨跌幅排序', 'zhishu', 'click')
    datas = []
    亿 = 100000000
    RK = '指数@涨跌幅:前复权['
    for row in rs:
        obj = ths_orm.THS_ZS_ZD()
        datas.append(obj)
        for k in row:
            if k == 'code': obj.code = row[k]
            elif k == '指数简称': obj.name = row[k]
            elif RK in k:
                day = k[len(RK) : len(RK) + 8]
                obj.day = f'{day[0 : 4]}-{day[4 : 6]}-{day[6 : 8]}'
                obj.zdf = float(row[k])
            elif '成交量' in k: obj.vol = int(float(row[k]) / 亿)
            elif '成交额' in k: obj.money = int(float(row[k]) / 亿)
            elif '开盘价' in k: obj.open = float(row[k])
            elif '最高价' in k: obj.high = float(row[k])
            elif '收盘价' in k: obj.close = float(row[k])
            elif '换手率' in k: obj.rate = float(row[k])
    return datas

def save_zs_zd(datas):
    for i in range(len(datas)):
        if i <= len(datas) // 2:
            datas[i].zdf_PM = i + 1
        else:
            datas[i].zdf_PM = i - len(datas)
    d50 = [d for d in datas if d.money >= 50]
    for i in range(len(d50)):
        if i <= len(d50) // 2:
            d50[i].zdf_50PM = i + 1
        else:
            d50[i].zdf_50PM = i - len(d50)
    day = datas[0].day
    q = ths_orm.THS_ZS_ZD.select().where(ths_orm.THS_ZS_ZD.day == day).dicts()
    ex = {}
    for it in q:
        ex[it['code']] = True
    ndatas = []
    for it in datas:
        if it.code not in ex:
            ndatas.append(it)
    ths_orm.THS_ZS_ZD.bulk_create(ndatas, 50)
    return len(ndatas)

if __name__ == '__main__':
    rs = download_dde_money()
    save_dde_money(rs)
    
    #download_hygn()
    #download_hot()
    #rs = download_zs_zd()
    #save_zs_zd(rs)
    pass