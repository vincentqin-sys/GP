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
def iwencai_search_page_1(question, intent = 'stock'):
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
        'log_info': '{"input_type":"typewrite"}',
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
# @return list
def iwencai_search(question, intent = 'stock'):
    rs = []
    try:
        data1, urlMore, count = iwencai_search_page_1(question, intent)
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
# @return data : list
def download_hygn():
    # 下载所有的 个股行业概念（含当日涨跌信息）
    # code 市盈率(pe)[20240708],  总股本[20240708]  所属概念  所属同花顺行业  最新涨跌幅  最新价 股票简称
    rs = iwencai_search(question = '个股及行业板块')
    return rs

# @return False | (insertNum, updateNum)
def save_hygn(rs, log : bool = True):
    zsInfos = {}
    qr = ths_orm.THS_ZS.select()
    for q in qr:
        zsInfos[q.name] = q.code

    for idx, line in enumerate(rs):
        if ('code' not in line) or ('股票简称' not in line) or ('所属同花顺行业' not in line) or ('所属概念' not in line):
            print('[ths_iwencai.download_hygn] Error: not find column', line)
            return False
        code, name, hy, gn = line['code'], line['股票简称'], line['所属同花顺行业'], line['所属概念']
        hy = hy.strip()
        gn = gn.strip()
        gns = gn.split(';')
        gn = ';'.join(gns)
        obj = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == code)
        insertNum, updateNum = 0, 0
        if obj:
            if obj.hy != hy or obj.gn != gn or obj.name != name:
                obj.hy = hy
                obj.name = name
                obj.gn = gn
                updateNum += 1
                if not log:
                    print(f'[{idx :04d}]', 'update ', code, name, hy, gn)
                modify_hygn(obj, zsInfos)
                obj.save()
        else:
            obj = ths_orm.THS_GNTC(code = code, name = name, gn = gn, hy = hy)
            modify_hygn(obj, zsInfos)
            obj.save()
            insertNum += 1
            if not log:
                print(f'[{idx :04d}]', 'insert ', code, name,hy, gn)
    if log:
        print(f'[download_hygn] insertNum ={insertNum} updateNum={updateNum}')
    return insertNum, updateNum

# dde大单净额
# @return data : list
def download_dde_money():
    rs = iwencai_search('个股及行业板块, 最新dde大单净额')
    return rs

# 个股热度排名
# http://www.iwencai.com/unifiedwap/result?w=个股热度排名<%3D200且个股热度从大到小排名&querytype=stock
# code, 股票简称, 个股热度[20240709], 个股热度排名[20240709]
def download_hot():
    rs = iwencai_search('个股热度排名<=200且个股热度从大到小排名')
    return rs

# @return 数量, 日期, 时间
def save_hot(rs):
    now = datetime.datetime.now()
    _time = now.hour * 100 + now.minute
    if not rs:
        return 0, 0, 0
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
    ths_orm.THS_Hot.bulk_create(hots, 50)
    return len(rs), hots[0].day, _time

# 指数涨跌信息
# http://www.iwencai.com/unifiedwap/result?w=同花顺概念指数或同花顺行业指数按涨跌幅排序&querytype=zhishu
# @return True | False
def download_zs_zd():
    rs = iwencai_search('同花顺概念指数或同花顺行业指数按涨跌幅排序', 'zhishu')
    if not rs:
        return False
    

if __name__ == '__main__':
    #download_dde_money()
    #download_hygn(False)
    download_hot()
    pass