var KLINE_SPACE = 4; // K线之间的间距
var KLINE_WIDTH = 10; // K线的宽度

class KLine {
    constructor(canvas) {
        this.hilightPosIdx = -1;
        this.selectPosIdxArr = [];
        this.dataArr = null;
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
        if (! cur) {
            return 'E'; // empty k-line
        }
        if (posIdx > 0) {
            let ZRDP = this.dataArr[posIdx - 1].close;
            let is20P = this.getCode().substring(0, 3) == '688' || this.getCode().substring(0, 2) == '30';
            if (cur.date < 20200824) {
                is20P = false;
            }
            let ZT = is20P ? 20 : 10;
            let isZT = (parseInt(ZRDP  * (100 + ZT) + 0.5) <= parseInt(cur.close * 100));
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
            return "rgb(255, 255, 0)";
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
            this.ctx.strokeStyle = '#7FFF00';
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
    
class TimeLine {
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