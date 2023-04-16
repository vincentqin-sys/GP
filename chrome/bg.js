proc_info = {
    hotWindowId: 0,
    lastOpenHotPageTime: 0,
    lastOpenHotPageTimeForSave: 0,
    needSave: false,
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
    } else if (cmd == 'LOG') {
        console.log('Receive message', data);
    }
	
	if (sendResponse) {
		sendResponse('OK');
	}
});

function setHotInfo(data) {
    if (! proc_info.hotWindowId) {
        return;
    }
    try {
        chrome.windows.remove(proc_info.hotWindowId);
    } catch (e) { }
    
    proc_info.hotWindowId = 0;

    let curDate = formatDate(new Date());
    let needSaveToServer = (curDate == data.hotDay && proc_info.needSave);
    proc_info.needSave = false;
    if (needSaveToServer) {
        proc_info.hotInfos.push(data);
        sendHotInfoToServer(data);
    }
}

function deepCopy(obj) {
    let _obj = Array.isArray(obj) ? [] : {};
    for (let i in obj) {
        _obj[i] = (typeof obj[i] === 'object') ? deepCopy(obj[i]) : obj[i];
    }
    return _obj;
}

function sendHotInfoToServer(data) {
    // save to server http://localhost:8071/saveHot
    // data = deepCopy(data);
    $.ajax({
        url: 'http://localhost:8071/saveHot',
        method: 'POST',
        dataType: 'json',
        contentType : 'application/json',
        data: JSON.stringify(data),
        success: function (res) {
            console.log('Success: Send hot info to server success ', res, data);
        },
        error: function (res) {
            console.log('Fail: Send hot info to server fail ', data);
        }
    });
}

// 热股排名
function hot_run() {
    if (proc_info.hotWindowId) {
        return;
    }
    let ft = formatTime(new Date());
    let jtTime = (ft >= '09:30' && ft < '11:35') || (ft >= '13:00' && ft < '15:05');
    let day = new Date();
    let jtDay = day.getDay() != 0 && day.getDay() != 6; // not 周六周日
    let holidays = ['2023-05-01', '2023-05-02', '2023-05-03', '2023-06-22', '2023-06-23', '2023-09-29', '2023-10-02', '2023-10-03', '2023-10-04', '2023-10-05', '2023-10-06'];
    jtDay = jtDay && (holidays.indexOf(formatDate(new Date())) < 0); // 不是节假日

    if (jtTime && jtDay) {
        if ((Date.now() - proc_info.lastOpenHotPageTimeForSave) / 1000 / 60 >= 15) { // 15 minutes
            openHotPage(true);
        }
    } else {
        if ((Date.now() - proc_info.lastOpenHotPageTime) / 1000 / 60 >= 30) { // 30 minutes, used for keep logined state
            openHotPage(false);
        }
    }
}

function openHotPage(needSave) {
    let url = 'http://www.iwencai.com/unifiedwap/result?w=%E4%B8%AA%E8%82%A1%E7%83%AD%E5%BA%A6%E6%8E%92%E5%90%8D%3C%3D200%E4%B8%94%E4%B8%AA%E8%82%A1%E7%83%AD%E5%BA%A6%E4%BB%8E%E5%A4%A7%E5%88%B0%E5%B0%8F%E6%8E%92%E5%90%8D&querytype=stock&mytag=bg';
    chrome.windows.create({ url: url, type: 'panel' }, function (window) {
        // callback
        proc_info.hotWindowId = window.id;
        proc_info.needSave = needSave;
        proc_info.lastOpenHotPageTime = Date.now();
        if (needSave) {
            proc_info.lastOpenHotPageTimeForSave = Date.now();
        }
    });
}



setInterval(hot_run, 1000 * 20); // 20 seconds