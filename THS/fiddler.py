import socket, sys, traceback, time
from concurrent.futures import ThreadPoolExecutor
import winreg, ctypes


MAX_CONNECTION = 5
BUFFER_SIZE = 4096
LISTENING_PORT = 9900

pools = None

# http=127.0.0.1:8888;https=127.0.0.1:8888
def set_system_proxy(enable):
    hkey = winreg.CreateKey(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings')
    ps = f'http=127.0.0.1:{LISTENING_PORT}' if enable else ''
    winreg.SetValueEx(hkey, 'ProxyServer', 0, winreg.REG_SZ, ps)
    pe = 1 if enable else 0
    winreg.SetValueEx(hkey, 'ProxyEnable', 0, winreg.REG_DWORD, pe) # enable proxy ?
    winreg.CloseKey(hkey)
    res = ctypes.windll.Wininet.InternetSetOptionW(0, 37, 0, 0) # 37 = INTERNET_OPTION_REFRESH
    res2 = ctypes.windll.Wininet.InternetSetOptionW(0, 39, 0, 0) # 39 = INTERNET_OPTION_SETTINGS_CHANGED
    print('res=', res, 'res2=', res2)

LPWSTR = ctypes.POINTER(ctypes.wintypes.WCHAR)
HINTERNET = ctypes.wintypes.LPVOID
#"""
class INTERNET_PER_CONN_OPTION(ctypes.Structure):
    class Value(ctypes.Union):
        _fields_ = [
            ('dwValue', ctypes.wintypes.DWORD),
            ('pszValue', LPWSTR),
            ('ftValue', ctypes.wintypes.FILETIME),
        ]
    _fields_ = [
        ('dwOption', ctypes.wintypes.DWORD),
        ('Value', Value),
    ]

class INTERNET_PER_CONN_OPTION_LIST(ctypes.Structure):
    _fields_ = [
        ('dwSize', ctypes.wintypes.DWORD),
        ('pszConnection', LPWSTR),
        ('dwOptionCount', ctypes.wintypes.DWORD),
        ('dwOptionError', ctypes.wintypes.DWORD),
        ('pOptions', ctypes.POINTER(INTERNET_PER_CONN_OPTION)),
    ]

InternetSetOption = ctypes.windll.wininet.InternetSetOptionW
InternetSetOption.argtypes = [HINTERNET, ctypes.wintypes.DWORD, ctypes.wintypes.LPVOID, ctypes.wintypes.DWORD]
InternetSetOption.restype  = ctypes.wintypes.BOOL

def sys_proxy():
    INTERNET_PER_CONN_FLAGS = 1
    INTERNET_PER_CONN_AUTOCONFIG_URL = 4
    INTERNET_PER_CONN_AUTODISCOVERY_FLAGS = 5
    INTERNET_OPTION_REFRESH = 37
    INTERNET_OPTION_SETTINGS_CHANGED = 39
    INTERNET_OPTION_PER_CONNECTION_OPTION = 75
    PROXY_TYPE_AUTO_PROXY_URL = 4

    proxy = ctypes.create_unicode_buffer(f'http://127.0.0.1:{LISTENING_PORT}/proxy.pac')
    ls = INTERNET_PER_CONN_OPTION_LIST()
    opts = (INTERNET_PER_CONN_OPTION * 2)()
    nSize = ctypes.c_ulong(ctypes.sizeof(INTERNET_PER_CONN_OPTION_LIST))

    opts[0].dwOption = INTERNET_PER_CONN_AUTOCONFIG_URL
    opts[0].Value.pszValue = proxy
    opts[1].dwOption = INTERNET_PER_CONN_FLAGS
    opts[1].Value.dwValue = PROXY_TYPE_AUTO_PROXY_URL

    ls.dwSize = ctypes.sizeof(INTERNET_PER_CONN_OPTION_LIST)
    ls.pszConnection = None
    ls.dwOptionCount = 2
    ls.dwOptionError = 0
    ls.pOptions = opts

    assert InternetSetOption(None, INTERNET_OPTION_PER_CONNECTION_OPTION, ctypes.byref(ls), nSize) == True
    assert InternetSetOption(None, INTERNET_OPTION_SETTINGS_CHANGED, None, 0) == True
    assert InternetSetOption(None, INTERNET_OPTION_REFRESH, None, 0) == True
#"""

def start():    #Main Program
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', LISTENING_PORT))
        sock.listen(MAX_CONNECTION)
        print("[*] Server started successfully, port [ %d ]" %LISTENING_PORT)
        print('[Press Ctrl + C to stop server]')
    except Exception as e:
        print("[*] Unable to Initialize Socket")
        print(e)
        sys.exit(2)

    global pools
    pools = ThreadPoolExecutor(max_workers = MAX_CONNECTION)
    #set_system_proxy(True)

    while True:
        try:
            conn, addr = sock.accept() #Accept connection from client browser
            data = conn.recv(BUFFER_SIZE) #Recieve client data
            print('data=', data)
            pools.submit(conn_string, (conn, data, addr)) #Starting a thread
        except KeyboardInterrupt:
            sock.close()
            print("\n[*] Graceful Shutdown")
            set_system_proxy(False)
            pools.shutdown(False)
            sys.exit(1)

def conn_string(conn, data, addr):
    try:
        print(data)
        first_line = data.split(b'\n')[0]
        url = first_line.split(' ')[1]
        print('url=', url)
        http_pos = url.find(b'://') #Finding the position of ://
        if(http_pos == -1):
            temp = url
        else:
            temp = url[(http_pos + 3) : ]
        port_pos = temp.find(b':')
        webserver_pos = temp.find(b'/')
        if webserver_pos == -1:
            webserver_pos = len(temp)
        webserver = ""
        port = -1
        if(port_pos == -1 or webserver_pos < port_pos):
            port = 80
            webserver = temp[:webserver_pos]
        else:
            port = int((temp[(port_pos+1):])[:webserver_pos-port_pos-1])
            webserver = temp[:port_pos]
        # print(data)
        proxy_server(webserver, port, conn, addr, data)
    except Exception:
        pass

def proxy_server(webserver, port, clientConn, clientAddr, data):
    try:
        # print(data)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((webserver, port))
        sock.send(data)
        while True:
            reply = sock.recv(BUFFER_SIZE)
            if(len(reply) > 0):
                clientConn.send(reply)
            else:
                break
        sock.close()
        clientConn.close()
    except socket.error:
        sock.close()
        clientConn.close()
        print(sock.error)
        # sys.exit(1)

def fillter(webserver, url):
    pass

if __name__== "__main__":
    print('Cleared system proxy')
    #set_system_proxy(False)
    #set_system_proxy(True)
    sys_proxy()
    input('Press Enter to start Server')
    start()