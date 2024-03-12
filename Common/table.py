import os, sys, re, time, json, io
import win32gui, win32con, win32api, win32clipboard
import requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Download import henxin
from Common import base_win, dialog

class CellEditor(base_win.Editor):
    def __init__(self) -> None:
        super().__init__()
        self.css['borderColor'] = 0x2faffff
        self.row = 0
        self.col = 0
        self.inEdit = False

# headers = [ {..., editable: True | False(default)}, ... ]
# listeners = 'CellChanged' = {src, row, col, data(is row data), header, model}
#             'ClickCell' = {src, row, col, data(is row data), header, model}
class ExTableWindow(base_win.TableWindow):
    def __init__(self) -> None:
        super().__init__()
        self.editor = CellEditor()
        self.editor.addListener(self.onPressEnter)

    def beginEdit(self, row, col):
        if row < 0 or col < 0:
            return
        self.editor.inEdit = True
        self.editor.row = row
        self.editor.col = col
        sx = self.getColumnX(col)
        sy = self.getYOfRow(row)
        cw = self.getColumnWidth(col)
        ch = self.rowHeight
        if not self.editor.hwnd:
            self.editor.createWindow(self.hwnd, (0, 0, 1, 1))
        win32gui.SetWindowPos(self.editor.hwnd, 0, sx, sy, cw, ch, win32con.SWP_NOZORDER)
        hd = self.headers[col]
        rowData = self.data[row]
        cellVal = rowData[hd['name']]
        if cellVal == None:
            cellVal = ''
        self.editor.setText(str(cellVal))
        W, H = self.getClientSize()
        win32gui.ShowWindow(self.editor.hwnd, win32con.SW_SHOW)
        win32gui.SetFocus(self.editor.hwnd)

    def endEdit(self):
        if not self.editor.inEdit:
            return
        self.editor.inEdit = False
        win32gui.ShowWindow(self.editor.hwnd, win32con.SW_HIDE)
        win32gui.SetFocus(self.hwnd)
        row = self.editor.row
        col = self.editor.col
        hd = self.headers[col]
        rowData = self.data[row]
        cellVal = rowData[hd['name']]
        if cellVal == self.editor.text:
            return
        rowData[hd['name']] = self.editor.text
        self.notifyListener('CellChanged', {'src': self, 'row': row, 'col': col, 'data': rowData, 'header': hd, 'model': self.data})

    def onPressEnter(self, evtName, evtInfo, args):
        if evtName == 'PressEnter':
            self.endEdit()

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDOWN:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.endEdit()
            self.onClick(x, y)
            return True
        if msg == win32con.WM_LBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            row = self.getRowAtY(y)
            col = self.getColAtX(x)
            if row < 0 or col < 0:
                return True
            dx = self.sortData if self.sortData else self.data
            self.notifyListener('ClickCell', {'src' : self, 'row': row, 'col': col, 'data' : dx[row], 'model': dx})
            return True
        if msg == win32con.WM_LBUTTONDBLCLK:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            row = self.getRowAtY(y)
            col = self.getColAtX(x)
            if row < 0 or col < 0:
                return True
            if self.headers[col].get('editable', False):
                self.beginEdit(row, col)
                return True
            if self.enableListeners['DbClick']:
                dx = self.sortData if self.sortData else self.data
                self.notifyListener('DbClick', {'src': self, 'x': x, 'y': y, 'row': row, 'data': dx[row], 'model': dx})
            return True
        return super().winProc(hwnd, msg, wParam, lParam)


if __name__ == '__main__':
    win = ExTableWindow()
    win.createWindow(None, (100, 100, 1000, 400), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    win32gui.PumpMessages()
    