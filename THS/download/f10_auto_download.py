import pyautogui as pa
import time

# 最新动态 股东研究  主力持仓
class Download_3:
    def __init__(self) -> None:
        self.posList = [(700, 150), (923, 148), (923, 176)]
        self.posIdx = 0
        self.WAIT_TIME = 1.5

    def nextPos(self):
        pos = self.posList[ self.posIdx % 3]
        self.posIdx += 1
        return pos

    #下一个
    def clickNext(self):
        pa.moveTo(1183, 113)
        pa.click()
        time.sleep(self.WAIT_TIME)

    def download(self, num = 4900):
        for i in range(num):
            for k in range(len(self.posList) - 1):
                pos = self.nextPos()
                pa.moveTo(pos[0], pos[1])
                pa.click()
                time.sleep(self.WAIT_TIME)

#下载所有的行业对比
class Download_HYDB:
    def download(self):
        codes = ['000166', '000004', '000034', '000002', '000031', '600082', '000417', '000056', '601888', '000829', '001209', '002634', '002293', '000030', '000572', '000868', '000550', '000055', '000401', '002372', '002066', '000012', '002094', '300896', '000523', '000560', '000060', '000630', '000612', '002115', '000617', '601318', '002807', '001227', '000001', '601288', '002022', '002382', '002223', '000028', '001211', '000910', '001222', '000017', '001323', '000726', '000955', '002003', '600448', '000639', '000716', '001318', '002495', '000529', '002689', '000856', '002209', '000852', '002890', '000157', '002722', '000010', '000779', '000032', '000498', '000628', '000881', '002211', '002562', '002615', '002326', '000902', '002054', '002037', '000408', '000565', '000553', '000422', '000731', '002717', '000035', '000544', '002549', '000890', '000096', '000698', '002093', '002280', '000504', '002821', '002035', '002403', '002584', '001223', '000988', '001266', '002527', '000762', '000831', '000657', '000506', '603612', '000547', '600072', '000519', '000638', '002829', '000025', '000681', '002174', '000607', '000802', '000719', '000156', '000721', '000428', '000524', '000430', '600706', '000151', '000906', '000875', '000040', '001210', '000601', '000027', '000423', '000153', '000756', '000659', '000695', '000488', '000729', '000568', '000848', '000869', '000801', '000016', '000404', '000333', '000521', '000066', '300183', '002017', '000070', '000063', '000757', '000913', '000008', '002045', '000021', '000062', '001373', '000541', '000020', '002371', '002077', '300456', '002049', '000636', '000823', '002119', '002079', '002227', '000009', '002202', '000821', '000720', '000533', '000400', '000922', '002058', '000039', '001696', '000530', '002046', '000410', '000795', '000633', '000629', '000708', '000709', '000859', '001255', '001207', '002224', '002768', '002108', '000949', '000782', '000420', '000301', '000723', '000552']    
        for c in codes:
            pa.typewrite(c, interval = 0.25)
            pa.press("enter")
            time.sleep(2.5)

if __name__ == '__main__':
    print('必须先打开fiddler')
    time.sleep(5)
    # Download_HYDB().download()
    # Download_3().download()