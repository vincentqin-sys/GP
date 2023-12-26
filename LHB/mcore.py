from email.policy import default
from flask import render_template, request, jsonify, Blueprint, url_for, g
from flask.views import MethodView, View
import peewee as pw


# proxy = pw.DatabaseProxy()
# proxy.initialize(db)

class BaseView(MethodView):
    _ormCls = None

    def before(self, name, *args, **kwargs):
        orm = self.__class__._ormCls
        if name == 'list':
            g.datas = [d.__data__ for d in orm.select().execute()]
        elif name == 'detail' or name == 'update':
            d = orm.get_or_none(orm.id == request.args.get('id', type=int))
            g.data = d.__data__ if d else orm().__data__
        pass

    def list(self, *args, **kwargs):
        url = f'{self.__class__._url_prefix}/list.html'
        return render_template(url)

    def add(self, *args, **kwargs):
        return render_template(f'{self.__class__._url_prefix}/add.html')

    def update(self, *args, **kwargs):
        return render_template(f'{self.__class__._url_prefix}/update.html')

    def detail(self, *args, **kwargs):
        return render_template(f'{self.__class__._url_prefix}/detail.html')

    @classmethod
    def as_uiview(cls, funcName):
        def uiview(*args, **kwargs):
            obj = uiview._cls()
            v = getattr(obj, uiview._funcName)
            obj.before(uiview._funcName, *args, **kwargs)
            return v(*args, **kwargs)
        uiview._cls = cls
        uiview._funcName = funcName
        uiview.__name__ = cls.__name__ + '_uiview_' + funcName
        return uiview

    @classmethod
    def initRoute(cls, bp : Blueprint):
        cls._url_prefix = bp.url_prefix
        viewFunc = cls.as_view(bp.name)
        bp.add_url_rule('/', defaults={'id': None}, view_func=viewFunc,  methods=['GET',])
        bp.add_url_rule('/', view_func=viewFunc, methods=['POST',])
        bp.add_url_rule('/<int:id>', view_func=viewFunc, methods=['GET', 'PUT', 'DELETE'])

        bp.add_url_rule('/list.html', view_func=cls.as_uiview('list'),  methods=['GET',])
        bp.add_url_rule('/add.html', view_func=cls.as_uiview('add'),  methods=['GET',])
        bp.add_url_rule('/update.html', view_func=cls.as_uiview('update'),  methods=['GET',])
        bp.add_url_rule('/detail.html', view_func=cls.as_uiview('detail'),  methods=['GET',])

    @classmethod
    def addUrlRule(cls, bp : Blueprint, rule, funcName):
        bp.add_url_rule(rule, view_func=cls.as_uiview(funcName),  methods=['GET',])

    @property
    def orm(self) -> pw.Model:
        return self.__class__._ormCls

    def success(self, data):
        return jsonify(status='OK', msg=None, data=data)
    def fail(self, msg, data = None):
        return jsonify(status='Fail', msg=msg, data=data)

    def get_json(self, name):
        return request.get_json(force=True, silent=True)

    def get(self, id = None):
        if id is None:
            params = self.get_json('get')
            pageIdx = 0
            pageSize = 20
            if params and 'pageIdx' in params:
                pageIdx = params.pageIdx
            if params and 'pageSize' in params:
                pageSize = params.pageSize
            sl = self.orm.select().paginate(pageIdx + 1, pageSize)
            #print(sl.sql())
            val = [u.__data__  for u in sl.execute()]
            return self.success(val)
        else:
            u = self.orm.get_or_none(self.orm.id == id)
            if u is not None:
                return self.success(u.__data__)
            return self.fail(f'Not found by ID of {id}')

    def post(self):
        params = self.get_json('post')
        if isinstance(params, list):
            r = []
            for p in params:
                u = self.orm.create(**p)
                r.append({"id": u.id})
            return self.success(r)
        elif isinstance(params, dict):
            u = self.orm.create(**params)
            return self.success({"id": u.id})
        return self.fail('post need valid json')

    def put(self, id):
        u = self.orm.get_or_none(self.orm.id == id)
        params = self.get_json('put')
        if u is None:
            return self.fail( msg = f'Not found by ID of {id}')
        for k in params:
            if hasattr(u, k):
                setattr(u, k, params[k])
        u.save()
        return self.success(None)

    def delete(self, id):
        self.orm.delete().where(self.orm.id == id).execute()
        return self.success(None)
