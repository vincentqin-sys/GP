import peewee as pw
from peewee import fn
import os, json, time, sys, pyautogui

sys.path.append('.')
import orm

BASE_DATA_PATH = 'D:/ths/struct/'

if not os.path.exists(BASE_DATA_PATH):
    os.makedirs(BASE_DATA_PATH)

def isCode(name):
    if not name:
        return False
    if len(name) != 6:
        return False
    for i in range(len(name)):
        if name[i] > '9' or name[i] < '0':
            return False
    return True

def listFiles():
    fs = os.listdir(BASE_DATA_PATH)
    rs = [BASE_DATA_PATH + f for f in fs if isCode(f) ]
    return rs

def loadFileData(fileName):
    data = {}
    f = open(fileName, 'r', encoding= 'utf8')
    lines = f.readlines()
    f.close()
    i = 0
    while i < len(lines) - 1:
        heads = lines[i].strip().split('\t')
        if len(heads) != 4 or len(lines[i + 1]) < 10:
            i += 1
            continue
        curTime, code, day, n = heads
        curDay, curTime = curTime.split(' ')
        curDay = curDay.replace('-', '')
        curTime = curTime[0 : 5] # hh:mm
        if curDay == day:
            if curTime < '15:00':
                i += 2
                continue
            
        js = json.loads(lines[i + 1])
        if js['code'] != 0:
            continue
        row = {'code' : code, 'day' : day}
        keys = ['activeIn', 'activeOut', 'positiveIn', 'positiveOut']
        for k in keys:
            row[k] = js['data'][k] / 100000000 # 亿
        row['total'] = row['activeIn'] + row['positiveIn'] - row['activeOut'] - row['positiveOut']
        data[day] = row
        i += 2
    
    # merge data
    rt = []
    for k, v in data.items():
        rt.append(v)
    return rt

def loadAllFileData():
    fs = listFiles()
    for f in fs:
        data = loadFileData(f)
        if len(data) <= 0:
            continue
        mergeSavedData(data)
        os.remove(f)

def getNameByCode(code):
    n = orm.THS_Newest.get_or_none(orm.THS_Newest.code == code)
    if not n:
        return ''
    return n.name

def mergeSavedData(datas):
    code = datas[0]['code']
    name = getNameByCode(code)
    maxDay = orm.THS_DDLR.select(pw.fn.Max(orm.THS_DDLR.day)).where(orm.THS_DDLR.code == code).scalar()
    if not maxDay:
        maxDay = ''
    for d in datas:
        if d['day'] > maxDay:
            d['name'] = name
            orm.THS_DDLR.create(**d)

def autoLoadTop200Data():
    time.sleep(10)
    datas = orm.THS_Hot.select().order_by(orm.THS_Hot.id.desc()).limit(200)
    datas = [d for d in datas]
    datas.reverse()
    for idx, d in enumerate(datas):
        for i in range(20):
            pyautogui.press('backspace')
            pyautogui.press('delete')
            time.sleep(0.02)
        code = f"{d.code :06d}" 
        print(f"[{idx + 1}]", code)
        pyautogui.typewrite(code, 0.1)
        pyautogui.press('enter')
        time.sleep(5)

def test():
    query = orm.THS_DDLR.select()
    for it in query:
        name = getNameByCode(it.code)
        it.name = name
        it.save()

def test2():
    import win32gui, win32con
    MAIN_WIN = 0x40468
    idx = 0
    def enumCallback(hwnd, exta):
        nonlocal idx
        title = win32gui.GetWindowText(hwnd)
        if win32gui.IsWindowVisible(hwnd):
            idx += 1
            print(f"[{idx}] hwnd = {hwnd : X}, {exta}, {title}")

    win32gui.EnumChildWindows(MAIN_WIN, enumCallback, 'WWX')

if __name__ == '__main__':
    print('自动下载Top 200大单买卖数据(同花顺Level-2)')
    print('必须打开Fiddler, Fiddler拦截onBeforeResponse, 将数据下载下来')
    print('再将同花顺的大单统计功能打开, 鼠标定位在输入框中')
    autoLoadTop200Data()
    loadAllFileData()
    # test2()
    pass