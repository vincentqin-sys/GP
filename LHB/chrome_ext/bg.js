//Breaking the CORS Limitation
/*
Access-Control-Allow-Methods:"*",
Access-Control-Allow-Headers:"Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With"

链接：https://juejin.cn/post/6844903639186669582
*/


// 监听消息
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
	let cmd = request['cmd'];
	if (cmd == 'LONGHU_DATA_LIST') {
		let lhbData = request['data'];
		console.log(lhbData);
		
		$.ajax({
			url: 'http://localhost:8050/writeLHBDataList',
			method: 'post',
			data: JSON.stringify(lhbData),  
			// dataType:'json', 
			contentType:'application/json', 
			success : function(data) {
					console.log(data);
					data = JSON.parse(data);
					data['day'] = lhbData['day'];
					console.log('Write ' + data['status'] + ': ', lhbData['day']);
					if (sendResponse) {
						sendResponse(data);
					}
				}
			});
	}
	
	return true;
});


// chrome中跨域问题解决方案 
// 插件解决， 插件地址  https://chrome.google.com/webstore/detail/allow-control-allow-origi/nlfbmbojpeacfghkpbjhddihlkkiljbi  (请用正确的方式打开)