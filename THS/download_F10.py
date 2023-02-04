import pyautogui as pa
import time

# 最新动态 股东研究  主力持仓  行业对比
posList = [(700, 150), (923, 148), (923, 176), (1366, 176)];
posIdx = 0

WAIT_TIME = 1.5

def nextPos():
    global posIdx
    pos = posList[ posIdx % 3]
    posIdx += 1
    return pos

#下一个
def clickNext():
    pa.moveTo(1183, 113)
    pa.click()
    time.sleep(WAIT_TIME)

def downloadFull(num = 4900):
    for i in range(num):
        for k in range(len(posList) - 1):
            pos = nextPos()
            pa.moveTo(pos[0], pos[1])
            pa.click()
            time.sleep(WAIT_TIME)
    
    
for i in range(4400):
    time.sleep(WAIT_TIME)
    print(i)
    clickNext()