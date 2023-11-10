   // 修改fiddler的rule

    static function getParams(url) {
        var rt = new Object();
        var idx = url.IndexOf('?');
        if (idx < 0) {
            return rt;
        }
        url = url.Substring(idx + 1);
        var items = url.Split('&');
        for (var k in items) {
            var kv = items[k].Split('=');
            rt[kv[0]] = kv[1];
        }
        return rt;
    }

    static function OnBeforeResponse(oSession: Session) {
        if (m_Hide304s && oSession.responseCode == 304) {
            oSession["ui-hide"] = "true";
        }
        
        var furl = oSession.fullUrl;
        
        /*
        var demain = "http://basic.10jqka.com.cn/";
        if (furl.StartsWith(demain)) {
            url = furl.Substring(demain.Length);
            if (url.EndsWith("/field.html")) {
                // 同行比较
                var code = url.Substring(0, 6);
                var file = "D:/ths/f10/" + code + "-同行比较.html";
                oSession.utilDecodeResponse();
                oSession.SaveResponseBody(file);
                return;
            }
        }*/
        
        
        // 同花顺Level-2功能： 大单结构(主动买入大单，被动买入大单，主动卖出大单，被动卖出大单)
        // stockCode=601127&start=20231107&dayNum=0
        if (furl.StartsWith("http://apigate.10jqka.com.cn/d/charge/orderprism/orderStruct?")) {
            var params = getParams(furl);
            var code = params['stockCode'];
            var startDay = params['start'];
            var dayNum = params['dayNum']; // 0: 1日   2:3日  4:5日   8: 9日
            
            if (code && startDay && (dayNum == 0)) {
                oSession.utilDecodeResponse();
                var body = oSession.GetResponseBodyAsString();
				if (body.Length < 20) {
					return;
				}
				var ts = DateTime.Now.ToString();
                body = ts + '\t' + code + '\t' + startDay + '\t' + dayNum + '\n' + body + '\n';
                var path = "D:/ths/struct/" + code;
                var fs = new FileStream(path, FileMode.Append, FileAccess.Write);
                var bb = new UTF8Encoding(true).GetBytes(body);
                fs.Write(bb, 0, bb.Length);
                fs.Close();
            }
        }
        
    }