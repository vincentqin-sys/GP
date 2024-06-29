import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, re

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from db import ths_orm
from THS import ths_win
from Common import base_win, ext_win
from db import tck_orm
import kline_utils

class TopMySelWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()