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
import sys, peewee as pw, requests, json, re, traceback, time

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from db import ths_orm
import henxin

# 下载第一页的 “个股行业概念”，前100个股票
def download_hygn_page_1():
    url = 'http://www.iwencai.com/customized/chart/get-robot-data'
    data = {
        'source': 'Ths_iwencai_Xuangu',
        'version': '2.0',
        'query_area': '',
        'block_list': '',
        'add_info' : '{"urp":{"scene":1,"company":1,"business":1},"contentType":"json","searchInfo":true}',
        'question': '个股及行业板块',
        'perpage': '100',
        'page': 1,
        'secondary_intent': 'stock',
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
                'Referer': 'http://www.iwencai.com/unifiedwap/result?w=%E4%B8%AA%E8%82%A1%E5%8F%8A%E8%A1%8C%E4%B8%9A%E6%9D%BF%E5%9D%97&querytype=stock',
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

# 按页下载个股行业概念，每页100个（共5400余个股票）
# page = [2...54] 从第二页开始
def download_hygn_page_n(page : int, moreUrl):
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

# 下载所有的 个股行业概念（含当日涨跌信息）
# code 市盈率(pe)[20240708],  总股本[20240708]  所属概念  最新dde大单净额  所属同花顺行业  最新涨跌幅  最新价 股票简称
def download_hygn_all():
    rs = []
    try:
        data1, urlMore, count = download_hygn_page_1()
        rs.extend(data1)
        maxPage = (count + 99) // 100
        for i in range(2, maxPage + 1):
            datas = download_hygn_page_n(i, urlMore)
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

# @return False | True
def run_个股行业概念(simple : bool = True):
    def trim(s): return s.replace('【', '').replace('】', '').strip()

    rs = download_hygn_all()
    if not rs:
        return False
    zsInfos = {}
    qr = ths_orm.THS_ZS.select()
    for q in qr:
        zsInfos[q.name] = q.code

    for idx, line in enumerate(rs):
        code, name, hy, gn = line['code'], line['股票简称'], line['所属同花顺行业'], line['所属概念']
        hy = hy.strip()
        gn = gn.strip()
        gns = list(map(trim, gn.split(';')))
        gn = ';'.join(gns)
        obj = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == code)
        insertNum, updateNum = 0, 0
        if obj:
            if obj.hy != hy or obj.gn != gn or obj.name != name:
                obj.hy = hy
                obj.name = name
                obj.gn = gn
                updateNum += 1
                if not simple:
                    print(f'[{idx :04d}]', 'update ', code, name, hy, gn)
                modify_hygn(obj, zsInfos)
                obj.save()
        else:
            obj = ths_orm.THS_GNTC(code = code, name = name, gn = gn, hy = hy)
            modify_hygn(obj, zsInfos)
            obj.save()
            insertNum += 1
            if not simple:
                print(f'[{idx :04d}]', 'insert ', code, name,hy, gn)
    print(f'[run_个股行业概念] insertNum ={insertNum} updateNum={updateNum}')
    return True

if __name__ == '__main__':
    run_个股行业概念(False)