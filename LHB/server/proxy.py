import requests, json, flask, socket, re
import mviews, orm, mcore

# 修改同花顺软件中的龙虎榜页面信息，添加营业部的注释信息
# fiddler AutoResponder
# regex:(?ix)http://news.10jqka.com.cn/data/api/lhcjmxgg/code/(\d+)/date/(.{10})/$
# http://localhost:8050/proxy?code=$1&date=$2

def proxy():
    code = flask.request.args.get('code')
    date = flask.request.args.get('date')
    url = f'http://news.10jqka.com.cn/data/api/lhcjmxgg/code/{code}/date/{date}?v=vv'
    #print(url)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36'}
    orgRes = requests.get(url, headers = headers)
    orgText = orgRes.text #str(orgRes.content, 'gbk')
    
    params = '{' + f'"Params":["1","{code}","{date}"]' + '}'
    res = requests.post('http://page2.tdx.com.cn:7615/TQLEX?Entry=CWServ.tdxsj_lhbd_ggxq', data = params)
    val = json.loads(res.text)
    if val.get('ErrorCode') != 0:
        return orgRes.text
    names = {}

    for it in val['ResultSets']:
        colNames = it['ColName']
        content = it['Content']
        if ('T008' not in colNames) or ('bq1' not in colNames):
            continue
        keyIdx = colNames.index('T008')
        valIdx = colNames.index('bq1')
        for c in content:
            if c[valIdx]:
                names[c[keyIdx]] = c[valIdx]
    #print(names)
    for k in names:
        v = names[k]
        orm.YouZi.saveInfo(k, v)
        rv = f'{k}  <span style="color:#f22; background-color:#aaa;" > {v} <span> '
        orgText = orgText.replace(k, rv)
    orgText = orgText.replace('width="350"', '')
    info = f"<a class='dc-more' href = 'http://page2.tdx.com.cn:7615/site/tdxsj/html/tdxsj_lhbd_ggxq.html?back=tdxsj_lhbd,%E9%BE%99%E8%99%8E%E6%A6%9C%E4%B8%AA%E8%82%A1,{code}' target='_blank' style='color:#FFFFFF;'> 打开通达信龙虎榜&gt;&gt; </a>"
    idx = orgText.find('<a class="dc-more"')
    if idx > 0:
        endIdx = orgText.find('</a>', idx) + 4
        sub = orgText[idx : endIdx]
        orgText = orgText.replace(sub, info)
    return orgText
    

def init(app):
    print('call prox init')
    app.add_url_rule('/proxy',  endpoint='proxy', view_func = proxy, methods = ['GET', 'POST'])


def initThsProxy():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', 8035))
        sock.listen(5)
        print("[*] THS Proxy Server started successfully [ 8035 ]")
    except Exception:
        print("[*] THS Proxy Server Unable to Initialize Socket")

    while True:
        try:
            conn, addr = sock.accept() #Accept connection from client browser
            data = conn.recv(8192) #Recieve client data
            doSocket(conn, data) #Starting a thread
        except KeyboardInterrupt:
            sock.close()
            print("\n[*] Graceful Shutdown")
   
def doSocket(conn, data):
    try:
        webserver, port, url = getProxyServerInfo(data)
        print('Proxy:', webserver, port, url)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((webserver, port))
        sock.send(data)
        buf = bytearray(b'')
        while True:
            reply = sock.recv(4096)
            if(len(reply) <= 0):
                break
            conn.send(reply)
            print(reply)
            #buf.extend(reply)
        #buf = doFilter(url, buf)
        #print(buf)
        #conn.send(buf)
        sock.close()
        conn.close()
    except socket.error as e:
        sock.close()
        conn.close()
        print('Proxy Error: ', e)

def doFilter(url, data):
    rex = r'http://news.10jqka.com.cn/data/api/lhcjmxgg/code/(\d+)/date/(.{10})/'
    ma = re.match(rex, url)
    if not ma:
        return data
    yzDesc = []
    code = ma.group(1)
    day = ma.group(2)
    details = orm.TdxLHB.select(orm.TdxLHB.detail).where(orm.TdxLHB.code == code, orm.TdxLHB.day == day)
    for d in details:
        detail = d[0]
        info = json.loads(detail)
        for item in info:
            if item['yzDesc']:
                yzDesc.append((item['yz'], item['yzDesc']))
        break
    if len(yzDesc) == 0:
        return data
    orgText = data.encode('gbk')
    for it in yzDesc:
        rv = f'{it[0]}  <span style="color:#f22; background-color:#aaa;" > {it[1]} <span> '
        orgText = orgText.replace(it[0], rv)
    orgText = orgText.replace('width="350"', '')
    info = f"<a class='dc-more' href = 'http://page2.tdx.com.cn:7615/site/tdxsj/html/tdxsj_lhbd_ggxq.html?back=tdxsj_lhbd,%E9%BE%99%E8%99%8E%E6%A6%9C%E4%B8%AA%E8%82%A1,{code}' target='_blank' style='color:#FFFFFF;'> 打开通达信龙虎榜&gt;&gt; </a>"
    idx = orgText.find('<a class="dc-more"')
    if idx > 0:
        endIdx = orgText.find('</a>', idx) + 4
        sub = orgText[idx : endIdx]
        orgText = orgText.replace(sub, info)
    return orgText.decode('gbk')

def getProxyServerInfo(data):
    first_line = data.split(b'\n')[0]
    url = first_line.split()[1]
    http_pos = url.find(b'://') # Finding the position of ://
    if(http_pos == -1):
        temp = url
    else:
        temp = url[(http_pos + 3):]
    port_pos = temp.find(b':')
    webserver_pos = temp.find(b'/')
    if webserver_pos == -1:
        webserver_pos = len(temp)
    webserver = ""
    port = -1
    if(port_pos == -1 or webserver_pos < port_pos):
        port = 80
        webserver = temp[ : webserver_pos]
    else:
        port = int((temp[(port_pos + 1) : ])[ : webserver_pos-port_pos - 1])
        webserver = temp[ : port_pos]
    print('Proxy info: ', webserver, port)
    return webserver.decode(), port, url.decode()

if __name__ == '__main__':
    initThsProxy()