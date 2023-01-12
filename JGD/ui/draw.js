var canvas, ctx; //canvas DOM    canvas上下文
// 图表属性
var canvasWidth, canvasHeight; //canvas中部的宽/高  canvas内边距/文字边距
var originX, originY; //坐标轴原点
// K线图属性
var K_MARGIN = 2, K_WIDTH = 5; // 每个k线图间间距  宽度
var kBarsNum, kMaxValue, kMinValue; //  数量  所有k线图的最大值/最小值
var maxRate = 0; // 最大换手率
var TOTAL_Y_LABEL_NUM = 10; //y轴上的标识数量

// 创建canvas并获得canvas上下文
canvas = document.getElementById("canvas");
ctx = canvas.getContext("2d");

const CANVAS_LR_MARGIN = 70; // 左右间距
const CANVAS_UD_MARGIN = 30; // 上下间距
const ZB_HEIGHT = 150; // 指标区域高度
const ZB_TOP_PADDING = 10; // 指标区域顶部间隙

// 初始化图表
function initGraph() {
    canvasHeight = canvas.height - CANVAS_UD_MARGIN * 2 - ZB_HEIGHT;
    canvasWidth = canvas.width - CANVAS_LR_MARGIN * 2;
    originX = CANVAS_LR_MARGIN;
    originY = canvasHeight + CANVAS_UD_MARGIN;
    //算最大值，最小值
    kMaxValue = 0;
    kMinValue = 9999999;
    for (var i = 0; i < dataArr.length; i++) {
        var barVal = dataArr[i].high;
        if (barVal > kMaxValue) {
            kMaxValue = barVal;
        }
        var barVal2 = dataArr[i].low;
        if (barVal2 < kMinValue) {
            kMinValue = barVal2;
        }
    }
    // kMaxValue += parseInt((kMaxValue - kMinValue) * 0.1); //上面预留10%的空间
    kMinValue -= parseInt(kMinValue * 0.1); //下面预留10%的空间

    kBarsNum = dataArr.length;
    maxRate = 0;
    for (let i = 0; i < kBarsNum; i++) {
        if (maxRate < dataArr[i].rate)
            maxRate = dataArr[i].rate;
    }
    if (maxRate < 10) {
        maxRate = 10;
    }
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

// 绘制图表轴、标签和标记
function drawLineLabelMarkers() {
    ctx.font = "24px Arial";
    ctx.lineWidth = 2;
    ctx.fillStyle = "#000";
    ctx.strokeStyle = "#000";
    // y轴
    drawLine(originX, originY, originX, 0);
    // x轴
    drawLine(originX, originY, originX + canvasWidth, originY);
    // 绘制标记
    drawMarkers();
}

// 画线的方法
function drawLine(x, y, X, Y, color) {
    color = color || 'white';
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x + 0.5, y + 0.5);
    ctx.lineTo(X + 0.5, Y + 0.5);
    ctx.stroke();
    ctx.closePath();
}

// int price * 100 to a float string
function priceToString(price) {
    price = String(price);
    s = price.substring(0, price.length - 2);
    s += '.';
    s += price.substring(price.length - 2, price.length);
    return s;
}

// 绘制标记
function drawMarkers() {
    ctx.strokeStyle = "#E0E0E0";
    // 绘制 y
    var oneVal = (kMaxValue - kMinValue) / TOTAL_Y_LABEL_NUM;
    ctx.textAlign = "right";
    for (var i = 1; i <= TOTAL_Y_LABEL_NUM; i++) {
        var markerVal = parseInt(i * oneVal + kMinValue);
        var xMarker = originX - 10;
        var yMarker = parseInt(originY - canvasHeight * (markerVal - kMinValue) / (kMaxValue - kMinValue));
        ctx.fillStyle = "white";
        ctx.font = "12px Verdana";
        ctx.fillText(priceToString(markerVal), xMarker - 15, yMarker); // 文字
        drawLine(originX + 1, yMarker - 3, originX - 9, yMarker - 3);
    }

    // 绘制 x
    ctx.textAlign = "center";
    const X_LABEL_NUM = 10;
    var oneTB = kBarsNum / X_LABEL_NUM;
    for (var i = 0; i < X_LABEL_NUM; i++) {
        let idx = parseInt(i * oneTB);
        if (idx >= kBarsNum) {
            idx = kBarsNum - 1;
        }
        if (idx < 0) {
            break;
        }
        var markerVal = dataArr[idx].date;
        var xMarker = parseInt(originX + (K_MARGIN + K_WIDTH) * idx + K_WIDTH / 2 + K_MARGIN);
        var yMarker = originY + 20;
        ctx.fillStyle = "white";
        ctx.font = "12px Verdana";
        ctx.textAlign = 'center';
        ctx.fillText(markerVal, xMarker, yMarker); // 文字
        drawLine(xMarker, originY, xMarker, originY - 10);
        
        
    }

    // draw buy sel day
    let jgd = getCurJGD();
    for (let i = 0; i < kBarsNum - 1 && jgd; ++i) {
        let mx = originX + i * (K_WIDTH + K_MARGIN) + K_MARGIN + K_WIDTH / 2;
        if (dataArr[i].date <= parseInt(jgd.buyDay) && dataArr[i + 1].date > parseInt(jgd.buyDay)) {
            drawLine(mx, originY, mx, originY - 40, 'rgb(255, 0, 0)');
        }
        if (dataArr[i].date <= parseInt(jgd.sellDay) && dataArr[i + 1].date > parseInt(jgd.sellDay)) {
            drawLine(mx, originY, mx, originY - 40, 'rgb(0, 255, 0)');
        }
    }

    // 绘制标题 y
    ctx.save();
    ctx.rotate(-Math.PI / 2);
    //ctx.fillText("指 数", -canvas.height / 2, cSpace - 20);
    ctx.restore();
    // 绘制标题 x
    //ctx.fillText("日 期", originX + cWidth / 2, originY + cSpace - 20);
}

function getZDTag(posIdx) {
    let cur = dataArr[posIdx];
    if (posIdx > 0 && getPeriod() == 'day') {
        let ZRDP = dataArr[posIdx - 1].close;
        let zf = (cur.close - ZRDP) / ZRDP * 100;
        let is20P = getCode().substring(0, 3) == '688' || getCode().substring(0, 2) == '30';
        if (cur.date < 20200824) {
            is20P = false;
        }
        let ZT = is20P ? 20 : 10;
        let isZT = (parseInt(ZRDP * (100 + ZT) / 100) <= parseInt(cur.close));
        if (isZT) {
            return 'ZT';
        }
        let isZTZB = (parseInt(ZRDP * (100 + ZT) / 100) <= parseInt(cur.high)) && (cur.high != cur.close);
        if (isZTZB) {
            return 'ZTZB';
        }
        let isDT = (parseInt(ZRDP * (100 - ZT) / 100) >= parseInt(cur.close));
        if (isDT) {
            return 'DT';
        }
    }
    if (cur.open <= cur.close) {
        return 'Z';
    } else {
        return 'D';
    }
}

function getKColor(tag) {
    if (tag == 'ZT' || tag == 'ZTZB')
        return "rgb(0, 0, 255)";
    if (tag == 'DT')
        return "rgb(255, 255, 0)";
    if (tag == 'Z')
        return "rgb(253,50,50)";
    // tag is 'D'
    return "rgb(84,252,252)"
}

function priceToPoint(pos, price) {
    let x = originX + pos * (K_WIDTH + K_MARGIN) + K_MARGIN + K_WIDTH / 2;
    let y = originY - parseInt(canvasHeight * (price - kMinValue) / (kMaxValue - kMinValue));
    return { 'x': x, 'y': y };
}

// attr = 'bbi' 'ma5'
function drawBezier(attr, color, lineWidth) {
    if (kBarsNum == 0) {
        return;
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.beginPath();
    ctx.fillStyle = "#ffffff";
    p = priceToPoint(0, dataArr[0][attr]);
    ctx.moveTo(p.x, p.y);
    let pts = [];
    pts.push(p);
    for (let i = 1; i < kBarsNum; i++) {
        let pt = priceToPoint(i, dataArr[i][attr]);
        let last = pts[i - 1];
        pts.push(pt);
        let paX = 0, paY, pbX, pbY = 0;
        paX = (pt.x - last.x) * 0.25 + last.x;
        paY = (pt.y - last.y) * 0.25 + last.y;
        pbX = (pt.x - last.x) * 0.75 + last.x;
        pbY = (pt.y - last.y) * 0.75 + last.y;
        ctx.bezierCurveTo(paX, paY, paX, pbY, pt.x, pt.y);
    }
    ctx.stroke();
}

//绘制k形图
function drawKBar(mouseMove) {
    drawBezier('ma5', "rgb(255, 255, 0)", 1);
    drawBezier('bbi', "rgb(238, 0, 238)", 2);

    for (var i = 0; i < kBarsNum; i++) {
        var data = dataArr[i];
        var tag = getZDTag(i);
        var color = getKColor(tag);
        var maxVal = 0;
        var disY = 0;
        //开盘0 收盘1 最低2 最高3   跌30C7C9  涨D7797F
        if (data.close > data.open) { //涨
            disY = data.close - data.open;
            maxVal = data.close;
        } else {
            disY = data.open - data.close;
            maxVal = data.open;
        }
        var showH = disY / (kMaxValue - kMinValue) * canvasHeight;
        showH = showH > 2 ? showH : 2;

        var beginY = parseInt(canvasHeight * (maxVal - kMinValue) / (kMaxValue - kMinValue));
        var y = originY - beginY;
        var x = originX + ((K_WIDTH + K_MARGIN) * i + K_MARGIN);
        
        //最高最低的线
        let y2 = originY - parseInt(canvasHeight * (data.high - kMinValue) / (kMaxValue - kMinValue));
        let y3 = originY - parseInt(canvasHeight * (data.low - kMinValue) / (kMaxValue - kMinValue));
        let x2 =  x + K_WIDTH / 2;
        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.moveTo(x2 + 0.5, y2);
        ctx.lineTo(x2 + 0.5, y3);
        ctx.stroke();
        ctx.closePath();

        drawRect(x, y, K_WIDTH, showH, mouseMove, color, tag); //开盘收盘  高度减一避免盖住x轴
    }
}

//绘制方块
function drawRect(x, y, w, h, mouseMove, color, tag) {
    ctx.beginPath();
    ctx.rect(parseInt(x) + 0.5, parseInt(y) + 0.5, parseInt(w), parseInt(h));
    if (tag == 'Z' || tag == 'ZT') {
        ctx.fillStyle = 'rgb(0, 0, 0)';
        ctx.fill();
        ctx.lineWidth = 1;
        ctx.strokeStyle = color;
        ctx.stroke();
    } else {
        ctx.fillStyle = color;
        ctx.lineWidth = 0;
        ctx.fill();
        ctx.stroke();
    }
    
    ctx.closePath();
}

// 绘换手率指标
function drawZBRate() {
    let zbX = originX;
    let zbY = originY + CANVAS_UD_MARGIN + ZB_HEIGHT;

    ctx.lineWidth = 1;
    for (var i = 0; i < kBarsNum; i++) {
        var data = dataArr[i];
        ctx.beginPath();
        color = data.close >= data.open ? "rgb(253,50,50)" : "rgb(84,252,252)";
        if (i > 0 && data.vol >= dataArr[i - 1].vol * 2) {
            // 倍量
            color = 'blue';
        }
        ctx.fillStyle = color;
        ctx.strokeStyle = color;
        zbX += K_MARGIN;
        let ht = (ZB_HEIGHT - ZB_TOP_PADDING) * data.rate / maxRate;
        let zy = (ZB_HEIGHT - ZB_TOP_PADDING) - ht;
        ctx.rect(zbX + 0.5, zbY + 0.5, K_WIDTH, -ht);
        if (data.close >= data.open) {
            ctx.stroke();
        } else {
            ctx.lineWidth = 0;
            ctx.fill();
            ctx.stroke();
        }
        zbX += K_WIDTH;
        ctx.closePath();
    }
    // 5% 10% 20%线
    ctx.beginPath();
    ctx.lineWidth = 2;
    ctx.strokeStyle = 'blue';
    ctx.moveTo(CANVAS_LR_MARGIN + 0.5, zbY - parseInt((ZB_HEIGHT - ZB_TOP_PADDING) * 5 / maxRate) + 0.5);
    ctx.lineTo(CANVAS_LR_MARGIN + canvasWidth + 0.5, zbY - parseInt((ZB_HEIGHT - ZB_TOP_PADDING) * 5 / maxRate) + 0.5);
    ctx.stroke();
    ctx.closePath();

    ctx.beginPath();
    ctx.lineWidth = 2;
    ctx.strokeStyle = 'rgb(238, 0, 238)';
    ctx.moveTo(CANVAS_LR_MARGIN + 0.5, zbY - parseInt((ZB_HEIGHT - ZB_TOP_PADDING) * 10 / maxRate) + 0.5);
    ctx.lineTo(CANVAS_LR_MARGIN + canvasWidth + 0.5, zbY - parseInt((ZB_HEIGHT - ZB_TOP_PADDING) * 10 / maxRate) + 0.5);
    ctx.stroke();
    ctx.closePath();

    if (maxRate >= 20) {
        ctx.beginPath();
        ctx.lineWidth = 2;
        ctx.strokeStyle = 'rgb(255, 255, 0)';
        ctx.moveTo(CANVAS_LR_MARGIN + 0.5, zbY - parseInt((ZB_HEIGHT - ZB_TOP_PADDING) * 20 / maxRate) + 0.5);
        ctx.lineTo(CANVAS_LR_MARGIN + canvasWidth + 0.5, zbY - parseInt((ZB_HEIGHT - ZB_TOP_PADDING) * 20 / maxRate) + 0.5);
        ctx.stroke();
        ctx.closePath();
    }

    if (maxRate >= 30) {
        ctx.beginPath();
        ctx.lineWidth = 1;
        ctx.strokeStyle = 'rgb(255, 255, 255)';
        let zy = zbY - parseInt((ZB_HEIGHT - ZB_TOP_PADDING) * maxRate / maxRate) + 0.5;
        ctx.moveTo(CANVAS_LR_MARGIN + 0.5, zy);
        ctx.lineTo(CANVAS_LR_MARGIN + canvasWidth + 0.5, zy);
        ctx.stroke();
        ctx.textAlign = "left";
        ctx.fillText("" + maxRate + "%", CANVAS_LR_MARGIN + canvasWidth + 10.5, zy + 3);
        ctx.closePath();
    }
}

canvas.addEventListener("mousemove", function (e) {
    var event = e || window.event;
    // console.log(event.pageX, event.pageY, event.offsetX, event.offsetY);
    var x = event.offsetX - CANVAS_LR_MARGIN;
    var y = event.offsetY - CANVAS_UD_MARGIN;
    if (y <= 0 || x <= 0 || x >= canvasWidth) {
        return;
    }
    var maxX = kBarsNum * (K_WIDTH + K_MARGIN);
    if (x >= maxX) {
        return;
    }
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawLineLabelMarkers();
    drawKBar(true);
    drawZBRate();

    // 十字线
    var posIdx = parseInt(x / (K_WIDTH + K_MARGIN));
    var xx = posIdx * (K_WIDTH + K_MARGIN);
    xx = parseInt(xx + K_MARGIN + K_WIDTH / 2) + CANVAS_LR_MARGIN;
    y += CANVAS_UD_MARGIN;
    drawLine(xx, CANVAS_UD_MARGIN, xx, originY + CANVAS_LR_MARGIN + ZB_HEIGHT);
    drawLine(0, y, CANVAS_LR_MARGIN + canvasWidth, y);

    x = event.offsetX;
    y = event.offsetY;

    // 左侧价格线提示框
    var vx = 0;
    var vy = y - 15;
    ctx.beginPath();
    ctx.moveTo(vx, vy);
    ctx.lineTo(vx + CANVAS_LR_MARGIN, vy);
    ctx.lineTo(vx + CANVAS_LR_MARGIN, vy + 30);
    ctx.lineTo(vx, vy + 30);
    ctx.lineTo(vx, vy); //绘制最后一笔使图像闭合
    ctx.lineWidth = 1;
    ctx.fillStyle = "rgb(104,113,130)";
    ctx.fill();
    ctx.stroke();

    y -= CANVAS_UD_MARGIN;
    if (y <= canvasHeight) {
        var ch = parseInt((kMaxValue - kMinValue) * (canvasHeight - y) / canvasHeight + kMinValue);
        ch = priceToString(ch);
        ctx.fillStyle = "white";
        ctx.textAlign = 'center';
        ctx.fillText(ch, CANVAS_LR_MARGIN / 2, vy + 20); // 价格文字
    } else if (y > canvasHeight + CANVAS_UD_MARGIN) {
        // 进入指标区域
        let zy = y - CANVAS_UD_MARGIN - canvasHeight;
        var ch = parseInt(maxRate * (ZB_HEIGHT - zy) / (ZB_HEIGHT - ZB_TOP_PADDING));
        ch = String(ch) + '%';
        ctx.fillStyle = "white";
        ctx.textAlign = 'center';
        ctx.fillText(ch, CANVAS_LR_MARGIN / 2, vy + 20); // 价格文字
    }

    // 日K线提示框
    const K_TIP_WIDTH = 120;
    const K_TIP_HEIGHT = 230;
    vx = canvasWidth + CANVAS_LR_MARGIN * 2 - K_TIP_WIDTH;
    vy = 0;
    // ctx.beginPath();
    ctx.moveTo(vx, vy);
    ctx.lineTo(vx + K_TIP_WIDTH, vy);
    ctx.lineTo(vx + K_TIP_WIDTH, vy + K_TIP_HEIGHT);
    ctx.lineTo(vx, vy + K_TIP_HEIGHT);
    ctx.lineTo(vx, vy); //绘制最后一笔使图像闭合
    ctx.lineWidth = 2;
    ctx.fillStyle = "rgba(104,113,130,0.5)";
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = "white";
    ctx.textAlign = "left";
    ctx.fillText(dataArr[posIdx].date, vx + 10, vy + 20); // 文字
    ctx.fillText("开盘价：" + priceToString(dataArr[posIdx].open), vx + 10, vy + 40); // 文字
    ctx.fillText("收盘价：" + priceToString(dataArr[posIdx].close), vx + 10, vy + 60); // 文字
    ctx.fillText("最高价：" + priceToString(dataArr[posIdx].high), vx + 10, vy + 80); // 文字
    ctx.fillText("最低价：" + priceToString(dataArr[posIdx].low), vx + 10, vy + 100); // 文字
    let amount = dataArr[posIdx].amount / 10000; // 亿
    amount = String(amount.toFixed(2)) + '亿';
    ctx.fillText("成交额：" + amount, vx + 10, vy + 130); // 文字
    ctx.fillText("换手率：" + String(dataArr[posIdx].rate) + '%', vx + 10, vy + 150); // 文字
    if (posIdx > 0) {
        let zf = (dataArr[posIdx].close - dataArr[posIdx - 1].close) / dataArr[posIdx - 1].close * 100;
        zf = zf.toFixed(2);
        ctx.fillText("涨  幅：" + zf + '%', vx + 10, vy + 170); // 文字
        let tb = dataArr[posIdx].vol / dataArr[posIdx - 1].vol;
        tb = tb.toFixed(2);
        ctx.fillText("昨同比：" + tb, vx + 10, vy + 190); // 文字
    }

    // 日期提示
    /*
    vx = originX + posIdx * (K_WIDTH + K_MARGIN) + K_WIDTH / 2 + K_MARGIN;
    vy = originY + 20;
    ctx.rect(vx - 50, vy - 15, 100, 20);
    ctx.fillStyle = "rgb(104,113,130)";
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "white";
    ctx.textAlign = "center";
    ctx.fillText(dataArr[posIdx].date, vx, vy); // 文字
    */
});


function resetGraph() {
    initGraph();
    drawLineLabelMarkers();
    drawKBar();
    drawZBRate();
}

resetGraph();