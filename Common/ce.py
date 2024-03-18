import win32gui, win32con , win32api, win32ui, win32gui_struct, win32clipboard # pip install pywin32
import threading, time, datetime, sys, os, copy, calendar, functools
import traceback, io

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Common import base_win
from Common.base_win import MutiEditor

class CodeEditor(MutiEditor):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0xfdfdfd
        self.paddingX = 40
        self.KEYS = ('def', 'None', 'False', 'True', 'and', 'or', 
                    'break', 'class', 'continue', 'del', 'if', 'elif', 'else',
                    'for', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 
                    'pass', 'return', 'while', 'super')
        self.DEF_FUNCS = ('print', 'range' )
        self.COLORS = {
            'KEY': 0xff7700, 'DEF_FUNC': 0x900090, 'STR': 0x808080
        }
        self.excInfo = None # {lineno, exc, }

    def insertText(self, text):
        if text:
            text = text.replace('\t', '    ')
        return super().insertText(text)

    def updateRowText(self, row, text):
        super().updateRowText(row, text)
        if self.excInfo and self.excInfo['lineno'] == row + 1:
            self.excInfo = None

    def drawRow(self, hdc, row, rc):
        if self.excInfo and self.excInfo['lineno'] == row + 1:
            self.drawer.drawRect(hdc, rc, 0x0000ff)
            pass
        self.drawer.drawText(hdc, self.lines[row]['text'], rc, color = self.css['textColor'], align = win32con.DT_LEFT | win32con.DT_SINGLELINE | win32con.DT_VCENTER)
        tokens = self.lines[row]['tokens']
        for tk in tokens:
            irc = (rc[0] + tk['sx'], rc[1], rc[0] + tk['ex'], rc[3])
            self.drawer.drawText(hdc, tk['name'], irc, color = self.COLORS[tk['type']], align = win32con.DT_LEFT | win32con.DT_SINGLELINE | win32con.DT_VCENTER)

    def participles(self, txt):
        #isalpha = lambda ch : (ch >= 'A' and ch <= 'Z') or (ch >= 'a' and ch <= 'z')
        tokens = []
        if not txt:
            return tokens
        b = -1
        for i in range(len(txt) + 1):
            if i == len(txt):
                ch = ' '
            else:
                ch = txt[i]
            if (ch >= 'A' and ch <= 'Z') or (ch >= 'a' and ch <= 'z'):
                if b == -1:
                    b = i
                continue
            if b == -1:
                continue
            # is not alpha
            tk = txt[b : i]
            if tk in self.KEYS:
                tokens.append({'type' : 'KEY', 'name': tk, 'b': b, 'e': i}) # type = KEY | DEF_FUNC | STR
            elif tk in self.DEF_FUNCS:
                tokens.append({'type' : 'DEF_FUNC', 'name': tk, 'b': b, 'e': i}) # type = KEY | DEF_FUNC | STR
            b = -1
        # find strs
        b = -1
        dsq_1 = 0
        for i in range(len(txt)):
            ch = txt[i]
            if ch != "'" and ch != '"':
                continue
            dsq = 1 if ch == "'" else 2
            if b == -1:
                b = i
                dsq_1 = dsq
            else:
                if dsq_1 == dsq:
                    tk = txt[b : i + 1]
                    tokens.append({'type' : 'STR', 'name': tk, 'b': b, 'e': i + 1}) # type = KEY | DEF_FUNC | STR
                    b = -1
                    dsq_1 = 0
        return tokens

    def beautiful(self, row, hdc):
        nd = self.lines[row].get('modified', True)
        if not nd:
            return
        self.lines[row]['modified'] = False
        tokens = self.participles(self.lines[row]['text'])
        self.lines[row]['tokens'] = tokens
        line = self.lines[row]['text']
        for tk in tokens:
            pre = line[0 : tk['b']]
            scw, *_ = win32gui.GetTextExtentPoint32(hdc, pre)
            pre = line[0 : tk['e']]
            ecw, *_ = win32gui.GetTextExtentPoint32(hdc, pre)
            tk['sx'] = scw
            tk['ex'] = ecw

    def drawLineNo(self, hdc):
        _, H = self.getClientSize()
        w = self.paddingX - 5
        rc = (0, 0, w, H)
        self.drawer.fillRect(hdc, rc, 0xdddddd)
        for i in range(self.startRow, len(self.lines)):
            hd = f'{i + 1}'
            sy = self.getYAtPos(MutiEditor.Pos(i, 0))
            self.drawer.drawText(hdc, hd, (0, sy, w - 10, sy + self.lineHeight), color = 0x908070, align = win32con.DT_RIGHT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

    def onDraw(self, hdc):
        for r in range(len(self.lines)):
            self.beautiful(r, hdc)
        super().onDraw(hdc)
        self.drawLineNo(hdc)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_KEYDOWN and wParam == win32con.VK_F5:
            self.notifyListener('Run', {'src': self, 'code': self.getText()})
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class Console(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.infos = [] # item of {text, color}
        self.lineHeight = 24
        self.css['fontSize'] = 18
        self.startRow = 0
        self.stdout = None
        self.stdin = None
        self.myout = io.StringIO()

    def redirect(self):
        self.clear()
        self.stdout = sys.stdout
        self.stdin = sys.stdin
        sys.stdout = self
        sys.stdin = self

    def restore(self):
        sys.stdout = self.stdout
        sys.stdin = self.stdin

    def write(self, msg : str):
        if msg == None:
            msg = 'None'
        if not isinstance(msg, str):
            msg = str(msg)
        for ch in msg:
            self.addChar(ch)

    def flush(self):
        pass

    def __addInfo(self, info, color):
        if not info:
            return
        lns = info.splitlines()
        for ln in lns:
            self.infos.append({'text': ln, 'color': color})

    def newRow(self):
        self.infos.append({'text': '', 'color': 0x202020})

    def addChar(self, ch):
        if not self.infos:
            self.newRow()
        if ch == '\n':
            self.newRow()
        else:
            self.infos[-1]['text'] += ch
    
    def clear(self):
        self.startRow = 0
        self.infos.clear()
        self.invalidWindow()

    def addLog(self, log):
        if not log:
            return
        self.__addInfo(log, 0x202020)
        self.invalidWindow()
    
    def addException(self, log):
        if not log:
            return
        self.__addInfo(log, 0x2020f0)
        self.invalidWindow()
    
    def onDraw(self, hdc):
        W, H = self.getClientSize()
        sy = 0
        for r in range(self.startRow, len(self.infos)):
            info = self.infos[r]
            rc = (5, sy, W, sy + self.lineHeight)
            self.drawer.drawText(hdc, info['text'], rc, color = info['color'], align = win32con.DT_VCENTER | win32con.DT_LEFT | win32con.DT_SINGLELINE)
            sy += self.lineHeight

def formatException(ex):
    exs : list = ex.splitlines()
    exs.reverse()
    TAG = '  File "<string>", line '
    rs = []
    for n in exs:
        if n.startswith(TAG):
            rs.append(n)
            break
        rs.append(n)
    rs.reverse()
    line = rs[0].split(',')
    ln = line[1].replace('line ', '')
    lineno = int(ln)
    txt = '\n'.join(rs)
    return {'lineno': lineno, 'exc' : txt}

def runCode_(code, editor : CodeEditor, console : Console):
    console.clear()
    editor.excInfo = None
    editor.invalidWindow()
    console.redirect()
    try:
        exec(code, {}, {})
    except Exception as e:
        #excName, excVal, exc_traceback = sys.exc_info()
        ex = traceback.format_exc()
        exc = formatException(ex)
        editor.excInfo = exc
        editor.invalidWindow()
        console.addException(exc['exc'])
    console.restore()

def runCode(evtName, evt, console):
    if evtName != 'Run':
        return
    base_win.ThreadPool.addTask('run', runCode_, evt['code'], evt['src'], console)
    base_win.ThreadPool.start()

if __name__ == '__main__':
    label = base_win.Label()
    label.css['bgColor'] = 0x505050
    label.createWindow(None, (150, 0, 1000, 700), win32con.WS_OVERLAPPEDWINDOW  | win32con.WS_VISIBLE, title='高绾卿')
    editor = CodeEditor()
    editor.createWindow(label.hwnd, (0, 0, 1, 1))
    console = Console()
    console.css['bgColor'] = 0xdddddd
    console.createWindow(label.hwnd, (0, 0, 1, 1))
    editor.addListener(runCode, console)

    layout = base_win.GridLayout(('3fr', '1fr'), ('100%', ), (5, 5))
    layout.setContent(0, 0, editor)
    layout.setContent(1, 0, console)
    W, H = label.getClientSize()
    layout.resize(0, 0, W, H)
    win32gui.PumpMessages()
