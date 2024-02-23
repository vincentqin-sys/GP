console.log('Load Chrome Extension ..');

function loadHeaders() {
    let ths = $('table.watch-table tr:eq(0) > th');
    let rs = [];
    for (let i = 0; i < ths.length; i++) {
        let title = ths.eq(i).text().trim();
        if (title == '股票/代码' || title == '连续涨停数' || title == '动因') {
            rs.push({idx: i, title: title});
        }
    }
    if (rs.length != 3) {
        console.log('[CLS] 1.chrome.extension error, not find all headers', rs, ths);
    }
    return rs;
}

function loadOneRow(tds) {
    let obj = {};
    for (let i = 0; i < headers.length; i++) {
        let h = headers[i];
        let cnt = tds.eq(h.idx).text().trim();
        if (h.title == '股票/代码') {
            let idx = cnt.indexOf('sz');
            if (idx < 0) idx = cnt.indexOf('sh');
            if (idx < 0) {
                console.log('[CLS] 2.chrome.extension error, 代码发生更新，请修改代码', tds);
                return null;
            }
            obj['name'] = cnt.substring(0, idx);
            obj['code'] = cnt.substring(idx + 2);
            if (obj['name'].indexOf('ST') >= 0) {
                // 忽略ST股
                return null;
            }
        } else if (h.title == '连续涨停数') {
            obj['lbs'] = cnt;
        } else if (h.title == '动因') {
            let idx = cnt.indexOf('|');
            if (cnt == '--') {
                obj['ztReason'] = obj['detail'] = '';
            } else if (idx < 0) {
                console.log('[CLS] 3.chrome.extension error, 代码发生更新，请修改代码', tds);
                return null;
            } else {
                obj['ztReason'] = cnt.substring(0, idx);
                obj['detail'] = cnt.substring(idx + 1);
            }
        }
    }
    return obj;
}

function loadPageData() {
    let day = loadDay();
    let trs = $('table.watch-table tr:gt(0)');
    let rs = [];
    for (let i = 0; i < trs.length; i++) {
        let tr = trs.eq(i);
        let tds = tr.find('td');
        let val = loadOneRow(tds);
        if (val && day) {
            val.day = day;
            rs.push(val);
        }
        console.log(val);
    }
    return rs;
}

function loadDay() {
    let day = $('.event-querydate-selected').text();
    if (! day) {
        console.log('[CLS] 4.chrome.extension error, 代码发生更新，请修改代码', day);
        return null;
    }
    day = day.replaceAll('/', '-')
    return day;
}

function sendToServer(data) {
    if (data.length < 0) {
        return;
    }
    $.ajax({
        url: 'http://localhost:8071/save-CLS-ZT',
        method: 'POST',
        dataType: 'json',
        contentType : 'application/json',
        data: JSON.stringify(data),
        success: function (res) {
            console.log('Success: Send ZS info to server success ', res);
            let day = data[0].day;
            chrome.runtime.sendMessage({cmd: 'SAVED_ZT', data: {day : day, data: data}});
        },
        error: function (res) {
            console.log('Fail: Send ZS info to server fail ', data);
        }
    });
}

// YYYY-MM-DD
function formatDate() {
    let d = new Date();
    let m = d.getMonth() + 1;
    return '' + d.getFullYear() + '-' + (m > 9 ? m : '0' + m) + '-' + (d.getDate() > 9 ? d.getDate() : '0' + d.getDate());
}

// HH:MM
function formatTime() {
    let d = new Date();
    let h = d.getHours();
    let m = d.getMinutes();
    let v = '';
    v += h > 9 ? h : '0' + h;
    v += ':';
    v += m > 9 ? m : '0' + m;
    return v;
}

setTimeout(() => {
    headers = loadHeaders();
    data = loadPageData();
    sendToServer(data);
}, 15 * 1000);


if (formatTime() >= '09:25' && formatTime() <= '15:00') {
    setTimeout(() => {
        window.location.reload();
    }, 3 * 60 * 1000);
}

