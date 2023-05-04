注意事项：
    开启fiddler，设置CROS response header，用于拦截验证码图片

修改fiddler rules：

static function OnPeekAtResponseHeaders(oSession: Session) {
    // add my Me 2023.04.23
    // || oSession.uriContains("upass.iwencai.com") || oSession.uriContains("www.iwencai.com")
    if (oSession.uriContains("captcha.10jqka.com.cn/getImg")) {
        oSession.oResponse.headers["Access-Control-Allow-Origin"] = "*";
        oSession.oResponse.headers["Access-Control-Allow-Credentials"] = "true";
        oSession.oResponse.headers["Access-Control-Allow-Methods"] = "*";
        // oSession.oResponse.headers["Access-Control-Allow-Headers"] = "accept, content-type, x-requested-with";
        FiddlerObject.log('CORS: ' + oSession.url);
    }
}