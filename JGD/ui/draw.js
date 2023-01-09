// 声明所需变量 
var canvas, ctx; //canvas DOM    canvas上下文
// 图表属性
var canvasWidth, canvasHeight, canvasMargin, canvasSpace; //canvas中部的宽/高  canvas内边距/文字边距
var originX, originY; //坐标轴原点
// 图属性
var kMargin, kBarsNum, kWidth, kMaxValue, kMinValue; //每个k线图间间距  数量 宽度   所有k线图的最大值/最小值 
var TOTAL_Y_LABEL_NUM; //y轴上的标识数量
var showArr; //显示出来的数据部分（因为可以选择范围，所以需要这个数据）

//范围选择属性
var dragBarX, dragBarWidth; //范围选择条中的调节按钮的位置，宽度

// 运动相关变量
var ctr, numctr, speed; //运动的起步，共有多少步，运动速度（timer的时间）
//鼠标移动
var mousePosition = {}; //用户存放鼠标位置


goChart(document.getElementById("chart"), dataArr);
drawLineLabelMarkers(); // 绘制图表轴、标签和标记
drawBarAnimate(); // 绘制柱状图的动画
//绘制拖动轴
drawDragBar();

// 绘制图表轴、标签和标记
function drawLineLabelMarkers() {
    ctx.font = "24px Arial";
    ctx.lineWidth = 2;
    ctx.fillStyle = "#000";
    ctx.strokeStyle = "#000";
    // y轴
    drawLine(originX, originY, originX, canvasMargin);
    // x轴
    drawLine(originX, originY, originX + canvasWidth, originY);
    // 绘制标记
    drawMarkers();
}

function drawMoveLine(x, y, X, Y, color) {
    /*绘制二次贝塞尔曲线*/
    ctx.strokeStyle = "white";
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.quadraticCurveTo((X - x) / 4 + x, y, X, Y);
    ctx.strokeStyle = color;
    ctx.lineWidth = 0.5;
    ctx.stroke();
}

// 画线的方法
function drawLine(x, y, X, Y) {
    ctx.strokeStyle = "white";
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(X, Y);
    ctx.stroke();
    ctx.closePath();
}

function drawLineWithColor(x, y, X, Y, color) {
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(X, Y);
    ctx.stroke();
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.closePath();
}

function setTime(time) {
    time = time.substring(0, 11);
    return time;
}

// 绘制标记
function drawMarkers() {
    ctx.strokeStyle = "#E0E0E0";
    // 绘制 y
    var oneVal = (kMaxValue - kMinValue) / TOTAL_Y_LABEL_NUM;
    ctx.textAlign = "right";
    for (var i = 1; i <= TOTAL_Y_LABEL_NUM; i++) {
        var markerVal = parseInt(i * oneVal + kMinValue);;
        var xMarker = originX - 10;
        var yMarker = parseInt(originY - canvasHeight * (markerVal - kMinValue) / (kMaxValue - kMinValue));
        ctx.fillStyle = "white";
        ctx.font = "22px Verdana";
        ctx.fillText(markerVal, xMarker - 15, yMarker, canvasSpace); // 文字
        if (i > 0) {
            drawLine(originX + 1, yMarker - 3, originX - 9, yMarker - 3);
        }
    }

    // 绘制 x
    var textNb = 6;
    ctx.textAlign = "center";
    for (var i = 0; i < kBarsNum; i++) {
        if (kBarsNum > textNb && i % parseInt(kBarsNum / 10) != 0) {
            continue;
        }
        var markerVal = dataArr[i][0];
        var xMarker = parseInt(originX + canvasWidth * (i / kBarsNum) + kMargin + kWidth / 2);
        var yMarker = originY + 30;
        ctx.fillStyle = "white";
        ctx.font = "22px Verdana";
        ctx.fillText(markerVal, xMarker, yMarker, canvasSpace); // 文字
        if (i > 0) {
            drawLine(xMarker, originY, xMarker, originY - 10);
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

//绘制k形图
function drawBarAnimate(mouseMove) {
    point_MA5 = new Array();
    point_MA10 = new Array();
    point_MA20 = new Array();
    point_MA30 = new Array();
    var parsent = ctr / numctr;
    for (var i = 0; i < kBarsNum; i++) {
        var oneVal = parseInt(kMaxValue / TOTAL_Y_LABEL_NUM);
        var data = dataArr[i];
        var color = "#30C7C9";
        var barVal = data.open;
        var disY = 0;
        //开盘0 收盘1 最低2 最高3   跌30C7C9  涨D7797F
        if (data.close > data.open) { //涨
            color = "#D7797F";
            barVal = data.close;
            disY = data.close - data.open;
        } else {
            disY = data.open - data.close;
        }
        var showH = disY / (kMaxValue - kMinValue) * canvasHeight * parsent;
        showH = showH > 2 ? showH : 2;

        var barH = parseInt(canvasHeight * (barVal - kMinValue) / (kMaxValue - kMinValue));
        var y = originY - barH;
        var x = originX + ((kWidth + kMargin) * i + kMargin) * parsent;

        // drawMA(MA5, i, x, "MA5");
        //drawMA(MA10, i, x, "MA10");
        //drawMA(MA20, i, x, "MA20");
        //drawMA(MA30, i, x, "MA30");
    }
    //drawBezier(point_MA5, "rgb(194,54,49)", 5);
    //drawBezier(point_MA10, "rgb(47,69,84)", 10);
    //drawBezier(point_MA20, "rgb(97,160,168)", 20);
    //drawBezier(point_MA30, "rgb(212,130,101)", 30);
    for (var i = 0; i < kBarsNum; i++) {
        var oneVal = parseInt(kMaxValue / TOTAL_Y_LABEL_NUM);
        var data = dataArr[i];
        var color = "rgb(13,244,155)";
        var barVal = data.open;
        var disY = 0;
        //开盘0 收盘1 最低2 最高3   跌30C7C9  涨D7797F
        if (data.close > data.open) { //涨
            color = "rgb(253,16,80)";
            barVal = data.close;
            disY = data.close - data.open;
        } else {
            disY = data.open - data.close;
        }
        var showH = disY / (kMaxValue - kMinValue) * canvasHeight * parsent;
        showH = showH > 2 ? showH : 2;

        var barH = parseInt(canvasHeight * (barVal - kMinValue) / (kMaxValue - kMinValue));
        var y = originY - barH;
        var x = originX + ((kWidth + kMargin) * i + kMargin) * parsent;

        drawRect(x, y, kWidth, showH, mouseMove, color, true); //开盘收盘  高度减一避免盖住x轴

        //最高最低的线
        showH = (data[3] - data[2]) / (kMaxValue - kMinValue) * canvasHeight * parsent;
        showH = showH > 2 ? showH : 2;

        y = originY - parseInt(canvasHeight * (data[3] - kMinValue) / (kMaxValue - kMinValue));
        drawRect(parseInt(x + kWidth / 2 - 1), y, 2, showH, mouseMove, color); //最高最低  高度减一避免盖住x轴


    }

    if (ctr < numctr) {
        ctr++;
        setTimeout(function () {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            drawLineLabelMarkers();
            drawBarAnimate();
            drawDragBar();
        }, speed *= 0.03);
    }
}

function drawBezier(point, color, num) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.font = "20px SimSun";
    ctx.fillStyle = "#ffffff";
    for (i = 0; i < point.length; i++) {

        if (i < num + 2) {
            ctx.moveTo(point[i].x, point[i].y);
        } else { //注意是从1开始
            var ctrlP = getCtrlPoint(point, i - 1);
            ctx.bezierCurveTo(ctrlP.pA.x, ctrlP.pA.y, ctrlP.pB.x, ctrlP.pB.y, point[i].x, point[i].y);
            //ctx.fillText("("+point[i].x+","+point[i].y+")",point[i].x,point[i].y);
        }
    }
    ctx.stroke();
}

function getCtrlPoint(ps, i, a, b) {
    if (!a || !b) {
        a = 0.25;
        b = 0.25;
    }
    //处理两种极端情形
    if (i < 1) {
        var pAx = ps[0].x + (ps[1].x - ps[0].x) * a;
        var pAy = ps[0].y + (ps[1].y - ps[0].y) * a;
    } else {
        var pAx = ps[i].x + (ps[i + 1].x - ps[i - 1].x) * a;
        var pAy = ps[i].y + (ps[i + 1].y - ps[i - 1].y) * a;
    }
    if (i > ps.length - 3) {
        var last = ps.length - 1
        var pBx = ps[last].x - (ps[last].x - ps[last - 1].x) * b;
        var pBy = ps[last].y - (ps[last].y - ps[last - 1].y) * b;
    } else {
        var pBx = ps[i + 1].x - (ps[i + 2].x - ps[i].x) * b;
        var pBy = ps[i + 1].y - (ps[i + 2].y - ps[i].y) * b;
    }
    return {
        pA: { x: pAx, y: pAy },
        pB: { x: pBx, y: pBy }
    }
}

//绘制方块
function drawRect(x, y, X, Y, mouseMove, color, ifBigBar, ifDrag) {
    ctx.beginPath();
    if (parseInt(x) % 2 !== 0) { //避免基数像素在普通分辨率屏幕上出现方块模糊的情况
        x += 0;
    }
    if (parseInt(y) % 2 !== 0) {
        y += 0;
    }
    if (parseInt(X) % 2 !== 0) {
        X += 0;
    }
    if (parseInt(Y) % 2 !== 0) {
        Y += 0;
    }
    ctx.rect(parseInt(x), parseInt(y), parseInt(X), parseInt(Y));

    if (ifBigBar && mouseMove && ctx.isPointInPath(mousePosition.x * 2, mousePosition.y * 2)) { //如果是鼠标移动的到柱状图上，重新绘制图表
        ctx.strokeStyle = color;
        ctx.strokeWidth = 20;
        ctx.stroke();
    }
    //如果移动到拖动选择范围按钮
    canvas.style.cursor = "default";
    if (ifDrag && ctx.isPointInPath(mousePosition.x * 2, mousePosition.y * 2)) { //如果是鼠标移动的到调节范围按钮上，改变鼠标样式
        //console.log(123);
        canvas.style.cursor = "all-scroll";
    }
    ctx.fillStyle = color;
    ctx.fill();
    ctx.closePath();
}

function drawDragBar() {
    drawRect(originX, originY + canvasSpace, canvasWidth, canvasMargin, false, "white");
    drawRect(originX, originY + canvasSpace, dragBarX - originX, canvasMargin, false, "rgb(87,93,110)");
    drawRect(dragBarX, originY + canvasSpace, dragBarWidth, canvasMargin, false, "red", false, true);
}

function goChart(cBox, dataArr) {
    // 创建canvas并获得canvas上下文
    canvas = document.createElement("canvas");
    if (canvas && canvas.getContext) {
        ctx = canvas.getContext("2d");
    }

    canvas.innerHTML = "你的浏览器不支持HTML5 canvas";
    cBox.appendChild(canvas);

    // 图表初始化
    // 图表信息
    canvasMargin = 100;
    canvasSpace = 100;
    //将canvas扩大2倍，然后缩小，以适应高清屏幕
    canvas.width = cBox.getAttribute("width") * 2;
    canvas.height = cBox.getAttribute("height") * 2;
    console.log(canvas.width, canvas.height);
    canvas.style.height = canvas.height / 2 + "px";
    canvas.style.width = canvas.width / 2 + "px";
    
    canvasHeight = canvas.height - canvasMargin * 2 - canvasSpace * 2;
    canvasWidth = canvas.width - canvasMargin * 2 - canvasSpace * 2;
    originX = canvasMargin + canvasSpace;
    originY = canvasMargin + canvasHeight;

    showArr = dataArr.slice(0, parseInt(dataArr.length));

    // 柱状图信息
    kBarsNum = showArr.length;
    kWidth = parseFloat(canvasWidth / kBarsNum / 3);
    kMargin = parseFloat((canvasWidth - kWidth * kBarsNum) / (kBarsNum + 1));
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
    kMaxValue += 2; //上面预留20的空间
    kMinValue -= 2; //下面预留20的空间
    TOTAL_Y_LABEL_NUM = 10;
    // 运动相关
    ctr = 1;
    numctr = 20;
    speed = 0;

    dragBarWidth = 10;
    dragBarX = canvasWidth + canvasSpace + canvasMargin - dragBarWidth;
}

//检测鼠标移动
var mouseTimer = null;
addMouseMove();

function addMouseMove() {
    canvas.addEventListener("mousemove", function (e) {
        var parsent = ctr / numctr;
        var event = e || window.event;
        var x = event.pageX - canvas.getBoundingClientRect().left - 60;
        var y = -event.pageY + canvas.getBoundingClientRect().top + 400;
        if (y > 0 && x > 0) {
            var positionx = 1;
            for (var i = 0; i < kBarsNum; i++) {
                if (x >= (1080 / kBarsNum) * i) {
                    positionx = i + 1;
                }
            }
            var xx = originX + ((kWidth + kMargin) * (positionx - 1) + kMargin) * parsent;

            ctx.clearRect(0, 0, canvas.width, canvas.height);
            drawLineLabelMarkers();
            drawBarAnimate(true);
            drawDragBar();
            drawLineWithColor(parseInt(xx + kWidth / 2 - 1), 40, parseInt(xx + kWidth / 2 - 1), 800);
            drawDashLine(ctx, 120, canvas.getBoundingClientRect().top + event.pageY * 2 - 90, 760 * 3, canvas.getBoundingClientRect().top + event.pageY * 2 - 90, 5);


            var vx = 10;
            var vy = canvas.getBoundingClientRect().top + event.pageY * 2 - 90 - 20;
            ctx.beginPath();
            ctx.moveTo(vx, vy);
            ctx.lineTo(vx + 100, vy);
            ctx.lineTo(vx + 100, vy + 40);
            ctx.lineTo(vx, vy + 40);
            ctx.lineTo(vx, vy); //绘制最后一笔使图像闭合
            ctx.lineWidth = 2;
            ctx.fillStyle = "rgb(104,113,130)";
            ctx.fill();
            ctx.stroke();


            var ch = parseFloat((kMaxValue - kMinValue) * y * 2 / canvasHeight + kMinValue).toFixed(2);

            ctx.fillStyle = "white";
            ctx.fillText(ch, vx + 50, vy + 30, 50); // 文字


            vx = parseInt(xx + kWidth / 2 - 1) + 20;
            vy = canvas.getBoundingClientRect().top + event.pageY * 2 - 90 + 20;
            ctx.beginPath();
            ctx.moveTo(vx, vy);
            ctx.lineTo(vx + 200, vy);
            ctx.lineTo(vx + 200, vy + 330);
            ctx.lineTo(vx, vy + 330);
            ctx.lineTo(vx, vy); //绘制最后一笔使图像闭合
            ctx.lineWidth = 2;
            ctx.fillStyle = "rgba(104,113,130,0.5)";
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = "white";
            ctx.textAlign = "left";
            ctx.fillText(dataArr[positionx - 1].date, vx + 20, vy + 30, 150); // 文字
            ctx.fillText("开盘价：" + dataArr[positionx - 1].open, vx + 20, vy + 70, 150); // 文字
            ctx.fillText("收盘价：" + dataArr[positionx - 1].close, vx + 20, vy + 105, 150); // 文字
            ctx.fillText("最高价：" + dataArr[positionx - 1].low, vx + 20, vy + 140, 150); // 文字
            ctx.fillText("最低价：" + dataArr[positionx - 1].high, vx + 20, vy + 175, 150); // 文字
            //ctx.fillText("MA5：" + MA5[positionx - 1], vx + 20, vy + 210, 150); // 文字
            //ctx.fillText("MA10：" + MA10[positionx - 1], vx + 20, vy + 245, 150); // 文字
            //ctx.fillText("MA20：" + MA20[positionx - 1], vx + 20, vy + 280, 150); // 文字
            //ctx.fillText("MA30：" + MA30[positionx - 1], vx + 20, vy + 315, 150); // 文字
        } else {
            e = e || window.event;
            if (e.offsetX || e.offsetX == 0) {
                mousePosition.x = e.offsetX;
                mousePosition.y = e.offsetY;
            } else if (e.layerX || e.layerX == 0) {
                mousePosition.x = e.layerX;
                mousePosition.y = e.layerY;
            }

            clearTimeout(mouseTimer);
            /*
            mouseTimer = setTimeout(function () {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                drawLineLabelMarkers();
                drawBarAnimate(true);
                drawDragBar();
            }, 10);
            */
        }

    });
}


//监听拖拽
canvas.onmousedown = function (e) {
    if (canvas.style.cursor != "all-scroll") {
        return false;
    }
    document.onmousemove = function (e) {
        e = e || window.event;
        if (e.offsetX || e.offsetX == 0) {
            dragBarX = e.offsetX * 2 - dragBarWidth / 2;
        } else if (e.layerX || e.layerX == 0) {
            dragBarX = e.layerX * 2 - dragBarWidth / 2;
        }

        if (dragBarX <= originX) {
            dragBarX = originX
        }
        if (dragBarX > originX + canvasWidth - dragBarWidth) {
            dragBarX = originX + canvasWidth - dragBarWidth;
        }

        var nb = Math.ceil(dataArr.length * ((dragBarX - canvasMargin - canvasSpace) / canvasWidth));
        showArr = dataArr.slice(0, nb || 1);

        // 柱状图信息
        kBarsNum = showArr.length;
        kWidth = parseFloat(canvasWidth / kBarsNum / 3);
        kMargin = parseFloat((canvasWidth - kWidth * kBarsNum) / (kBarsNum + 1));
    }

    document.onmouseup = function () {
        document.onmousemove = null;
        document.onmouseup = null;
    }
}

function getBeveling(x, y) {
    return Math.sqrt(Math.pow(x, 2) + Math.pow(y, 2));
}

function drawDashLine(context, x1, y1, x2, y2, dashLen) {
    dashLen = dashLen === undefined ? 5 : dashLen;
    //得到斜边的总长度  
    var beveling = getBeveling(x2 - x1, y2 - y1);
    //计算有多少个线段  
    var num = Math.floor(beveling / dashLen);
    for (var i = 0; i < num; i++) {
        context[i % 2 == 0 ? 'moveTo' : 'lineTo'](x1 + (x2 - x1) / num * i, y1 + (y2 - y1) / num * i);
    }
    context.stroke();
}





