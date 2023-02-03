import pyautogui as pa
import time

# 股东研究  主力持仓  行业对比
posList = [(923, 148), (923, 176), (1366, 176)];
posIdx = 0

WAIT_TIME = 3

def nextPos():
    global posIdx
    pos = posList[ posIdx % 3]
    posIdx += 1
    return pos

for i in range(4700):
    for k in range(len(posList) - 1):
        pos = nextPos()
        pa.moveTo(pos[0], pos[1])
        pa.click()
        time.sleep(WAIT_TIME)
    
    #下一个
    pa.moveTo(1183, 113)
    pa.click()
    time.sleep(WAIT_TIME)