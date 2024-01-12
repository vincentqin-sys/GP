import orm
import re, peewee as pw

txt = """
园林股份605303
雅博股份002323
华达新材605158 回封
清源股份603628 回封
金辰股份603396回封
大连圣亚600593回封
长白山603099
中兴商业000715 回封
双象股份002395回封
南京熊猫600775
证通电子002197
09:52
09:30
09:30
09:36
14:27
09:30
09:39
09:42
09:32
09:32
09:54
首板
2连板
2连板
首板
首板
4连板
5连板
首板
首板
首板
首板
地露产链(5)
光伏(4)
光伏(4)
光伏(4)
光伏(4)
振兴东北(3)
振兴东北(3)
振兴东北(3)
VR/AR/MR(2)
VR/AR/MR(2)
数字货币(2)
"""

def format(day):
    lines = txt.splitlines()
    codeNum = 0
    rs = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        if len(line) == 5:
            break
        m = re.match('(.*?)\s*(\d+)\s*(.*)', line)
        name, code, tag = m.groups()
        rs.append([name, code, tag])
        codeNum += 1

    lines = lines[i : ]
    if len(lines) % codeNum != 0:
        raise Exception('error')
    times = lines[0 : codeNum]
    status = lines[codeNum : codeNum * 2]
    reason = lines[codeNum * 2: codeNum * 3]
    for i, r in enumerate(rs):
        r.append(times[i])
        r.append(status[i])
        r.append(reason[i])
        r.append(day)
        print(r)
    return rs

if __name__ == '__main__':
    day = '20240108'
    rs = format(day)
    print('')
    for r in rs:
        count = orm.THS_ZT_FuPan.select(pw.fn.count(orm.THS_ZT_FuPan.code)).where(orm.THS_ZT_FuPan.code == r[1], orm.THS_ZT_FuPan.day == day)
        #print(count.sql())
        count = count.scalar()
        if not count:
            orm.THS_ZT_FuPan.create(name=r[0], code=r[1], tag=r[2], ztTime=r[3], status=r[4], ztReason=r[5], day=day)
        else:
            print('重复项：', r)