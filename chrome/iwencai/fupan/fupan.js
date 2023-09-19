var klineUIMgr = new KLineUIManager();
var timeLineUIMgr = new TimeLineUIManager();

//--------------------------K 线-------------------------------------------------
function buildCodeUI(code, limitConfig, parent) {
    if (! code || !code.trim()) {
        return;
    }
    const ROW_HEIGHT = 120;
    let p = $('<p style="width: 100%; border-bottom: solid 1px #ccc; padding-left: 20px;" />');
    if (code.trim().toLowerCase() == 'empty') {
        parent.append(p);
        p.css({height: '4px', backgroundColor : '#abc'});
        return;
    }

    let infoDiv = $('<div style="float: left; width: 100px; height: ' + ROW_HEIGHT + 'px; border-right: solid 1px #ccc; " /> ');
    let selInfoDiv = $('<div style="float: left; width: 150px; height: ' + ROW_HEIGHT + 'px; border-right: solid 1px #ccc; " /> ');
   
    let klineUI = new KLineUI(540, ROW_HEIGHT);
    klineUIMgr.add(klineUI);
    var timelineUI = new TimeLineUI(300, ROW_HEIGHT);
    timeLineUIMgr.add(timelineUI);

    klineUI.ui.css('float', 'left');
    p.append(infoDiv);
    p.append(selInfoDiv);
    p.append(klineUI.ui);
    p.append(timelineUI.ui);
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
    timelineUI.loadData(code);
}


function buildUI(codeArr, limitConfig) {
    let cntDiv = $('<div style="position: absolute; left: 0; top :0; width: calc(100% - 16px); height: 100%; overflow: auto; z-index: 9999999; background-color: #fff; border: solid 8px #aaa; padding-bottom: 10px;" />');
    $(document.body).append(cntDiv);

    codeArr.unshift('1A0001');
    codeArr.push('Empty');
    for (let i in codeArr) {
        let cur = codeArr[i];
        cur = cur.substring(0, 6);
        buildCodeUI(cur, limitConfig, cntDiv);
    }
}

//--------------------------------------------------------------------------------------
政券 = ['881157', '885456', 'Empty','601099', '601136', '601059', '600906', '301315', '300380', '000712', '600095', '002670', '600621'];
// buildUI(政券, {startDate : 20230713, endDate: 202301031});

数据要素 = ['886041', 'Empty', '603000', '605398', '301159', '301169',  '601858', '300807', '301299', '003007', '002235', '002777', '600602', '600633', '002095'];
// buildUI(数据要素, {startDate : 20230713, endDate: 202301031} );

医药商业 = ['881143', 'Empty','603716', '301281', '600272', '603122', '301509', '301408', '000705', '300937', '600829', '301370'];
// buildUI(医药商业, {startDate : 20230713, endDate: 202301031} );

环保 = ['881181', '000826', '605069', 'Empty', '301203', '002310', '688671', '605081', '603291', '600796', '600292', '301372', '301288', '301148', '301049', '300958', '300172' , '002887', '002778'];
// buildUI(环保, {startDate : 20230713, endDate: 202301031} );

机器人 = ['', '600336', '301137', '002833', '603728', '603662', '002553', '002031', '002896', '300503', '002527', '300885', '', '', '', '', '', '', ];
减速器 = ['', '603767', '000678', '002833', '002031', '002553', '002472', '300904', '002896', '300503', '002527', '301255', '', ];
// buildUI(机器人, {startDate : 20230713, endDate: 202301031} );

零售 = ['881158', '605188 国光连锁', '600280 中央商场', '002336 人人乐', '000715 中兴商业', '601086 国芳集团'];
// buildUI(零售, {startDate : 20230801, endDate: 202301031} );


// 2023.08.30日启动
华为概念 = [ '885806', 'Empty', '002855 捷荣技术', '000536 华映科技', '300045 华力创通', '002261 拓维信息', '000158 常山北明', '300537 广信材料', '002642 荣联科技', '605588 冠石科技',  '002767 先锋电子',
        '300936 中英科技', '300814 中富电路', '300097 智云股份', '300538 同益股份', '000801 四川九洲',  '301348 蓝箭电子', '601127 赛力斯', '300231 银信科技', 
        '688651 盛邦安全', '002222 福晶科技', '000851 高鸿股份',  '002654 万润科技', '002341 新纶新材', '300807 天迈科技' ];
// buildUI(华为概念, {startDate : 20230801, endDate: 202301031} );

// 2023.09.06日启动
光刻胶 = ['885864', 'Empty', '600895 张江高科', '300293 蓝英装备', '300537 广信材料', '603005 晶方科技', '300576 容大感光', '301421 波长光电', '', '', ];
 // buildUI(光刻胶, {startDate : 20230801, endDate: 202301031} );

// 2023.09.18 日启动（涨停16， 大爆发）
// 会不会实际上是 “ 华为汽车 ” 概念 ？ （9个涨停）
汽车零部件 = ['881126', 'Empty', '', '', '', '', '', '', '', '', '', '', ''];
buildUI(汽车零部件, {startDate : 20230901, endDate: 202301031} );

