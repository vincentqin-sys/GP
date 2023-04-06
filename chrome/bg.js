proc_info = {
    hotWindowId: 0,
    hotLastOpenTabTime: 0,
    hotInfos : [],
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

// 监听消息
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
	let cmd = request['cmd'];
    let data = request['data'];

    if (cmd == 'SET_HOT_INFO') {
        // console.log('sender=', sender);
        if (sender && sender.tab && sender.tab.windowId == proc_info.hotWindowId) {
            setHotInfo(data);
        }
	}
	
	if (sendResponse) {
		sendResponse('OK');
	}
});

function setHotInfo(data) {
    if (! proc_info.hotWindowId) {
        return;
    }
    let curDate = formatDate(new Date());
    if (curDate == data.hotDay) {
        proc_info.hotInfos.push(data);
    }
    try {
        chrome.windows.remove(proc_info.hotWindowId);
    } catch (e) {}
    proc_info.hotWindowId = 0;
    proc_info.hotLastOpenTabTime = Date.now();
    // save to server http://localhost:8071/saveHot
    $.ajax({
        url: 'http://localhost:8071/saveHot',
        method: 'POST',
        dataType : 'json',
        data: JSON.stringify(data),
        success: function (res) {
            console.log('Send hot info to server success: ', res);
        },
        error: function (res) {
            console.log('Send hot info to server Fail: ', res);
        }
    });
}

// 热股排名
function hot_run() {
    let dt = new Date();
    let week = dt.getDay();
    if (week == 0 || week == 6) {
        // 周六 周日
        return;
    }
    let hour = dt.getHours();
    if (hour < 9 || hour >= 16) {
        return;
    }

    if ((Date.now() - proc_info.hotLastOpenTabTime) / 1000 / 60 < 30) { // 30 minutes
        return;
    }

    let url = 'http://www.iwencai.com/unifiedwap/result?w=%E4%B8%AA%E8%82%A1%E7%83%AD%E5%BA%A6%E6%8E%92%E5%90%8D%3C%3D100%E4%B8%94%E4%B8%AA%E8%82%A1%E7%83%AD%E5%BA%A6%E4%BB%8E%E5%A4%A7%E5%88%B0%E5%B0%8F%E6%8E%92%E5%90%8D&querytype=stock';
    chrome.windows.create({url : url, type : 'panel'}, function(window) {
            // callback
            proc_info.hotWindowId = window.id;
        }
    );
}



setInterval(hot_run, 1000 * 60 * 5);