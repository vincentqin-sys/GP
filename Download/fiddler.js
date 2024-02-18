    // 修改fiddler的rule

    import System.IO;
    import System.Text;

   // ---------------------------------------------
    static function mkdirs(path) {
        if(! Directory.Exists(path)) {
            var di = new DirectoryInfo(path);
            di.Create()
        }
    }

    // 同行比较
    static function load_THBJ(furl, oSession) {
        var demain = "http://basic.10jqka.com.cn/";
        if (! furl.StartsWith(demain)) {
            return;
        }
        url = furl.Substring(demain.Length);
        if (! url.EndsWith("/field.html")) {
            return;
        }
        var code = url.Substring(0, 6);
        var file = "D:/ThsData/f10/" + code + "-同行比较.html";
        oSession.utilDecodeResponse();
        oSession.SaveResponseBody(file);
    }

   //----------------------------------------------

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

    // 是否是交易时间段
    static function isTradeTime() {
        var dw = DateTime.Now.DayOfWeek;
        if (dw >= 1 && dw <= 5) { // 周一至周五
            var tt = DateTime.Now.ToString('t') // 13:09	HH:MM
            if (tt >= '09:00' && tt < '15:00') {
                return true;
            }
        }
        return false;
    }

    // 同花顺Level-2功能：大单买卖详细数据
    // stockCode=601136
    static function load_ddlr_detail(furl, oSession) {
        if (isTradeTime())
            return;
        var TAG_URL = "http://apigate.10jqka.com.cn/d/charge/orderprism/historyOrder?"
        if (! furl.StartsWith(TAG_URL))
            return;
        var params = getParams(furl);
        var code = params['stockCode'];
        oSession.utilDecodeResponse();
        var body = oSession.GetResponseBodyAsString();
        var ts = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
        var path = "D:/ThsData/ddlr-detail-src/" + code;
        body = ts + '\t' + code + '\n' + body + '\n';
        var fs = new FileStream(path, FileMode.Append, FileAccess.Write);
        var bb = new UTF8Encoding(true).GetBytes(body);
        fs.Write(bb, 0, bb.Length);
        fs.Close();
    }

    // 同花顺Level-2功能： 大单结构(主动买入大单，被动买入大单，主动卖出大单，被动卖出大单)
    // stockCode=601127&start=20231107&dayNum=0
    static function load_ddlr_struct(furl, oSession) {
        if (isTradeTime())
            return;
        var TAG_URL = "http://apigate.10jqka.com.cn/d/charge/orderprism/orderStruct?"
        if (! furl.StartsWith(TAG_URL))
            return;
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
            var ts = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
            body = ts + '\t' + code + '\t' + startDay + '\t' + dayNum + '\n' + body + '\n';
            var path = "D:/ThsData/ddlr-struct/" + code;
            var fs = new FileStream(path, FileMode.Append, FileAccess.Write);
            var bb = new UTF8Encoding(true).GetBytes(body);
            fs.Write(bb, 0, bb.Length);
            fs.Close();
        }
    }

    static function OnBeforeResponse(oSession: Session) {
        if (m_Hide304s && oSession.responseCode == 304) {
            oSession["ui-hide"] = "true";
        }
        
        var furl = oSession.fullUrl;
        // load_THBJ(furl, oSession);
        load_ddlr_detail(furl, oSession);
        load_ddlr_struct(furl, oSession);
    }