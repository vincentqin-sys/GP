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
import sys, peewee as pw, requests, json

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from db import ths_orm
import henxin

# page = [1...54]
# 按页下载个股行业概念，每页100个（共5400余个股票）
def download_hygn(page : int):
    url = 'http://www.iwencai.com/customized/chart/get-robot-data'
    data = {
        'source': 'Ths_iwencai_Xuangu',
        'version': '2.0',
        'query_area': '',
        'block_list': '',
        'add_info' : '{"urp":{"scene":1,"company":1,"business":1},"contentType":"json","searchInfo":true}',
        'question': '个股及行业板块',
        'perpage': '100',
        'page': page,
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
    print(txt)
    pass

download_hygn(1)

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

def run_个股行业概念():
    def trim(s): return s.replace('【', '').replace('】', '').strip()

    f = open('D:/a.txt', 'r', encoding='utf8')
    lines = f.readlines()
    f.close()
    zsInfos = {}
    qr = ths_orm.THS_ZS.select()
    for q in qr:
        zsInfos[q.name] = q.code

    for line in lines:
        line = line.strip()
        if not line:
            continue
        code, name, hy, gn = line.split('\t', 3)
        hy = hy.strip()
        gn = gn.strip()
        gns = list(map(trim, gn.split(';')))
        gn = ';'.join(gns)
        obj = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == code)
        if obj:
            if obj.hy != hy or obj.gn != gn:
                obj.hy = hy
                obj.name = name
                obj.gn = gn
                print('update ', code, name, hy, gn)
                modify_hygn(obj, zsInfos)
                obj.save()
        else:
            obj = ths_orm.THS_GNTC(code = code, name = name, gn = gn, hy = hy)
            modify_hygn(obj, zsInfos)
            obj.save()
            print('insert ', code, name,hy, gn)
