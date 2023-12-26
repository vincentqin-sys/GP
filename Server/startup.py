from flask import Flask, url_for, views, abort, make_response, request
# pip install  psutil
import psutil, time, os, threading, datetime
import flask, peewee as pw
import json, os, sys
from flask_cors import CORS 
import traceback
import logging
from multiprocessing import Process

cwd = os.getcwd()
w = cwd.index('GP')
cwd = cwd[0 : w + 2]
sys.path.append(cwd)

from THS import hot_server
from Server import lhb_server

app = Flask(__name__, static_folder='ui/static', template_folder='ui/templates')
cors = CORS(app)

logging.basicConfig(level = logging.ERROR)
log = logging.getLogger('werkzeug')
log.disabled = True

if __name__ == '__main__':
    print('启动8071服务')
    
    # 启动同花顺热点服务
    hot_server.startup(app)
    # 启动龙虎榜
    lhb_server.startup(app)

    app.run(host = '0.0.0.0', port=8070) #, debug=True  port=8071