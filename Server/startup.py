from flask import Flask, url_for, views, abort, make_response, request
# pip install  psutil
import psutil, time, os, threading, datetime
import flask, peewee as pw
import json, os, sys
from flask_cors import CORS 
import traceback
import logging
from multiprocessing import Process

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

from Server import lhb_server, hot_server
from Server import lhb_downloader

app = Flask(__name__, static_folder='ui/static', template_folder='ui/templates')
cors = CORS(app)

logging.basicConfig(level = logging.ERROR)
log = logging.getLogger('werkzeug')
log.disabled = True

def showHot():
    return flask.render_template('show-hot.html')

if __name__ == '__main__':
    print('启动8071服务')
    
    # 启动同花顺热点服务
    hot_server.startup(app)
    app.add_url_rule('/show-hot.html', view_func=showHot,  methods = ['GET'])

    # 启动龙虎榜
    lhb_server.startup(app)
    lhb_downloader.autoLoadTdxLHB()

    app.run(host = '0.0.0.0', port=8071, debug=False) #, debug=True  port=8071