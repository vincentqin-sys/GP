var KLINE_SPACE = 4; // K线之间的间距
var KLINE_WIDTH = 12; // K线的宽度

class KLine {
    constructor(canvas) {
        this.canvas = canvas;
        canvas.width = this.width  = $(canvas).width();
        canvas.height =  this.height = $(canvas).height();
        this.ctx = canvas.getContext("2d");
        console.log('canvas size = ', this.width , this.height);
    }

    // [ {open, close, low, high, vol, money, rate}, ... ]
    setData(baseInfo, dataArr) {
        this.dataArr = dataArr;
        this.baseInfo = baseInfo;
        this.calcMinMax();
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
    }

    getPosIdx(x) {
        let nx = x - KLINE_SPACE;
        var posIdx = parseInt(nx / (KLINE_WIDTH + KLINE_SPACE));
        if (posIdx >= this.dataArr.length) {
            posIdx = this.dataArr.length - 1;
        } else if (posIdx < 0) {
            pos = 0;
        }
        return posIdx;
    }

    drawMouse(x, y) {
        var posIdx = this.getPosIdx(x);
        let nx = posIdx * (KLINE_WIDTH + KLINE_SPACE) + KLINE_SPACE + parseInt(KLINE_WIDTH / 2);
        this.ctx.beginPath();
        this.ctx.setLineDash([2, 2]);
        this.ctx.strokeStyle = 'black';
        this.ctx.lineWidth = 1;
        this.ctx.moveTo(nx + 0.5, 0);
        this.ctx.lineTo(nx + 0.5, this.height);
        this.ctx.stroke();
        this.ctx.closePath();
        this.ctx.setLineDash([]);
    }
}
    
