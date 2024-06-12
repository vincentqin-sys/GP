// HH:MM
function formatTime(date) {
    let d = date;
    let h = d.getHours();
    let m = d.getMinutes();
    let v = '';
    v += h > 9 ? h : '0' + h;
    v += ':';
    v += m > 9 ? m : '0' + m;
    return v;
}

function _doHook(response) {
	let data = response.response;
	let len = response.headers['content-length'];
	if (! len) {
		return;
	}
	let url = response.config.url;
	if (! url) {
		return;
	}
	if (url.indexOf('https://x-quote.cls.cn/quote/index/up_down_analysis') >= 0) {
		//loadZTInfo(response);
		adjustZTInfo(response);
		return;
	}
	if (url.indexOf('https://x-quote.cls.cn/quote/stock/emotion_options') >= 0) {
        //loadDegree(response);
    }
}

function loadDegree(response) {
	//console.log('Hook response ->', response);
	if (formatTime(new Date()) <= '15:00') {
        return;
    }
	let body = response.response;
	let json = JSON.parse(body);
	let day = json.data.date;
	let degree = json.data.market_degree;
	degree = parseInt(parseFloat(degree) * 100);
	console.log(formatTime(new Date()), '==>', day, degree);
	let data = {day, degree};
	sendToServer('http://localhost:8071/save-CLS-Degree', data);
}

function loadZTInfo(response) {
	//console.log('Hook response ->', response);
	let body = response.response;
	let json = JSON.parse(body);
	let rs = [];
	for (i in json.data) {
		let item = json.data[i];
		if (item.is_st != 0)
			continue
		let obj = {code : item.secu_code, name: item.secu_name, lbs: item.limit_up_days};
		if (obj.code && obj.code.length == 8) {
			obj.code = obj.code.substring(2);
		}
		// obj.ztTime = item.time.substring(11, 16);
		obj.day = item.time.substring(0, 10);
		obj.ztReason = '';
		if (item.up_reason.indexOf(' | ') > 0) {
			let idx = item.up_reason.indexOf('|');
			obj.ztReason = item.up_reason.substring(0 , idx).trim();
			obj.detail = item.up_reason.substring(idx + 1).trim();
		} else {
			obj.detail = item.up_reason;
		}
		if (obj.ztReason && obj.ztReason.trim() != '--') {
			rs.push(obj);
		}
	}
	console.log(rs);
	//sendToServer('http://localhost:8071/save-CLS-ZT', rs);
}

function adjustZTInfo(response) {
	let body = response.response;
	let json = JSON.parse(body);
	console.log(json);
	let rs = [];
	for (i in json.data) {
		let item = json.data[i];
		if (item.is_st != 0)
			continue
		rs.push(item);
	}
	json.data = rs;
	response.response = JSON.stringify(json);
	//window.postMessage({cmd: 'ZT-INFO', data: rs}, '*');
	window['zt-info'] = rs;
}

function sendToServer(url, data) {
    if (data.length <= 0) {
        return;
    }
    $.ajax({
        url: url,
        method: 'POST',
        dataType: 'json',
        contentType : 'application/json',
        data: JSON.stringify(data),
        success: function (res) {
            console.log('Success: Send to server success ', res);
        },
        error: function (res) {
            console.log('Fail: Send to server fail ', data);
        }
    });
}

function hook_proxy() {
	ah.proxy({
		onRequest:  function(config, handler) {
			// console.log('Hook request ->', config);
			handler.next(config)
		},
		
		onError: function(err, handler) {
			handler.next(err);
		},
		
		onResponse:function(response, handler) {
			_doHook(response);
			handler.next(response)
		},
	});
}

hook_proxy();
console.log('in hook :', window.location.href)

/*
var _can2DProto = CanvasRenderingContext2D.prototype;
var _old_can2d_ft = _can2DProto.fillText;
let _txtAll = ''
let doTtt = false;
_can2DProto.fillText = function(txt, x, y) {
	_old_can2d_ft.call(this, txt, x, y);
	let v = txt.replace(/[\r\n]/g, '');
	// console.log(v);
	_txtAll += v;
	if (! doTtt) {
		doTtt = true;
		setTimeout(function() {
			console.log(_txtAll);
		}, 4000);
	}
}
*/