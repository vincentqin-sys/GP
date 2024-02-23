from flask import Flask, url_for, views, abort, make_response, request
import flask, peewee
from flask_cors import CORS 
import json, os, sys
import traceback
import requests, json, logging

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from THS import orm

def saveCLS_ZT():
    saveNum = 0
    num = len(request.json)
    day = None
    for it in request.json:
        day = it['day']
        obj = orm.CLS_ZT.get_or_none(code = it['code'], day = it['day'])
        if obj:
            continue
        saveNum += 1
        orm.CLS_ZT.create(**it)
    if saveNum > 0:
        print(f'[cls-server] save cls zt {day} {saveNum} / {num}')
    return {'status': 'OK'}

def startup(app : Flask):
    print('[cls-server]功能: 启动财联社服务')
    app.add_url_rule('/save-CLS-ZT', view_func=saveCLS_ZT, methods = ['POST'])
