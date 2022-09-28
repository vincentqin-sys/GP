
temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.setAttribute('charset', "UTF-8");
temp.src = chrome.extension.getURL('longhu-name-parse.js');
temp.async = false;
document.documentElement.appendChild(temp);


temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.setAttribute('charset', "UTF-8");
temp.src = chrome.extension.getURL('longhu-data-parse.js');
temp.async = false;
document.documentElement.appendChild(temp);

function showTip(data) {
	let color = '#ff3333';
	let ds = 5000;
	if (data['status'] == 'OK') {
		color = '#33ff33';
		ds = 1500;
	} else if (data['status'] == 'Exists') {
		color = '#ffff33';
		ds = 1500;
	}
	
	let html = $('<div style="position:fixed;  background-color:' + color + ';z-index: 99999; right: 0px; top: 0px; width: 400px; height: 100px; font-size: 20px; " > </div>');
	html.append(data['day'] + '<br/> Status: ' + data['status'] + '<br/>' + 'Msg: ' + data['msg']);
	$(document.body).append(html);
	html.delay(ds).hide('fast');
}

window.addEventListener("message", function(evt) {
	console.log(evt);
	
	let cmd = evt.data['cmd'];
	
	function handleResponse(data) {
		console.log('receive bg msg: ', data);
		// alert(data)
		showTip(data);
	}
	
	chrome.runtime.sendMessage(evt.data, handleResponse);
	
	if (cmd == 'LOAD_LONGHU_DATA_LIST') {
		
	}
	
}, false);