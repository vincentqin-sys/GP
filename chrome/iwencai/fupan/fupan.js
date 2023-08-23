var klineUIMgr = new KLineUIManager();

//--------------------------K 线-------------------------------------------------
function buildCodeUI(code, limitConfig, parent) {
    const ROW_HEIGHT = 120;
    let p = $('<p style="width: 100%; border-bottom: solid 1px #ccc; padding-left: 20px;" />');
    let infoDiv = $('<div style="float: left; width: 100px; height: ' + ROW_HEIGHT + 'px; border-right: solid 1px #ccc; " /> ');
    let selInfoDiv = $('<div style="float: left; width: 150px; height: ' + ROW_HEIGHT + 'px; border-right: solid 1px #ccc; " /> ');
   
    let klineUI = new KLineUI(540, ROW_HEIGHT);
    klineUIMgr.add(klineUI);
    p.append(infoDiv);
    p.append(selInfoDiv);
    p.append(klineUI.ui);
    parent.append(p);

    klineUI.addListener('LoadDataEnd', function(event) {
        let info = klineUI.view.baseInfo;
        infoDiv.append(info.code + '<br/>' + info.name);
    });

    klineUI.addListener('VirtualMouseMove', function(event) {
        let dataArr = klineUI.view.dataArr;
        if (event.pos < 0 || !dataArr  ||  event.pos >= dataArr.length) {
            return;
        }
        let info = dataArr[event.pos];
        let txt = '' ;
        txt += '' + info.date + ' <br/><br/>';
        txt += '涨幅：';
        if (event.pos > 0) {
            let preInfo = dataArr[event.pos - 1];
            let zf = '' + ((info.close - preInfo.close) / preInfo.close * 100);
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
        selInfoDiv.html(txt);
    });

    klineUI.loadData(code, limitConfig);
}


function buildUI(codeArr, limitConfig) {
    let cntDiv = $('<div style="position: absolute; left: 0; top :0; width: 100%; height: 100%; overflow: auto; z-index: 9999999; background-color: #fff;" />');
    $(document.body).append(cntDiv);

    for (let i in codeArr) {
        buildCodeUI(codeArr[i], limitConfig, cntDiv);
    }
}

//--------------------------------------------------------------------------------------
政券板块 = ['881157', '601099', '601136', '601059', '600906'];
// buildUI(政券板块, {startDate : 20230713, endDate: 202301031});

数据要素板块 = ['886041', '605398', '301159', '301169',  '601858', '300807', '301299', '003007', '002235', '002777', '600602', '600633', '002095'];
buildUI(数据要素板块, {startDate : 20230713, endDate: 202301031} );