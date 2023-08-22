let klineObjArr = [];


console.log('in fupan.js ', new Date());

let cntDiv = $('<div style="position: absolute; left: 0; top :0; width: 100%; height: 100%; overflow: auto; z-index: 9999999; background-color: #fff;" />');
$(document.body).append(cntDiv);

function buildCodeUI(code, callback) {
    const ROW_HEIGHT = 200;
    let p = $('<p style="width: 100%; border-bottom: solid 1px #ccc; padding-left: 20px;" />');
    let infoDiv = $('<div style="float: left; width: 100px; height: ' + ROW_HEIGHT + 'px; border-right: solid 1px #ccc; " /> ');
    let selInfoDiv = $('<div style="float: left; width: 150px; height: ' + ROW_HEIGHT + 'px; border-right: solid 1px #ccc; " /> ');
    let canvas = $('<canvas style="width: 540px; height: ' + ROW_HEIGHT + 'px; border-right: solid 1px #ccc;" />');
    let obj = new KLine(canvas.get(0));
    obj.selInfoDiv = selInfoDiv;
    // canvas.data('klineObj', obj);
    canvas.get(0).addEventListener('mousemove', function(e) {
        kline_mouseMove(e, obj);
    });

    p.append(infoDiv);
    p.append(selInfoDiv);
    p.append(canvas);

    loadKLineData(code, 30, function(info, klineInfo) {
        obj.setData(info, klineInfo);
        obj.draw();
        infoDiv.append(info.code + '<br/>' + info.name);
        callback(obj);
    });
    return p;
}

function kline_mouseMove(e, klineObj) {
    var event = e || window.event;
    var x = event.offsetX;
    var y = event.offsetY;
    for (let i in klineObjArr) {
        klineObjArr[i].draw();
        klineObjArr[i].drawMouse(x, y);

        let posIdx = klineObjArr[i].getPosIdx(x);
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

// 最多取maxDayNum天的数据
function loadKLineData(code, maxDayNum, callback) {
    maxDayNum = maxDayNum || 30;
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
            if (klineDataArr.length > maxDayNum) {
                klineDataArr = klineDataArr.slice(- maxDayNum);
            }
            for (let i = 0; i < klineDataArr.length; i++) {
                let kv = klineDataArr[i].split(',');
                let keys = ['date', 'open', 'high', 'low', 'close', 'vol', 'money', 'rate']; // vol: 单位股, money:单位元
                let item = {};
                for (let j = 0; j < keys.length; ++j) {
                    item[keys[j]] = parseFloat(kv[j]);
                }
                klineInfo.push(item);
            }
            console.log(info, klineInfo);
            if (callback) {
                callback(info, klineInfo);
            }
        }
    });
}

function loadFinishi(klineObjArr) {
    let gp = klineObjArr[klineObjArr.length - 1]; // 最后一个股票代码
    let lastDate = gp.dataArr[gp.dataArr.length - 1].date;
    let firstDate = gp.dataArr[0].date;
    for (let i = 0; i < klineObjArr.length - 1; i++) {
        let obj = klineObjArr[i];
        let curLastDate = obj.dataArr[obj.dataArr.length - 1].date;
        let curFirstDate = obj.dataArr[0].date;
        if (curLastDate < lastDate) {
            obj.dataArr.push(null); // 加一天
        }
        if (curFirstDate < firstDate) {
            obj.dataArr.splice(0, 1); // 删除第一天
        }
        while (obj.dataArr.length < gp.dataArr.length) {
            obj.dataArr.unshift(null);
        }
        obj.draw();
    }
}

function buildUI(codeArr) {
    let num = 0;
    for (let i in codeArr) {
        let p = buildCodeUI(codeArr[i], function(klineObj) {
            klineObjArr.push(klineObj);
            ++num;
            if (num == codeArr.length) {
                loadFinishi(klineObjArr);
            }
        });
        cntDiv.append(p);
    }
}

// 最后一个必须是股票代码
buildUI(['881157', '601099', '601136']);