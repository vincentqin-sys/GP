import requests, os, sys

cwd = os.getcwd()
w = cwd.index('GP')
cwd = cwd[0 : w + 2]
sys.path.append(cwd)
from THS import orm
from THS.download import henxin

hexin = henxin.HexinUrl()

def loadCode(code):
    url = hexin.getKLineUrl(code)
    ps = hexin.loadUrlData(url)
    name = ps['name']
    data = ps['data']
    

def main():
    qs = orm.THS_ZS.select()
    codes = [c.code for c in qs]
    

if __name__ == '__main__':
    main()
