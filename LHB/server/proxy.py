import requests, json, flask
import mviews, orm, mcore

# 修改同花顺软件中的龙虎榜页面信息，添加营业部的注释信息
# fiddler AutoResponder
# regex:(?ix)http://news.10jqka.com.cn/data/api/lhcjmxgg/code/(\d+)/date/(.{10})/$
# http://localhost:8050/proxy?code=$1&date=$2

def proxy():
    code = flask.request.args.get('code')
    date = flask.request.args.get('date')
    url = f'http://news.10jqka.com.cn/data/api/lhcjmxgg/code/{code}/date/{date}?v=vv'
    print(url)
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
    app.add_url_rule('/proxy',  endpoint='proxy', view_func = proxy, methods = ['GET', 'POST'])