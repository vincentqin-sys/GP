let timelines = {}; // key : {model, ui }
let pageInfo = { tableColNum : 0 };
window['pageInfo'] = pageInfo;
let thread = new Thread();
const ADD_WIDTH = 300;

function updateFinacePageUI(code) {
    let item = timelines[code];
    if (! item) {
        return;
    }
    if (item.ui) {
        item.ui.remove();
    } else {
        item.view = new TimeLineView(ADD_WIDTH, 40);
        item.ui = $(item.view.canvas);
    }
    // check is same
    let changed = !item.model  || !item.view.data || item.view.data.dataArr.length != item.model.dataArr.length;
    item.view.setData(item.model);
    let table = $('table.watch-table');
    let trs = table.find('tr');
    for (let i = 1; i < trs.length; i++) {
        let tr = trs.eq(i);
        let rowCode = getCodeInTd(tr);
        if (rowCode == code) {
            let tds = tr.find('td');
            let td = null;
            if (tds.length < pageInfo.tableColNum) {
                td = $('<td> </td>');
                tr.append(td);
            } else {
                td = tr.find('td:last');
                td.empty();
            }
            td.append(item.ui);
            break;
        }
    }
    if (changed) {
        item.view.draw();
    }
}

function loadTimeLine(task, resolve) {
    //console.log('[loadTimeLine]', task);
    let code = task.code;
    function cb(resp) {
        if (! resp) {
            // console.log('clear ui: ', task.code);
            // clear ui
            if (timelines[code] && timelines[code].ui) {
                timelines[code].ui.remove();
            }
            timelines[code] = null;
            resolve();
            return;
        }
        let obj = timelines[code];
        if (! obj) {
            timelines[code] = obj = {model: null, ui: null, view: null};
        }
        obj.model = resp;
        // update ui
        task.updateUI(code);
        resolve();
    }

    chrome.runtime.sendMessage({cmd: 'GET_TIMELINE', data: code}, cb);
}

function extendWidth(obj, aw) {
    let w = obj.width();
    w += aw;
    obj.css('width', '' + w + 'px');
}

function getCodeInTd(tr) {
    let txt = tr.find('td:eq(0)').text().trim();
    let code = txt.substring(txt.length - 6)
    if (code && code.length == 6) {
        return code;
    }
    return '';
}

function initFinacePage() {
    extendWidth($('div.w-1200'), ADD_WIDTH);
    extendWidth($('div.content-main-box div.watch-content-left'), ADD_WIDTH);

    let table = $('table.watch-table');
    let trs = table.find('tr');
    trs.eq(0).append('<th style="width:' + ADD_WIDTH + 'px">分时</th>');
    pageInfo.tableColNum = trs.eq(0).find('th').length;

    let codes = [];
    for (let i = 1; i < trs.length; i++) {
        trs.eq(i).css('border-top', 'solid 1px #ccc');
        let code = getCodeInTd(trs.eq(i));
        if (code && code.length == 6) {
            codes.push(code);
            chrome.runtime.sendMessage({cmd: 'LOAD_TIMELINE', data: code});
        } else {
            console.log('Load Code Fail: ', trs[i]);
        }
    }

    function loadAllCodes(tk, resolve) {
        let table = $('table.watch-table');
        let trs = table.find('tr');
        for (let i = 1; i < trs.length; i++) {
            let code = getCodeInTd(trs.eq(i));
            //console.log(i, code);
            if (code.length != 6) {
                continue;
            }
            let task = new Task(i, 300, loadTimeLine);
            task.code = code;
            task.updateUI = updateFinacePageUI;
            thread.addTask(task);
        }
        let task = new Task('LAC', 5000, loadAllCodes);
        thread.addTask(task);
        resolve();
    }

    let task = new Task('LAC', 5000, loadAllCodes);
    thread.addTask(task);
    thread.start();
}


let url = window.location.href;
if (url == 'https://www.cls.cn/finance') {
    setTimeout(() => {
        initFinacePage();
    }, 3000);
} else if (url.indexOf('https://www.cls.cn/plate?code=') >= 0) {
    setTimeout(() => {
        initFinacePage();
    }, 3000);
}
