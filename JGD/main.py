from flask import Flask, url_for, views, abort, make_response, request, render_template
from werkzeug.routing import BaseConverter           

import os, json
import tdx

class RegexConverter(BaseConverter):
    def __init__(self, map, *args):
        self.map = map
        self.regex = args[0]

    """
    def to_python(self, value):
        pass

    def to_url(self, values):
        pass
    """

app = Flask(__name__, static_folder='uis', template_folder='ui')

app.url_map.converters['regex'] = RegexConverter

@app.route('/load_code', methods = ['GET'])
def load_code():
    code = request.args.get('code')
    day = int(request.args.get('day'))
    period = request.args.get('period')
    maxNum = int(request.args.get('maxNum'))
    data = tdx.load_code(code, day, period, maxNum)
    txt = json.dumps(data, ensure_ascii = False)
    return txt

@app.route('/load_jgd', methods = ['GET'])
def load_jgd():
    data = tdx.JGD.select().execute()
    data = [it.__data__ for it in data]
    txt = json.dumps(data, ensure_ascii = False)
    # print(txt)
    return txt

@app.route('/update_jgd', methods = ['POST'])
def update_jgd():
    try:
        params = request.json
        id = params['id']
        old : tdx.JGD = tdx.JGD.get_by_id(id)
        old.name = params['name']
        old.code = params['code']
        if params['buyDay']:
            old.buyDay =  int(params['buyDay'])
        if params['buyPrice']:
            old.buyPrice = float(params['buyPrice'])
        if params['sellDay']:
            old.sellDay = int(params['sellDay'])
        if params['sellPrice']:
            old.sellPrice = float(params['sellPrice'])
        old.remark = params['remark']
        old.save()
        rt = {"status": "OK", 'info': 'Save Success !', 'data': old.__data__}
        print('update_jgd:', old.__data__, old)
        txt = json.dumps(rt, ensure_ascii = False)
        return txt
    except BaseException as e:
        rt = {"status": "FAIL", 'info': str(e)}
        txt = json.dumps(rt, ensure_ascii = False)
        return txt

@app.route('/insert_jgd', methods = ['POST'])
def insert_jgd():
    try:
        params = request.json
        if params['buyDay']:
            params['buyDay'] = int(params['buyDay'])
        if params['buyPrice']:
            params['buyPrice'] = float(params['buyPrice'])
        if params['sellDay']:
            params['sellDay'] = int(params['sellDay'])
        if params['sellPrice']:
            params['sellPrice'] = float(params['sellPrice'])
        obj = tdx.JGD.create(**params)
        rt = {"status": "OK", 'info': 'Insert Success !', 'data': obj.__data__}
        print('insert_jgd:', obj.__data__, obj)
        txt = json.dumps(rt, ensure_ascii = False)
        return txt
    except BaseException as e:
        rt = {"status": "FAIL", 'info': str(e)}
        txt = json.dumps(rt, ensure_ascii = False)
        return txt


@app.route('/ui/<regex(".*.html|.*.js"):url>', methods = ['GET'])
def html(url):
    print('url=', url)
    return render_template(url)


if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    #init
    pass

if __name__ == '__main__':    
    app.run(host = '0.0.0.0', port=8055, debug=True)