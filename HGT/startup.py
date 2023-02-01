import time, threading, datetime
from multiprocessing import Process, Pipe

import fetch_hgt
import fetch_hgt_acc



def main():
    print(f'Start up HGT ')
    fetch_hgt.main(True)
    fetch_hgt_acc.main(True)
    while True:
        hour = datetime.datetime.now().hour
        if  hour < 8 and hour >= 7:
            fetch_hgt.main(True)
            fetch_hgt_acc.main(True)
        time.sleep(20 * 60)

if __name__ == '__main__':    
    main()