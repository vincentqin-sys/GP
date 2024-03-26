let timelines = {}; // key : {model, ui }
const ADD_WIDTH = 300;

function updateFinacePageUI(code) {
    let item = timelines[code];
    if (! item) {
        return;
    }
    
    if (item.ui) {
        item.ui.remove();
    } else {
        item.view = new TimeLineView(ADD_WIDTH, 50);
        item.ui = $(item.canvas);
    }
    item.view.setData(item.model);
    item.view.draw();

    let table = $('.watch-table-box > table.watch-table');
    let trs = table.find('tr');
    for (let i = 1; i < trs.length; i++) {
        let tr = trs.eq(i);
        let rowCode = tr.find('td:eq(0) > a > div:eq(1)').text();
        rowCode = rowCode.trim().substring(2);
        if (rowCode == code) {
            let tds = tr.find('td');
            let td = null;
            if (tds.length == 5) {
                td = $('<td> </td>');
                tr.append(td);
            } else {
                td = tr.find('td:last');
                td.empty();
            }
            td.append(item.ui);
            console.log('find ', td, item.ui);
            break;
        }
    }
}

function loadTimeLine(code, updateUI) {
    chrome.runtime.sendMessage({cmd: 'GET_TIMELINE', data: code}, null, function(resp) {
        if (! resp) {
            // clear ui
            if (timelines[code] && timelines[code].ui) {
                timelines[code].ui.remove();
            }
            timelines[code] = null;
            return;
        }
        let obj = timelines[code];
        if (! obj) {
            timelines[code] = obj = {model: null, ui: null, view: null};
        }
        // check is same
        if (obj.model && (resp.dotsCount == obj.model.dotsCount || resp['dataArr'])) {
            // console.log('same value for ', code, resp);
            return;
        }
        resp.pre = parseFloat(resp.pre);
        resp.dataArr = [];
        let iv = resp.data.split(/;|,/g);
        const FEN_SHI_DATA_ITEM_SIZE = 5;
        // 时间，价格，成交额（元），分时均价，成交量（手）
        for (let i = 0; i < iv.length; i += FEN_SHI_DATA_ITEM_SIZE) {
            let item = {};
            item['time'] = parseInt(iv[i]);
            item['price'] = parseFloat(iv[i + 1]);
            item['money'] = parseInt(iv[i + 2]);
            item['avgPrice'] = parseFloat(iv[i + 3]);
            item['vol'] = parseInt(iv[i + 4]);
            resp.dataArr.push(item);
        }
        obj.model = resp; // changed
        // update ui
        updateUI(code);
    });
}

function extendWidth(obj, aw) {
    let w = obj.width();
    w += aw;
    obj.css('width', '' + w + 'px');
}

function initFinacePage() {
    extendWidth($('div.w-1200'), ADD_WIDTH);
    extendWidth($('div.content-main-box div.watch-content-left'), ADD_WIDTH);

    let table = $('.watch-table-box > table.watch-table');
    let trs = table.find('tr');
    trs.eq(0).append('<th style="width:' + ADD_WIDTH + 'px">分时<th>');
    let codes = [];
    for (let i = 1; i < trs.length; i++) {
        let code = trs.eq(i).find('td:eq(0) > a > div:eq(1)').text();
        code = code.trim().substring(2);
        if (code && code.length == 6) {
            codes.push(code);
            chrome.runtime.sendMessage({cmd: 'LOAD_TIMELINE', data: code})
        } else {
            console.log('Load Code Fail: ', trs[i]);
        }
    }

    setInterval(function() {
        for (let i = 0; i < codes.length; i++) {
            loadTimeLine(codes[i], updateFinacePageUI);
        }
    }, 5000);
}

let url = window.location.href;
if (url == 'https://www.cls.cn/finance') {
    setTimeout(() => {
        initFinacePage();
    }, 2000);
}
