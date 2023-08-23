let klineObjArr = [];


console.log('in fupan.js ', new Date());

let cntDiv = $('<div style="position: absolute; left: 0; top :0; width: 100%; height: 100%; overflow: auto; z-index: 9999999; background-color: #fff;" />');
$(document.body).append(cntDiv);

//--------------------------K 线-------------------------------------------------
function buildCodeUI(code, limitConfig, callback) {
    const ROW_HEIGHT = 120;
    let p = $('<p style="width: 100%; border-bottom: solid 1px #ccc; padding-left: 20px;" />');
    let infoDiv = $('<div style="float: left; width: 100px; height: ' + ROW_HEIGHT + 'px; border-right: solid 1px #ccc; " /> ');
    let selInfoDiv = $('<div style="float: left; width: 150px; height: ' + ROW_HEIGHT + 'px; border-right: solid 1px #ccc; " /> ');
    let canvas = $('<canvas style="float-x: left; width: 540px; height: ' + ROW_HEIGHT + 'px; border-right: solid 1px #ccc;" />');
    let fenShiCanvas = $('<canvas style="width: 300px; height: ' + ROW_HEIGHT + 'px; border-right: solid 1px #ccc; " />');
    
    let obj = new KLine(canvas.get(0));
    obj.selInfoDiv = selInfoDiv;
    let timeLineObj = new TimeLine(fenShiCanvas.get(0));
    obj.timeLineObj = timeLineObj;
    // canvas.data('klineObj', obj);
    canvas.get(0).addEventListener('mousemove', function(e) {
        kline_mouseMove(e, obj);
    });
    canvas.get(0).addEventListener('click', function(e) {
        kline_click(e, obj);
    });
    canvas.get(0).addEventListener('contextmenu', function(e) {
        kline_rightclick(e, obj);
        console.log('contextmenu');
        e.preventDefault();
    });

    p.append(infoDiv);
    p.append(selInfoDiv);
    p.append(canvas);
    // p.append(fenShiCanvas);

    loadKLineData(code, limitConfig, function(info, klineInfo) {
        obj.setData(info, klineInfo);
        infoDiv.append(info.code + '<br/>' + info.name);
        loadTodayKLineData(code, limitConfig, obj, function(obj) {
            obj.draw();
            callback(obj);
        });
    });
    return p;
}

function kline_rightclick(e, klineObj) {
    var event = e || window.event;
    var x = event.offsetX;
    var y = event.offsetY;
    for (let i in klineObjArr) {
        let pos = klineObjArr[i].getPosIdx(x);
        klineObjArr[i].setHilightMouse(pos);
        klineObjArr[i].draw();
        /*
        let fsObj = klineObjArr[i].timeLineObj;
        loadTimeLineData(klineObjArr[i].baseInfo.code, function(rs) {
            fsObj.setData(rs);
            fsObj.draw();
        });
        */
    }
}

function kline_click(e, klineObj) {
    var event = e || window.event;
    var x = event.offsetX;
    var y = event.offsetY;
    for (let i in klineObjArr) {
        let pos = klineObjArr[i].getPosIdx(x);
        if (pos < 0)
            continue;
        klineObjArr[i].setSelectMouse(pos);
        klineObjArr[i].draw();
    }
}

function kline_mouseMove(e, klineObj) {
    var event = e || window.event;
    var x = event.offsetX;
    var y = event.offsetY;
    for (let i in klineObjArr) {
        let posIdx = klineObjArr[i].getPosIdx(x);
        klineObjArr[i].draw();
        klineObjArr[i].drawMouse(posIdx);
        if (posIdx < 0) {
            continue;
        }

        let info = klineObjArr[i].dataArr[posIdx];
        let txt = '' ;
        txt += '' + info.date + ' <br/><br/>';
        txt += '涨幅：';
        if (posIdx > 0) {
            let zf = '' + ((info.close - klineObjArr[i].dataArr[posIdx - 1].close) / klineObjArr[i].dataArr[posIdx - 1].close * 100);
            zf = zf.substring(0, zf.indexOf('.') + 2);
            txt += '' + zf + '% <br/>';
        } else {
            txt += '- <br/>';
        }
        let money = '' + (info.money / 100000000);
        money = money.substring(0, money.indexOf('.') + 2);
        txt += '成交额：' + money + '亿<br/>';
        let rate = '' + parseInt(info.rate);
        txt += '换手率：' + rate + '%';
        klineObjArr[i].selInfoDiv.html(txt);
    }
}

function limitKLineData(arr, startDate, endDate) {

}

// limitConfig = {startDate: xx,   endDate : xxx}
function loadKLineData(code, limitConfig, callback) {
    let url = getKLineUrl(code);
    $.ajax({
        url: url, type: 'GET', dataType : 'text',
        success: function(data) {
            let idx = data.indexOf('(');
            let eidx = data.indexOf(')');
            data = data.substring(idx + 1, eidx); 
            data = JSON.parse(data);
            // console.log(data);
            let info = {code : code, name : data.name, today : data.today};
            let klineInfo = [];
            let klineDataArr = data.data.split(/;/g);
            for (let i = 0; i < klineDataArr.length; i++) {
                let kv = klineDataArr[i].split(',');
                // first is date
                let date = parseFloat(kv[0]);
                if (date < limitConfig.startDate || date > limitConfig.endDate) {
                    continue;
                }
                let keys = ['date', 'open', 'high', 'low', 'close', 'vol', 'money', 'rate']; // vol: 单位股, money:单位元
                let item = {};
                for (let j = 0; j < keys.length; ++j) {
                    item[keys[j]] = parseFloat(kv[j]);
                }
                klineInfo.push(item);
            }
            // console.log(info, klineInfo);
            if (callback) {
                callback(info, klineInfo);
            }
        }
    });
}

// limitConfig = {startDate: xx,   endDate : xxx}
function loadTodayKLineData(code, limitConfig, klineObj, callback) {
    let url = getTodayKLineUrl(code);
    $.ajax({
        url: url, type: 'GET', dataType : 'text',
        success: function(data) {
            let idx = data.indexOf(':{');
            let eidx = data.indexOf('}}');
            data = data.substring(idx + 1, eidx + 1);
            data = JSON.parse(data);
            let keys = ['date', 'open', 'high', 'low', 'close', 'vol', 'money', 'rate'];
            let idxKeys = ['1', '7', '8', '9', '11', '13', '19', '1968584'];
            
            let item = {};
            for (let j = 0; j < keys.length; ++j) {
                item[keys[j]] = parseFloat(data[idxKeys[j]]);
            }
            if (item.date >= limitConfig.startDate && item.date <= limitConfig.endDate) {
                let last = klineObj.dataArr[klineObj.dataArr.length - 1];
                if (last.date == item.date) {
                    klineObj.dataArr.splice(klineObj.dataArr.length - 1, 1);
                }
                klineObj.dataArr.push(item);
            }
            console.log(klineObj);
            if (callback) {
                callback(klineObj);
            }
        }
    });
}

function loadFinish(klineObjArr) {
    
}

//-------------------------------分时线--------------------------------------------------
function loadTimeLineData(code, callback) {
    const FEN_SHI_DATA_ITEM_SIZE = 5;
    let url = getFenShiUrl(code);
    $.ajax({
        url: url, type: 'GET', dataType : 'text',
        success: function(data) {
            let idx = data.indexOf(':');
            let eidx = data.indexOf('}})');
            data = data.substring(idx + 1, eidx + 1);
            data = JSON.parse(data);
            let rs = {};
            rs.pre = data.pre; // 昨日收盘价
            rs.dataArr = [];
            let iv = data.data.split(/;|,/g);
            // 时间，价格，成交额（元），分时均价，成交量（手）
            for (let i = 0; i < iv.length; i += FEN_SHI_DATA_ITEM_SIZE) {
                let item = {};
                item['time'] = parseInt(iv[i]);
                item['price'] = parseFloat(iv[i + 1]);
                item['money'] = parseInt(iv[i + 2]);
                item['avgPrice'] = parseFloat(iv[i + 3]);
                item['vol'] = parseInt(iv[i + 4]);
                rs.dataArr.push(item);
            }
            callback(rs);
        }
    });
}

//--------------------------------------------------------------------------------------
function buildUI(codeArr, limitConfig) {
    let num = 0;
    for (let i in codeArr) {
        let p = buildCodeUI(codeArr[i], limitConfig, function(klineObj) {
            klineObjArr.push(klineObj);
            ++num;
            if (num == codeArr.length) {
                loadFinish(klineObjArr);
            }
        });
        cntDiv.append(p);
    }
}

政券板块 = ['881157', '601099', '601136', '601059', '600906'];
// buildUI(政券板块, {startDate : 20230713, endDate: 202301031});

数据要素板块 = ['886041', '605398', '301159', '301169',  '601858', '300807', '301299', '003007', '002235', '002777', '600602', '600633', '002095'];
buildUI(数据要素板块, {startDate : 20230713, endDate: 202301031} );