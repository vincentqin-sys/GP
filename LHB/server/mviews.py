from flask import Flask, request, Blueprint, jsonify
import json
import orm, mcore

class UserView(mcore.BaseView):
    _ormCls = orm.User

bp_user = Blueprint('user', __name__, url_prefix='/user')
UserView.initRoute(bp_user)

#-----------------------------------------------------
class DeptView(mcore.BaseView):
    _ormCls = orm.Dept

bp_dept = Blueprint('dept', __name__, url_prefix='/dept')
DeptView.initRoute(bp_dept)

def init(app : Flask):
    app.register_blueprint(bp_user)
    app.register_blueprint(bp_dept)