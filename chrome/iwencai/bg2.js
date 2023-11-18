// 监听消息
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
	let cmd = request['cmd'];
    let data = request['data'];
    let cl = false;

    if (cmd == 'SET_TOP_VOL') {
        cl = true;
        setTopVol(data);
    }
	
	if (sendResponse) {
		sendResponse('OK');
	}
});

function setTopVol(data) {
    if (! proc_info.topVols[data.day]) {
        proc_info.topVols[data.day] = [];
    }
    let arr = proc_info.topVols[data.day];
    arr.push(data);
}

function getTopVol(day) {
    return proc_info.topVols[day];
}