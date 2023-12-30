import basewin

class KLineModel:
    def __init__(self) -> None:
        pass

    def loadCode(code):
        pass

class KLineWindow(basewin.BaseWindow):

    def __init__(self):
        super().__init__()
        self.model = KLineModel()

    # @return True: 已处理事件,  False:未处理事件
    def winProc(hwnd, msg, wParam, lParam):
        return False

