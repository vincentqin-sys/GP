import requests, os, sys

cwd = os.getcwd()
w = cwd.index('GP')
cwd = cwd[0 : w + 2]
sys.path.append(cwd)
from THS import orm
from THS.download import henxin

DEST_ZS_DIR = r'D:\ThsData\zs'

hexin = henxin.HexinUrl()

def loadCode(code):
    url = hexin.getKLineUrl(code)
    ps = hexin.loadUrlData(url)
    name = ps['name']
    data = ps['data']
    f = open(os.path.join(DEST_ZS_DIR, code), 'w')
    f.write()
    f.close()
    

def main():
    qs = orm.THS_ZS.select()
    codes = [c.code for c in qs]
    for c in codes:
        loadCode(c)

if __name__ == '__main__':
    main()
