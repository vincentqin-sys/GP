import time, os, threading, datetime
import json, os, sys

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Server import cls_server, ths_server, lhb_server

thsServer = ths_server.Server()
clsServer = cls_server.Server()
lhbServer = lhb_server.Server()

def runner():
    while True:
        thsServer.loadHotsOneTime()
        time.sleep(10)

def loop():
    lastDay = None
    while True:
        td = datetime.datetime.today()
        if lastDay != td:
            lastDay = td
            print('---------------->', lastDay.strftime('%Y-%m-%d'), '<----------------')
        thsServer.loadOneTime()
        clsServer.loadOneTime()
        lhbServer.loadOneTime()
        time.sleep(10)

if __name__ == '__main__':
    th = threading.Thread(target = runner, daemon = True)
    th.start()
    loop()