var KLINE_SPACE = 4; // K线之间的间距
var KLINE_WIDTH = 10; // K线的宽度

class KLineView {
    constructor(canvas) {
        this.hilightPosIdx = -1;
        this.selectPosIdxArr = [];
        this.dataArr = [];
        this.canvas = canvas;
        canvas.width = this.width  = $(canvas).width();
        canvas.height =  this.height = $(canvas).height();
        this.ctx = canvas.getContext("2d");
    }

    // [ {open, close, low, high, vol, money, rate}, ... ]
    setData(baseInfo, dataArr) {
        this.dataArr = dataArr;
        this.baseInfo = baseInfo;
    }

    calcMinMax() {
        //算最大值，最小值
        let kMaxValue = 0;
        let kMinValue = 9999999;
        for (var i = 0; i < this.dataArr.length; i++) {
            if (! this.dataArr[i]) {
                continue;
            }
            var barVal = this.dataArr[i].high;
            if (barVal > kMaxValue) {
                kMaxValue = barVal;
            }
            var barVal2 = this.dataArr[i].low;
            if (barVal2 < kMinValue) {
                kMinValue = barVal2;
            }
        }
        this.kMaxValue = kMaxValue;
        this.kMinValue = kMinValue;
    }

    priceToPoint(pos, price) {
        let x = pos * (KLINE_WIDTH + KLINE_SPACE) + KLINE_SPACE;
        let y = parseInt(this.height * ( 1 - (price - this.kMinValue) / (this.kMaxValue - this.kMinValue)));
        // y = Math.max(y, 0);
        return { 'x': x, 'y': y };
    }

    getCode() {
        if (this.baseInfo) {
            return this.baseInfo.code;
        }
        return '';
    }

    isZhiSu() { // 是否是指数
        return this.getCode().substring(0, 2) == '88';
    }

    getZDTag(posIdx) {
        let cur = this.dataArr[posIdx];
        if (posIdx < 0 || !this.dataArr || posIdx >= this.dataArr.length || !cur) {
            return 'E'; // empty k-line
        }
        if (posIdx > 0 && this.dataArr[posIdx - 1]['close']) {
            let ZRDP = this.dataArr[posIdx - 1].close;
            let is20P = this.getCode().substring(0, 3) == '688' || this.getCode().substring(0, 2) == '30';
            if (cur.date < 20200824) {
                is20P = false;
            }
            let ZT = is20P ? 20 : 10;
            let isZT = (parseInt(ZRDP  * (100 + ZT) + 0.5) <= parseInt(cur.close * 100 + 0.1));
            if (isZT) {
                return 'ZT';
            }
            let isZTZB = (parseInt(ZRDP  * (100 + ZT)+ 0.5) <= parseInt(cur.high * 100))  && (cur.high != cur.close);
            if (isZTZB) {
                return 'ZTZB';
            }
            let isDT = (parseInt(ZRDP * (100 - ZT) + 0.5) >= parseInt(cur.close * 100))
            if (isDT) {
                return 'DT';
            }
            let isDTZB = (parseInt(ZRDP * (100 - ZT) + 0.5) >= parseInt(cur.low * 100)) && (cur.low != cur.close);
            if (isDTZB) {
                return 'DTZB';
            }
            if (this.isZhiSu()) {
                let zf = (cur.close - ZRDP) / ZRDP * 100;
                let zf2 = Math.abs((Math.max(cur.high, ZRDP) - cur.low) / ZRDP * 100);
                if (zf >= 3.5 || zf2 >= 3.5) {
                    return 'DZDD'; // 指数大涨大跌
                }
            }
        }
        if (cur.open <= cur.close) {
            return 'Z';
        } else {
            return 'D';
        }
    }
    
    getKColor(tag) {
        if (tag == 'ZT' || tag == 'ZTZB')
            return "rgb(0, 0, 255)";
        if (tag == 'DT' || tag == 'DTZB')
            return "#FFC125";
        if (tag == 'DZDD')
            return "rgb(255, 0, 255)";
        if (tag == 'Z')
            return "rgb(253,50,50)";
        // tag is 'D'
        return "rgb(84,252,252)"
    }

    draw() {
        this.calcMinMax();
        this.ctx.clearRect(0, 0, this.width, this.height);
        let kBarsNum = this.dataArr.length;
        for (let i = 0; i < kBarsNum; i++) {
            let data = this.dataArr[i];
            if (! data) {
                continue;
            }
            let tag = this.getZDTag(i);
            let color = this.getKColor(tag);
          
            //最高最低的线
            this.ctx.beginPath();
            this.ctx.strokeStyle = color;
            this.ctx.lineWidth = 1;
            let pt1 = this.priceToPoint(i, data.low);
            let pt2 = this.priceToPoint(i, data.high);
            this.ctx.moveTo(pt1.x + parseInt(KLINE_WIDTH / 2) + 0.5, pt1.y);
            this.ctx.lineTo(pt2.x + parseInt(KLINE_WIDTH / 2) + 0.5, pt2.y);
            this.ctx.stroke();
            this.ctx.closePath();
            
            //绘制方块
            this.ctx.beginPath();
            pt1 = this.priceToPoint(i, data.open);
            pt2 = this.priceToPoint(i, data.close);
            this.ctx.rect(pt1.x + 0.5, Math.min(pt1.y, pt2.y) + 0.5, KLINE_WIDTH, Math.abs(pt1.y - pt2.y));
            if (data.close >= data.open) {
                this.ctx.fillStyle = 'rgb(255, 255, 255)';
                this.ctx.lineWidth = 1;
                this.ctx.strokeStyle = color;
                this.ctx.fill();
                this.ctx.stroke();
            } else {
                this.ctx.fillStyle = color;
                this.ctx.lineWidth = 0;
                this.ctx.fill();
                this.ctx.stroke();
            }
            this.ctx.closePath();
        }
        this.drawSelectMouse();
        this.drawMouse(this.hilightPosIdx);
    }

    getPosIdx(x) {
        let nx = x - KLINE_SPACE;
        var posIdx = parseInt(nx / (KLINE_WIDTH + KLINE_SPACE));
        
        if (posIdx >= this.dataArr.length) {
            posIdx = -1;
        } else if (posIdx < 0) {
            pos = -1;
        }
        return posIdx;
    }

    drawMouse(posIdx) {
        if (posIdx < 0 || posIdx >= this.dataArr.length) {
            return;
        }
        let nx = posIdx * (KLINE_WIDTH + KLINE_SPACE) + KLINE_SPACE + parseInt(KLINE_WIDTH / 2);
        this.ctx.beginPath();
        if (posIdx == this.hilightPosIdx) {
            this.ctx.strokeStyle = '#00ff00' // '#7FFF00';
            this.ctx.setLineDash([3, 4]);
        } else {
            this.ctx.strokeStyle = 'black';
            this.ctx.setLineDash([1, 4]);
        }
        this.ctx.lineWidth = 1;
        this.ctx.moveTo(nx + 0.5, 0);
        this.ctx.lineTo(nx + 0.5, this.height);
        this.ctx.stroke();
        this.ctx.closePath();
        this.ctx.setLineDash([]);
    }

    setSelectMouse(posIdx) {
        let i = this.selectPosIdxArr.indexOf(posIdx);
        if (i < 0)
            this.selectPosIdxArr.push(posIdx);
        else
            this.selectPosIdxArr.splice(i, 1);
    }

    drawSelectMouse() {
        for (let i in this.selectPosIdxArr) {
            let pos = this.selectPosIdxArr[i];
            this.drawMouse(pos);
        }
    }

    setHilightMouse(posIdx) {
        this.hilightPosIdx = posIdx;
    }
}
    
class TimeLineView {
    constructor(canvas) {
        this.data = null;
        this.canvas = canvas;
        canvas.width = this.width  = $(canvas).width();
        canvas.height =  this.height = $(canvas).height();
        this.ctx = canvas.getContext("2d");
    }

    setData(data) {
        // {pre: xx, dataArr: [{time, price, money, avgPrice, vol}, ...] }
        this.data = data;
    }

    calcMinMax() {
        //算最大值，最小值
        let maxPrice = 0;
        let minPrice = 9999999;
        for (var i = 0; i < this.data.dataArr.length; i++) {
            if (! this.data.dataArr[i]) {
                continue;
            }
            var price = this.data.dataArr[i].price;
            if (price > maxPrice) {
                maxPrice = price;
            }
            if (price < minPrice) {
                minPrice = price;
            }
        }
        this.maxPrice = maxPrice;
        this.minPrice = minPrice;
    }

    draw() {
        if (! this.data || this.data.dataArr.length == 0) {
            return;
        }
        let ctx = this.ctx;
        const POINT_NN = 1;// 每几分钟选一个点
        const PADDING_X = 30; // 右边留点空间
        
        this.calcMinMax();
        if (this.minPrice > this.data.pre)
            this.minPrice = this.data.pre;
        if (this.maxPrice < this.data.pre)
            this.maxPrice = this.data.pre;
        
        let pointsCount = parseInt(4 * 60 / POINT_NN); // 画的点数
        let pointsDistance = (this.width - PADDING_X) / (pointsCount - 1); // 点之间的距离
        
        ctx.fillStyle = 'rgb(255, 255, 255)';
        ctx.lineWidth = 1;
        this.ctx.clearRect(0, 0, this.width, this.height);
        if (this.data.dataArr[this.data.dataArr.length - 1].price >= this.data.pre)
            ctx.strokeStyle = 'rgb(255, 0, 0)';
        else
            ctx.strokeStyle = 'rgb(0, 204, 0)';
        ctx.beginPath();
        ctx.setLineDash([]);
        for (let i = 0, pts = 0; i < this.data.dataArr.length; i++) {
            if (i % POINT_NN != 0) {
                continue;
            }
            let x = pts * pointsDistance;
            let y = this.height - (this.data.dataArr[i].price - this.minPrice) * this.height / (this.maxPrice - this.minPrice);
            if (pts == 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
            ++pts;
        }
        ctx.stroke();
    
        // 画开盘价线
        ctx.strokeStyle = 'rgb(150, 150, 150)';
        ctx.beginPath();
        ctx.setLineDash([2, 4]);
        let y = this.height - (this.data.pre - this.minPrice) * this.height / (this.maxPrice - this.minPrice);
        ctx.moveTo(0, y);
        ctx.lineTo(this.width - PADDING_X, y);
        ctx.stroke();
        // 画最高、最低价
        this.drawZhangFu( (this.maxPrice - this.data.pre) * 100 / this.data.pre, this.width, 10);
        this.drawZhangFu( (this.minPrice - this.data.pre) * 100 / this.data.pre, this.width, this.height - 5);
    }
    
    drawZhangFu(zf, x, y) {
        if (zf >= 0) {
            this.ctx.fillStyle = 'rgb(255, 0, 0)';
        } else {
            this.ctx.fillStyle = 'rgb(0, 204, 0)';
        }
        zf = '' + zf;
        let pt = zf.indexOf('.');
        if (pt > 0) {
            zf = zf.substring(0, pt + 2);
        }
        zf += '%';
        let ww = this.ctx.measureText(zf).width;
        this.ctx.fillText(zf, x - ww, y);
    }

    drawMouse(x) {
        if (x < 0 || x >= this.width) {
            return;
        }
        this.ctx.beginPath();
        this.ctx.strokeStyle = 'black';
        this.ctx.setLineDash([1, 4]);
        this.ctx.lineWidth = 1;
        this.ctx.moveTo(x + 0.5, 0);
        this.ctx.lineTo(x + 0.5, this.height);
        this.ctx.stroke();
        this.ctx.closePath();
        this.ctx.setLineDash([]);
    }
}

class KLineUI {
    constructor(width, height) {
        let thiz = this;
        let canvas = $('<canvas style="float-x: left; width: ' + width + 'px; height: ' + height + 'px; border-right: solid 1px #ccc;" />');
        this.ui = canvas;
        canvas = canvas.get(0);
        this.view = new KLineView(canvas);
        canvas.addEventListener('mousemove', function(e) {
            thiz.mouseMove(e.offsetX, e.offsetY, true);
        });
        canvas.addEventListener('click', function(e) {
            thiz.click(e.offsetX, e.offsetY, true);
        });
        canvas.addEventListener('contextmenu', function(e) {
            thiz.rightClick(e.offsetX, e.offsetY, true);
            e.preventDefault();
        });
        canvas.addEventListener('mouseleave', function(e) {
            thiz.mouseLeave(true);
        });
        this.listeners = {};
    }

    mouseMove(x, y, notify) {
        let pos = this.view.getPosIdx(x);
        this.view.draw();
        this.view.drawMouse(pos);
        if (notify) {
            this.notify({name : 'MouseMove', pos : pos, x : x, y : y, source : this});
        }
    }

    click(x, y, notify) {
        let pos = this.view.getPosIdx(x);
        if (pos < 0) {
            return;
        }
        this.view.setSelectMouse(pos);
        this.view.draw();
        if (notify) {
            this.notify({name : 'Click', pos : pos, x : x, y : y, source : this});
        }
    }

    rightClick(x, y, notify) {
        let pos = this.view.getPosIdx(x);
        this.view.setHilightMouse(pos);
        this.view.draw();
        if (notify) {
            this.notify({name : 'RightClick', pos : pos, x : x, y : y, source : this});
        }
    }

    mouseLeave(notify) {
        this.view.draw();
        if (notify) {
            this.notify({name : 'MouseLeave', source : this});
        }
    }

    addListener(eventName, listener) {
        let lsts = this.listeners[eventName];
        if (! lsts) {
            lsts = this.listeners[eventName] = [];
        }
        lsts.push(listener);
    }

    // event = {name: '', ..}
    // {name: 'LoadDataEnd' }
    // {name : 'RightClick | Click | MouseMove', pos, x, y, source}
    notify(event) {
        let name = event.name;
        let lsts = this.listeners[name];
        if (! lsts) {
            return;
        }
        for (let i in lsts) {
            lsts[i](event);
        }
    }

    limitLoadDataLength(len) {
        let arr = this.view.dataArr;
        if (arr.length > len) {
            arr.splice(0, arr.length - len);
        }
        while (arr.length < len) {
            arr.unshift({});
        }
    }

    loadData(code, limitConfig) {
        let thiz = this;
        this.loadData_(code, limitConfig, function(info, klineInfo) {
            thiz.view.setData(info, klineInfo);
            // infoDiv.append(info.code + '<br/>' + info.name);
            thiz.loadTodayData_(code, limitConfig, thiz.view, function(view) {
                thiz.view.draw();
                thiz.notify({name : 'LoadDataEnd'});
            });
        });
    }

    // limitConfig = {startDate: xx,   endDate : xxx}
    loadData_(code, limitConfig, callback) {
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
    loadTodayData_(code, limitConfig, klineObj, callback) {
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

}

class TimeLineUI {
    constructor(width, height) {
        let thiz = this;
        let canvas = $('<canvas style="float-x: left; width: ' + width + 'px; height: ' + height + 'px; border-right: solid 1px #ccc;" />');
        this.ui = canvas;
        canvas = canvas.get(0);
        this.view = new TimeLineView(canvas);
        canvas.addEventListener('mousemove', function(e) {
            thiz.mouseMove(e.offsetX, e.offsetY, true);
        });
        canvas.addEventListener('mouseleave', function(e) {
            thiz.mouseLeave(true);
        });
        this.listeners = {};
    }

    mouseMove(x, y, notify) {
        this.view.draw();
        this.view.drawMouse(x);
        if (notify) {
            this.notify({name : 'MouseMove', x : x, y : y, source : this});
        }
    }

    mouseLeave(notify) {
        this.view.draw();
        if (notify) {
            this.notify({name : 'MouseLeave', source : this});
        }
    }

    addListener(eventName, listener) {
        let lsts = this.listeners[eventName];
        if (! lsts) {
            lsts = this.listeners[eventName] = [];
        }
        lsts.push(listener);
    }

    // {name: 'LoadDataEnd' }
    // {name : 'MouseMove', x, y, source}
    notify(event) {
        let name = event.name;
        let lsts = this.listeners[name];
        if (! lsts) {
            return;
        }
        for (let i in lsts) {
            lsts[i](event);
        }
    }

    loadData(code) {
        let thiz = this;
        this.loadData_(code, function(rs) {
            thiz.view.setData(rs);
            thiz.view.draw();
            thiz.notify({name: 'LoadDataEnd' });
        });
    }

    loadData_(code, callback) {
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
}

class KLineUIManager {
    constructor() {
        this.klineUIArr = [];
        this.loadDataEndNum = 0;
    }

    add(klineUI) {
        let thiz = this;
        this.klineUIArr.push(klineUI);
        klineUI.addListener('LoadDataEnd', function() {
            thiz.loadDataEndNum++;
            if (thiz.loadDataEndNum == thiz.klineUIArr.length) {
                thiz.onAllLoadDataEnd();
            }
        });
        klineUI.addListener('MouseMove', function(event) {thiz.onUserEvent(event);});
        klineUI.addListener('Click', function(event) {thiz.onUserEvent(event);});
        klineUI.addListener('RightClick', function(event) {thiz.onUserEvent(event);});
        klineUI.addListener('MouseLeave', function(event) {thiz.onUserEvent(event);});
    }

    onUserEvent(event) {
        let newEvent = $.extend({}, event);
        newEvent.name = 'Virtual' + event.name;
        for (let i in this.klineUIArr) {
            let cur = this.klineUIArr[i];
            if (event.source != cur) {
                if (event.name == 'MouseMove') cur.mouseMove(event.x, event.y, false);
                else if (event.name == 'Click') cur.click(event.x, event.y, false);
                else if (event.name == 'RightClick') cur.rightClick(event.x, event.y, false);
                else if (event.name == 'MouseLeave') cur.mouseLeave(false);
            }
            cur.notify(newEvent);
        }
    }

    onAllLoadDataEnd() {
        let maxLen = 0;
        for (let i in this.klineUIArr) {
            let cur = this.klineUIArr[i];
            if (maxLen < cur.view.dataArr.length) {
                maxLen = cur.view.dataArr.length;
            }
        }
        for (let i in this.klineUIArr) {
            let cur = this.klineUIArr[i];
            cur.limitLoadDataLength(maxLen);
        }
    }
}


class TimeLineUIManager {
    constructor() {
        this.timeLineUIArr = [];
    }

    add(timeLineUI) {
        let thiz = this;
        this.timeLineUIArr.push(timeLineUI);
        timeLineUI.addListener('MouseMove', function(event) {thiz.onUserEvent(event);});
        timeLineUI.addListener('Click', function(event) {thiz.onUserEvent(event);});
        timeLineUI.addListener('MouseLeave', function(event) {thiz.onUserEvent(event);});
    }

    onUserEvent(event) {
        let newEvent = $.extend({}, event);
        newEvent.name = 'Virtual' + event.name;
        for (let i in this.timeLineUIArr) {
            let cur = this.timeLineUIArr[i];
            if (event.source != cur) {
                if (event.name == 'MouseMove') cur.mouseMove(event.x, event.y, false);
                // else if (event.name == 'Click') cur.click(event.x, event.y, false);
                else if (event.name == 'MouseLeave') cur.mouseLeave(false);
            }
            cur.notify(newEvent);
        }
    }

}