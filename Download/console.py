import os, sys

os.system('') # fix win10 下console 颜色不生效bug

BLACK, RED, GREEN, YELLOW, BLUE, PURPLE, CYAN, WHITE = 0, 1, 2, 3, 4, 5, 6, 7
# PURPLE = 5 # 紫色
# CYAN = 6 # 青
F_CLOSE = 0 # 关闭所有格式，还原为初始状态
F_BOLD = 1 # 高亮显示
F_OBSCURE = 2 # 模糊
F_ITALIC = 3  # 斜体
F_UNDERLINE = 4 # 下划线
F_SLOW_FLASH = 5 # 闪烁（慢)
F_FAST_FLASH = 6 # 闪烁（快)
F_EXCHANGE = 7 # 交换背景色与前景色
F_HIDE = 8 # 隐藏

def write_1(color, *args):
    print(f'\033[{30 + color}m', *args, '\033[0m', end='')

def writeln_1(color, *args):
    print(f'\033[{30 + color}m', *args, '\033[0m')

def writeln_2(color, bgColor, *args):
    print(f'\033[{30 + color};{40 + bgColor}m', *args, '\033[0m')

def write_2(color, bgColor, *args):
    print(f'\033[{30 + color};{40 + bgColor}m', *args, '\033[0m', end='')    

def writeln_3(font, color, bgColor, *args):
    print(f'\033[{font};{30 + color};{40 + bgColor}m', *args, '\033[0m')

def write_3(font, color, bgColor, *args):
    print(f'\033[{font};{30 + color};{40 + bgColor}m', *args, '\033[0m', end='')

#Console.write2( Console.YELLOW, Console.BLACK, 'Hello', 'World AA')
#Console.write3(Console.F_HIDE, Console.RED, Console.BLACK, 'Hello', 'World BB')
