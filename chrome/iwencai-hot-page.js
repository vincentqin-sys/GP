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
        return null;
    }
    let hotVals = heads[2].innerText.split('\n');
    let hotOrders = heads[3].innerText.split('\n');
    if (hotVals[0] != '个股热度' || hotOrders[0] != '个股热度排名') {
        loadHotPageError();
        return null;
    }
    let hotDay = hotVals[1].replaceAll('.', '-');
    let dayRe = /^\d{4}-\d{2}-\d{2}$/;
    if (! dayRe.test(hotDay)) {
        loadHotPageError();
        return null;
    }

    let vals = [];
    for (let i = 0; i < trs.length; ++i) {
        let tds = trs[i].querySelectorAll('td');
        if (tds.length != 8) {
            loadHotPageError();
            return null;
        }
        let obj = { code: tds[2].innerText, name: tds[3].innerText, hotValue : tds[6].innerText, hotOrder : tds[7].innerText};
        obj.hotValue = parseInt(obj.hotValue);
        obj.hotOrder = parseInt(obj.hotOrder);
        vals.push(obj);
        // console.log(obj);
    }
    pageInfo.hotDay = hotDay;

    return vals;
}

function getPageData(task, resolve) {
    let tbs = document.querySelectorAll('table');
    let cntTable = tbs[1];
    let trs = cntTable.querySelectorAll('tr');
    let datas = loadHotPage(trs);

    if (datas[0].hotOrder == task.startOrder) {
        for (let d in datas) {
            pageInfo.hotPageDatas.push(datas[d]);
        }
    }
    
    resolve();
}

function gotoPage(task, resolve) {
    let pageIdx = task.pageIdx;
    let pi = document.querySelectorAll('.pager .page-item > a');
    let a = pi[pageIdx];
    console.log('gotoPage: ', task, a);
    a.click();
    resolve();
}

function sendPageData(task, resolve) {
    console.log('sendPageData: ', pageInfo.hotPageDatas);
    let ct = new Date();
    let hotTime = '';
    if (ct.getHours() < 10)
        hotTime += '0';
    hotTime += ct.getHours();
    hotTime += ':';
    if (ct.getMinutes() < 10)
        hotTime += '0';
    hotTime += ct.getMinutes();

    let msg = { cmd: 'SET_HOT_INFO', data: { hotDay: pageInfo.hotDay, hotTime: hotTime, hotInfo: pageInfo.hotPageDatas } };

    chrome.runtime.sendMessage(msg
        // function(response) {
        // 	console.log('收到来自后台的回复：' + response);
        // }
    );

    resolve();
}

function getPageInfo(task, resolve) {
    let ops = document.querySelectorAll('.drop-down-box > span');
    let txt = ops[0].innerText;
    pageInfo.perpage = parseInt(txt.substring(2));
    pageInfo.pageCount = document.querySelectorAll('.pager .page-item').length;

    getLoginInfo();
    console.log('getPageInfo: ', pageInfo);

    for (let i = 1; i < pageInfo.pageCount && pageInfo.isLogined; ++i) {
        let w2 = new Task('gotoPage', 1000, gotoPage);
        w2.pageIdx = i;
        workThread.addTask(w2);
        
        let w1 = new Task('getPageData', 8000, getPageData);
        w1.startOrder = i * pageInfo.perpage + 1;
        workThread.addTask(w1);
    }
    if (! pageInfo.isLogined) {
        // wait 120 secods , for user login
        let we = new Task('wait', 120 * 1000, function (task, resolve, reject) { resolve(); });
        workThread.addTask(we);
    }
    let wx = new Task('sendPageData', 0, sendPageData);
    workThread.addTask(wx);

    resolve();
}

function getLoginInfo() {
    let btns = document.querySelectorAll('.login-box .login_btn ');
    if (btns.length > 0) {
        pageInfo.isLogined = false;
        return true;
    }
    let users = document.querySelectorAll('.login-box .user-photo');
    if (users.length > 0) {
        pageInfo.isLogined = true;
        return true;
    }

    console.log('getLoginInfo: 无法确定是否已登录，代码需修改');
    loadHotPageError();
    return false;
}

var workThread = new Thread();
var pageInfo = {
    pageCount: 0,
    perpage: 0,
    hotPageDatas: [],
    isLogined : false,
};

// 热股排名页面
if (decodeURI(window.location.href).indexOf('个股热度排名') > 0) {
    let w1 = new Task('getPageInfo', 8000, getPageInfo);
    workThread.addTask(w1);

    // first page
    let w2 = new Task('getPageData', 1000, getPageData);
    w2.startOrder = 1;
    workThread.addTask(w2);

    workThread.start();
}