var youZiML = {
	"华鑫证券有限责任公司上海红宝石路证券营业部" :  "炒股养家",
	"中国银河证券股份有限公司绍兴证券营业部" : "赵老哥",
	"申银万国上海陆家嘴营业部"  : "徐翔",
	"国泰君安上海打浦路营业部" : "徐翔",
	"中信证券上海浦东大道营业部" : "徐翔",
	"光大证券杭州庆春路营业部": "孙哥",
	"兴业证券福州湖东路营业部" : "asking",
	"兴业证券股份有限公司陕西分公司" : "方新侠",
	"国泰君安证券股份有限公司总部": "境外机构",
	"华泰证券股份有限公司总部" : "量化基金",
	"兴业证券股份有限公司厦门分公司" : "首板挖掘",
	"中国国际金融股份有限公司上海分公司" : "量化基金",
	"上海证券有限责任公司苏州太湖西路证券营业部" : "涅槃重生",
	"东莞证券股份有限公司四川分公司" : "苏南帮",
	"长江证券股份有限公司佛山普澜二路证券营业部" : "佛山系",
	"中国银河证券股份有限公司北京中关村大街证券营业部" : "苏南帮",
	"中国银河证券股份有限公司北京学院南路证券营业部" : "苏南帮",
	"国泰君安证券股份有限公司上海江苏路证券营业部" : "章盟主",
	"国泰君安证券股份有限公司宁波广福街证券营业部": "章盟主",
	"华鑫证券有限责任公司上海茅台路证券营业部": "炒股养家",
};


function resoleYouZi() {
	let style = ' style="background: #22b935; color: #fff; " ';
	// $('.m-table.m-table-nosort.mt10')
	$('.tl.rel').each(function() {
		let name = $(this).children().attr('title').trim();
		if (youZiML[name]) {
			$(this).append($('<span + ' + style + '> [' + youZiML[name] + '] <span>'));
		} else if (name.indexOf('拉萨') > 0) {
			$(this).append($('<span + ' + style + '> [T] <span>'));
		}
	});
}

function bindDayChange() {
	$('iframe').each(function() {
		if ($(this).attr('src') != "http://data.10jqka.com.cn/js/My97DatePicker/My97DatePicker.htm")
			return;
		DC = this.contentWindow.day_Click;
		console.log(DC);
		this.contentWindow.day_Click = function(F, B, _, D, C, A) {
			DC(F, B, _, D, C, A);
			setTimeout(function() {
				resoleYouZi();
			}, 2000);
		};
	});
}

setTimeout(function() {
	bindDayChange();
	resoleYouZi();
}, 2000);

