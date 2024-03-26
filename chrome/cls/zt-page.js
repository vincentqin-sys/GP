// YYYY-MM-DD
function formatDate() {
    let d = new Date();
    let m = d.getMonth() + 1;
    return '' + d.getFullYear() + '-' + (m > 9 ? m : '0' + m) + '-' + (d.getDate() > 9 ? d.getDate() : '0' + d.getDate());
}

// HH:MM
function formatTime() {
    let d = new Date();
    let h = d.getHours();
    let m = d.getMinutes();
    let v = '';
    v += h > 9 ? h : '0' + h;
    v += ':';
    v += m > 9 ? m : '0' + m;
    return v;
}

setTimeout(() => {
    //headers = loadHeaders();
    //data = loadPageData();
    //sendToServer(data);
    // loadDegree();
}, 15 * 1000);


if (formatTime() >= '09:25' && formatTime() <= '15:15') {
    setTimeout(() => {
        window.location.reload();
    }, 3 * 60 * 1000);
}

if (window.location.href.indexOf('autoClose') > 0) {
    setTimeout(function() {
        window.close();
    }, 3000);
}

