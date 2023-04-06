console.log('Load Chrome Extension ..');

function loadHotPageError() {
    let ul = document.querySelectorAll('ul.iwc-table-header-ul');
    let li = document.createElement("li");
    li.style.color = 'green';
    let newContent = document.createTextNode("源代码已发生变更");
    li.appendChild(newContent);
    ul.appendChild(li);
}

function loadHotPage(trs) {
    let heads = document.querySelectorAll('ul.iwc-table-header-ul > li');
    if (heads.length != 4) {
        loadHotPageError();
        return;
    }
    let hotVals = heads[2].innerText.split('\n');
    let hotOrders = heads[3].innerText.split('\n');
    if (hotVals[0] != '个股热度' || hotOrders[0] != '个股热度排名') {
        loadHotPageError();
        return;
    }
    let hotDay = hotVals[1].replaceAll('.', '-');
    let dayRe = /^\d{4}-\d{2}-\d{2}$/;
    if (! dayRe.test(hotDay)) {
        loadHotPageError();
        return;
    }

    let vals = [];
    for (let i = 0; i < trs.length; ++i) {
        let tds = trs[i].querySelectorAll('td');
        if (tds.length != 8) {
            loadHotPageError();
            return;
        }
        let obj = { code: tds[2].innerText, name: tds[3].innerText, hotValue : tds[6].innerText, hotOrder : tds[7].innerText};
        obj.hotValue = parseInt(obj.hotValue);
        obj.hotOrder = parseInt(obj.hotOrder);
        vals.push(obj);
        console.log(obj);
    }
    
    let ct = new Date();
    let hotTime = '';
    if (ct.getHours() < 10)
        hotTime += '0';
    hotTime += ct.getHours();
    hotTime += ':';
    if (ct.getMinutes() < 10)
        hotTime += '0';
    hotTime += ct.getMinutes();

    let msg = { cmd: 'SET_HOT_INFO', data: { hotDay: hotDay, hotTime: hotTime, hotInfo : vals} };

    chrome.runtime.sendMessage( msg
		// function(response) {
		// 	console.log('收到来自后台的回复：' + response);
		// }
	);
}

// 热股排名页面
if (decodeURI(window.location.href).indexOf('个股热度排名') > 0) {
    function check() {
        console.log('Check 个股热度排名 is load finish....');
        let tbs = document.querySelectorAll('table');
        let heads = document.querySelectorAll('ul.iwc-table-header-ul');
        if (tbs.length < 3 || heads.length < 1) {
            setTimeout(check, 500);
            return;
        }
        let cntTable = tbs[1];
        let trs = cntTable.querySelectorAll('tr');
        if (trs.length != 100) {
            setTimeout(check, 500);
            return;
        }

        loadHotPage(trs);
    }
    check();
}