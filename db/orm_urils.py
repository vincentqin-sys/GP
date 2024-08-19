# move table from a database to another database
def move_table_data(fromDb, modelClass : pw.Model):
    cols = [] # (field.name, column_name)
    for k in modelClass._meta.columns:
        field = modelClass._meta.columns[k]
        if k == 'id':
            continue
        cols.append((k, field.column_name))
    #print(cols)
    # build query select sql
    c = map(lambda x: x[1], cols)
    sql = 'select ' + ', '.join(c) + ' from ' + modelClass._meta.table_name
    cc = fromDb.cursor()
    cc.execute(sql)
    rs = cc.fetchall()
    for row in rs:
        params = {}
        for i, c in enumerate(cols):
            params[c[0]] = row[i]
        print(params)
        modelClass.create(**params)
    rs = modelClass.select()
    for r in rs:
        print(r.__data__)

#move_table_data(db_tck, TCK_TCGN)