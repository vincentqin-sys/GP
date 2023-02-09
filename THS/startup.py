from flask import Flask, url_for, views, abort, make_response, request
import flask, peewee
import json, os
import traceback

import query

app = Flask(__name__, static_folder='ui/el', template_folder='ui')

@app.route('/', methods = ['GET'])
def home():
    return flask.render_template('query.html')

@app.route('/my-select.js', methods = ['GET'])
def myselect():
    return flask.render_template('my-select.js')
    
@app.route('/queryByCode/<codes>', methods = ['GET'])
def queryByCodes(codes): # codes = 'code, code....' 股票代码
    cs = codes.split(',')
    data = query.queryManyFlatFullInfo(cs)
    #print('queryByCodes=', data, cs)
    return json.dumps(data, ensure_ascii=False)
    
@app.route('/queryByGN/<cndType>/<gns>', methods = ['GET'])
def queryByGN(gns, cndType): # gns = 'gn, gn....' 概念  cndType='AND' | 'OR'
    cs = gns.split(',')
    data = query.queryByGN(cs, cndType)
    codes = (d.code for d in data)
    rs = query.queryManyFlatFullInfo(codes)
    #print('queryByGN=', rs, data)
    return json.dumps(rs, ensure_ascii=False)

@app.route('/queryByHY/<hyName>', methods = ['GET'])
def queryByHY(hyName): # gns = 'gn, gn....' 概念  cndType='AND' | 'OR'
    data = query.queryByHY(hyName)
    codes = (d.code for d in data)
    rs = query.queryManyFlatFullInfo(codes)
    #print('queryByGN=', rs, data)
    return json.dumps(rs, ensure_ascii=False)

print(__name__)

if __name__ == '__main__':
    app.run(host = '0.0.0.0', port=8071, debug=True)