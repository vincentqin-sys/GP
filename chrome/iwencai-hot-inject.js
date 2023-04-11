
function getHotInfo(obj) {
    let rs = { code: obj.code, name: obj['股票简称'] };
    for (d in obj) {
        if (d.indexOf('个股热度排名') >= 0) {
            rs.hotOrder = parseInt(obj[d]);
        } else if (d.indexOf('个股热度') >= 0) {
            rs.hotValue = parseInt(obj[d] / 10000); // xx万
        }
    }
    return rs;
}

function getHotDate(obj) {
    for (d in obj) {
        if (d.indexOf('个股热度排名') >= 0) {
            let s = d.indexOf('[');
            let e = d.indexOf(']');
            let date = d.substring(s + 1, e);
            return date.substring(0, 4) + '-' + date.substring(4, 6) + '-' + date.substring(6);
        }
    }
    throw new Exception('Get Hot Date Fail: ', obj);
    // return 'NotFind';
}

function getHotTime() {
    let ct = new Date();
    let hotTime = '';
    if (ct.getHours() < 10)
        hotTime += '0';
    hotTime += ct.getHours();
    hotTime += ':';
    if (ct.getMinutes() < 10)
        hotTime += '0';
    hotTime += ct.getMinutes();
    return hotTime;
}

function doLoadHotInfo(res) {
    let txt = res.response;
    try {
        let data = JSON.parse(txt);
        let datas = data.data.answer[0].txt[0].content.components[0].data.datas;
        let info = { hotInfo: [], hotDay: getHotDate(datas[0]), hotTime: getHotTime() };
        for (let i in datas) {
            let hi = getHotInfo(datas[i]);
            info.hotInfo.push(hi);
        }
        window.postMessage({ cmd: 'SET_HOT_INFO', data: info });
    } catch (e) {
        let info = 'Json changed: ' + e;
        console.log('Json changed: ', e);
        window.postMessage({ cmd: 'LOG', data: info });
    }
}

function doModifyHotRequest(config) {
    let body = JSON.parse(config.body);
    body['perpage'] = 100; //修改每页100个
    body = JSON.stringify(body);
    config.body = body;
    console.log('Modify Hot Request: ', config);
}

function hook_ajax() {
    if (! window['ah']) {
        setTimeout(hook_ajax, 50);
        return;
    }
    console.log('Hook ajax proxy OK');
    ah.proxy({
        onRequest: function (config, handler) {
            // console.log('my proxy request = ', config)
            let targetUrl = '/customized/chart/get-robot-data';
            if (config.url.indexOf(targetUrl) >= 0) {
                doModifyHotRequest(config);
            }
            handler.next(config)
        },

        onError: function (err, handler) {
            handler.next(err);
        },

        onResponse: function (response, handler) {
            let url = response.config.url;
            // console.log('my proxy response = ', response);
            let targetUrl = '/customized/chart/get-robot-data';
            if (url.indexOf(targetUrl) >= 0) {
                // console.log('my proxy response Hot = ', response);
                doLoadHotInfo(response);
            }
            handler.next(response)
        },
    });
}

hook_ajax();