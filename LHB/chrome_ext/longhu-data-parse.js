var codeInfos = [];

function initCodeInfos() {
	let trArr = $('.twrap > table.m-table tr');
	for (let i = 0; i < trArr.length; i++) {
		let tdArr = trArr.eq(i).children('td');
		let item = {};
		item.tag = tdArr.eq(0).text().trim();
		item.code = tdArr.eq(1).text().trim();
		if (item.code.charAt(0) != '0' && item.code.charAt(0) != '3' && item.code.charAt(0) != '6')
			continue;
		let a = tdArr.eq(2).children('a');
		item.name = a.text().trim();
		item.rid = a.attr('rid');
		item.price = tdArr.eq(3).text().trim();
		item.zd = tdArr.eq(4).text().trim(); // 涨跌幅
		item.cjje = tdArr.eq(5).text().trim(); // 成交金额
		item.jme = tdArr.eq(6).text().trim(); // 净买额
		codeInfos.push(item);
	}
}

function findCodeInfoByRid(rid) {
	for (let i = 0; i < codeInfos.length; ++i) {
		if (codeInfos[i].rid == rid) {
			return codeInfos[i];
		}
	}
	return null;
}

function initDetailInfo() {
	let detailArr = $('.rightcol.fr > div');
	for (let i = 0; i < detailArr.length; ++i) {
		let it = detailArr.eq(i);
		let title = it.children('p').text().trim();
		title = title.substring(title.indexOf('：') + 1);
		let detail = {};
		detail.rid = it.attr('rid');
		if (! detail.rid) {
			continue;
		}
		detail.title = title;
		detail.data = [];
		let trs = it.find('div.cell-cont.cjmx > table > tbody > tr');
		for (let j = 0; j < trs.length; ++j) {
			let obj = {};
			let tds = trs.eq(j).children('td');
			obj.yyb = tds.eq(0).children('a').attr('title'); // 营业部
			obj.mrje = tds.eq(1).text().trim() + '万'; // 买入金额
			obj.mcje = tds.eq(2).text().trim() + '万'; // 卖出金额
			obj.jme = tds.eq(3).text().trim() + '万'; // 净买额
			detail.data.push(obj);
		}
		// console.log(detail);
		let code = findCodeInfoByRid(detail.rid);
		if (! code) {
			console.log('Error: ', detail, codeInfos);
		} else {
			code.detail = detail;
		}
	}

}

function fetchLHB() {
	codeInfos = [];
	initCodeInfos();
	initDetailInfo();
	console.log(codeInfos);
	let dd = {};
	dd.day = $('input.m_text_date.startday').val();
	dd.data = codeInfos;
	let txt = JSON.stringify(dd);
	console.log(txt);
	window.postMessage({cmd: 'LONGHU_DATA_LIST', data: dd}, window.location.href);
}

fetchLHB();
