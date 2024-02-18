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
		let gn = tds.eq(6).text().trim();
        let hy = tds.eq(10).text().trim();
		console.log(code + '\t' + name + '\t' +  hy + '\t' +  gn);
	}
}
"""
import sys

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from THS import orm

f = open('D:/a.txt', 'r', encoding='utf8')
lines = f.readlines()
f.close()
models = []
for line in lines:
    line = line.strip()
    if not line:
        continue
    code, name, hy, gn = line.split('\t', 3)
    hy = hy.strip()
    gn = gn.strip()
    if ' ' in gn:
        gn = gn.replace(' ', '')
    obj = orm.THS_GNTC.get_or_none(orm.THS_GNTC.code == code)
    if obj:
        obj.hy = hy
        obj.name = name
        obj.gn = gn
        obj.save()
        print('update ', code, name, hy, gn)
    else:
        orm.THS_GNTC.create(code = code, name = name, gn = gn, hy = hy)
        print('insert ', code, name,hy, gn)

    

