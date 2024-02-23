proc_info = {
    clsZTWindowId: 0,
    lastOpenZSPageTime : 0,
    savedDays : {} // day : True
};

// YYYY-MM-DD
function formatDate(date) {
    let d = date;
    let m = d.getMonth() + 1;
    return '' + d.getFullYear() + '-' + (m > 9 ? m : '0' + m) + '-' + (d.getDate() > 9 ? d.getDate() : '0' + d.getDate());
}

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

function mlog(...args) {
    let ms = formatDate(new Date()) + ' ' + formatTime(new Date());
    console.log('[' + ms + '] ', ...args);
}

// 监听消息
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
	let cmd = request['cmd'];
    let data = request['data'];

    if (cmd == 'SAVED_ZT') {
        if (sender && sender.tab && sender.tab.windowId == proc_info.clsZTWindowId) {
            let today = formatDate(new Date());
            proc_info.savedDays[today] = true;
        }
    } else if (cmd == 'LOG') {
        mlog('Log', request);
    }
	if (sendResponse) {
		sendResponse('OK');
	}
});


function deepCopy(obj) {
    let _obj = Array.isArray(obj) ? [] : {};
    for (let i in obj) {
        _obj[i] = (typeof obj[i] === 'object') ? deepCopy(obj[i]) : obj[i];
    }
    return _obj;
}

function checkWindowAlive() {
    let bt = (Date.now() - proc_info.lastOpenZSPageTime) / 1000 >= 60;
    if (! bt) {
        return;
    }
    let wid = proc_info.clsZTWindowId;
    proc_info.clsZTWindowId = 0; // reset window id
    chrome.windows.remove(wid, function () {
            // proc_info.clsZTWindowId = 0;
        }
    );
}

function run_loop() {
    if (proc_info.clsZTWindowId) {
        checkWindowAlive();
        return;
    }
    let ft = formatTime(new Date());
    if (ft <= '15:00') {
        return;
    }
    let today = formatDate(new Date());
    if (! proc_info.savedDays[today] && (Date.now() - proc_info.lastOpenZSPageTime >= 30 * 60 * 1000)) {
        openZTPage();
    }
}

function openZTPage() {
    let url = 'https://www.cls.cn/finance';
    chrome.windows.create({ url: url, type: 'panel' }, function (window) {
        // callback
        proc_info.clsZTWindowId = window.id;
        proc_info.lastOpenZSPageTime = Date.now();
    });
}

setInterval(run_loop, 1000 * 20); // 20 seconds

// CORS
function updateHeaders(hds, name, value) {
	let sname = name.toLowerCase();
	for (let i = 0; i < hds.length; i++) {
		if (hds[i].name.toLowerCase() == sname) {
			hds[i].value = value;
			return;
		}
	}
	hds.push({'name': name, 'value': value});
}

chrome.webRequest.onHeadersReceived.addListener(function(details) {
		let hds = details.responseHeaders;
		updateHeaders(hds, 'Access-Control-Allow-Origin', '*');
		updateHeaders(hds, 'Access-Control-Allow-Credentials', 'true');
		updateHeaders(hds, 'Access-Control-Allow-Methods', '*');
		return {responseHeaders : hds};
	},
	{urls: ['https://www.cls.cn/*', '*://*/*']},
	['responseHeaders','blocking', 'extraHeaders']
);