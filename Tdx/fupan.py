import sys
import peewee as pw
from data_parser import *
from orm import *

class FuPan:
    db = None

    def __init__(self):
        pass

    # return {days:[], data:[ [one-day-top10], ... ]}
    def calcTop10VolOfBk(self, codes, daysNum):
        TOP_NUM = 10
        rs = []
        gplist = [ DataFile(code, DataFile.DT_DAY) for code in codes ]
        for i in range(daysNum, 0, -1):
            gp = sorted(gplist, key = lambda x : x.data[-i].money, reverse=True)
            m = 0
            for x in gp[0 : TOP_NUM]: m += x.data[-i].money
            day = gp[0].data[-i].day
            rs.append((day, m / 100000000))
        return rs

    def calcVolOrder(self):
        pass


"""
rx = ''; trs = $('.iwc-table-fixed table tr'); for (i =0; i <= trs.length; i++) {let cc = trs.eq(i).find('td:eq(2)'); if (cc.text()) rx += cc.text() + ','; }; console.log(rx)
"""

汽车整车 = '301039,000572,000800,601777,600066,600841,600303,600213,000951,601633,000868,600375,600686,600104,000980,600006,000957,601238,600166,000550,000625,002594,600733,601127,600418'


if __name__ == '__main__':
    # fp = FuPan()
    # rs = fp.calcTop10VolOfBk(汽车整车.split(','), 15)
    #for r in rs: print(r[0], int(r[1]), sep='\t')
    pass

