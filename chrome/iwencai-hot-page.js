console.log('Load Chrome Extension ..');

function loadHotPageError() {
    let div = document.querySelector('.xuangu-count-line');
    let li = document.createElement("div");
    li.style.color = 'green';
    let newContent = document.createTextNode("源代码已发生变更");
    li.appendChild(newContent);
    div.appendChild(li);
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
    let tb = document.querySelector('.iwc-table-content .iwc-table-scroll table');
    let trs = tb.querySelectorAll('tr');
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

function initPageInfo(task, resolve) {
    let ops = document.querySelectorAll('.drop-down-box > span');
    let txt = ops[0].innerText;
    pageInfo.perpage = parseInt(txt.substring(2));
    pageInfo.pageCount = document.querySelectorAll('.pager .page-item').length;

    getLoginInfo();
    console.log('initPageInfo: ', pageInfo);
    if (! pageInfo.isLogined) {
        // wait 120 secods , for user login
        let we = new Task('wait', 120 * 1000, function (task, resolve) { resolve(); });
        workThread.addTask(we);
    }
    for (let i = 1; i < pageInfo.pageCount && pageInfo.isLogined; ++i) {
        let w2 = new Task('Goto Page', 1000, gotoPage);
        w2.pageIdx = i;
        workThread.addTask(w2);
        
        let w1 = new Task('Get Page Data', 8000, getPageData);
        w1.startOrder = i * pageInfo.perpage + 1;
        workThread.addTask(w1);
    }

    let wx = new Task('Send Page Data', 0, sendPageData);
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
    isLogined: false,

    klineCode: '',
    klineSelectDay : '',
    klineHotInfo : null, // server hot data of select code
};


function buildKlineUI() {
    document.querySelector('.condition-list').style.display = 'none';
    // '#xuangu-table-popup > .popup_main_box'
    let kline = $('#klinePopup');
    kline.css('float', 'left');
    let hots = $('<div id = "kline_hots_info" style="float: left; width: 400px; height: 590px; border: solid 1px #000; overflow: auto;" > </div>');
    kline.after(hots);
    kline.after('<div id="kline_hots_tip" style="float: left; width: 100px; height:590px; background-color: #ccc;" > </div>');

    setInterval(listenKlineDOM, 100);
}

function updateKlineUI() {
    $('#kline_hots_info').empty();
    let tab = $('<table style="text-align:center; " > </table>');
    tab.append('<tr> <th style="width:80px;" >日期 </th>  <th style="width:100px;">时间 </th> <th  style="width:100px;"> 热度值(万) </th> <th style="width:100px;"> 热度排名 </th> </tr>');
    let lastDay = '';
    for (let d in pageInfo.klineHotInfo) {
        let tr = $('<tr />');
        let v = pageInfo.klineHotInfo[d];
        if (v.day != lastDay) {
            tr.append('<td>' + v.day + '</td>');
            tr.css('border-top', 'solid #ccc 1px');
        } else {
            tr.append('<td> </td>');
        }
        lastDay = v.day;
        tr.append('<td>' + v.time + '</td>');
        tr.append('<td>' + v.hotValue + '</td>');
        tr.append('<td>' + v.hotOrder + '</td>');
        tab.append(tr);
    }
    $('#kline_hots_info').append(tab);
}

function markKlineHotDay(oldDay, newDay) {
    if (! pageInfo.klineHotInfo) {
        return;
    }
    let newIdx = -1, oldIdx = -1, lastNewIdx = -1;
    for (let i = 0; i < pageInfo.klineHotInfo.length; i++) {
        let d = pageInfo.klineHotInfo[i];
        if (d.day == newDay && newIdx == -1) {
            newIdx = i;
        } else if (d.day == oldDay && oldIdx == -1) {
            oldIdx = i;
        }
        if (d.day == newDay) {
            lastNewIdx = i;
        }
    }
    if (oldIdx >= 0) {
        let dx = $('#kline_hots_info tr:eq(' + (oldIdx + 1) + ') td:eq(0)');
        dx.css('color', '#000');
    }
    if (newIdx >= 0) {
        let dx = $('#kline_hots_info tr:eq(' + (newIdx + 1) + ') td:eq(0)');
        dx.css('color', 'red' );
    }

    if (newIdx < 0 || lastNewIdx < 0) {
        return;
    }

    let lineHeight = $('#kline_hots_info tr:eq(1)').height();
    let startY = lineHeight * newIdx;
    let endY = lineHeight * (lastNewIdx + 1);
    
}

function listenKlineDOM() {
    let code = $('#klinePopup .code').text();
    if (code != '' && code != pageInfo.klineCode) {
        pageInfo.klineCode = code;
        $('#kline_hots_info').empty();
        pageInfo.klineHotInfo = null;
        // download
        $.get('http://localhost:8071/getHot/' + code, function (result) {
            pageInfo.klineHotInfo = result;
            console.log('Get Server Hot: ', result);
            updateKlineUI();
        });
        return;
    }

    let selectDay = $('#klinePopup .d3charts-tooltip').text().substring(0, 10); // yyyy-MM-dd
    if (selectDay != pageInfo.klineSelectDay) {
        let oldDay = pageInfo.klineSelectDay;
        pageInfo.klineSelectDay = selectDay;
        markKlineHotDay(oldDay, selectDay);
    }
}



// 热股排名页面
if (decodeURI(window.location.href).indexOf('个股热度排名') > 0) {

    // open from bg extention
    if (decodeURI(window.location.href.indexOf('mytag=bg')) > 0) {
        let w1 = new Task('Init Page Info', 8000, initPageInfo);
        workThread.addTask(w1);

        // first page
        let w2 = new Task('Get Page Data', 1000, getPageData);
        w2.startOrder = 1;
        workThread.addTask(w2);

        workThread.start();
    } else {
        setTimeout(buildKlineUI, 8000);
    }
}