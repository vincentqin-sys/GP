import socket, sys, traceback, time
from concurrent.futures import ThreadPoolExecutor
import winreg, ctypes


MAX_CONNECTION = 1
BUFFER_SIZE = 4096
LISTENING_PORT = 9900

pools = None

# http=127.0.0.1:8888;https=127.0.0.1:8888
def set_system_proxy(enable):
    hkey = winreg.CreateKey(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings')
    ps = f'127.0.0.1:{LISTENING_PORT}' if enable else ''
    winreg.SetValueEx(hkey, 'ProxyServer', 0, winreg.REG_SZ, ps)
    pe = 1 if enable else 0
    winreg.SetValueEx(hkey, 'ProxyOverride', 0, winreg.REG_SZ, '<-loopback>')
    winreg.SetValueEx(hkey, 'ProxyEnable', 0, winreg.REG_DWORD, pe) # enable proxy ?
    winreg.CloseKey(hkey)
    res = ctypes.windll.Wininet.InternetSetOptionW(0, 37, 0, 0) # 37 = INTERNET_OPTION_REFRESH
    res2 = ctypes.windll.Wininet.InternetSetOptionW(0, 39, 0, 0) # 39 = INTERNET_OPTION_SETTINGS_CHANGED
    print(f'set_system_proxy {"success" if res and res2 else "fail"}')

def start():    #Main Program
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', LISTENING_PORT))
        sock.listen(MAX_CONNECTION)
        print("[*] Server started successfully, port [ %d ]" % LISTENING_PORT)
        #print('[Press Ctrl + C to stop server]')
    except Exception as e:
        print("[*] Unable to Initialize Socket")
        print(e)
        sys.exit(2)

    global pools
    pools = ThreadPoolExecutor(max_workers = MAX_CONNECTION, thread_name_prefix = 'worker-')
    set_system_proxy(True)

    while True:
        try:
            conn, addr = sock.accept() #Accept connection from client browser
            #pools.submit(conn_string, conn, data, addr) #Starting a thread
            proxy(conn, addr)
        except KeyboardInterrupt:
            sock.close()
            print("\n[*] Graceful Shutdown")
            set_system_proxy(False)
            pools.shutdown(False)
            sys.exit(1)

def proxy(clientConn, clientAddr):
    try:
        reqData = clientConn.recv(BUFFER_SIZE) #Recieve client request data
        first_line = reqData.split(b'\n')[0]
        first_line = first_line.split(b' ')
        method = first_line[0]
        url = first_line[1]
        print('\n')
        print('reqData=', reqData)
        print(f'url=[{url}]')
        print(f'method=[{method}]')
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
            webserver = temp[: webserver_pos]
        else:
            port = int((temp[(port_pos+1):])[:webserver_pos-port_pos-1])
            webserver = temp[:port_pos]
        # print(data)
        proxy_server(method, webserver, port, clientConn, clientAddr, reqData)
    except Exception as e:
        print('Exception: ', e)
        traceback.print_exc()
        pass

def do_connect(clientConn, serverConn):
    print('do connect')
    clientConn.send(b'HTTP/1.1 200 Connection Established\r\n\r\n')
    # request: client send to server
    while True:
        data = clientConn.recv(BUFFER_SIZE)
        print('client data: ', data)
        if not data:
            break
        serverConn.send(data)
    # response: server send to client
    print('========')
    while True:
        data = serverConn.recv(BUFFER_SIZE)
        print('server data: ', data)
        if not data:
            break
        clientConn.send(data)
    clientConn.close()
    serverConn.close()
    print('do connect END')

def proxy_server(method, webserver, port, clientConn, clientAddr, data):
    try:
        # print(data)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((webserver, port))
        if method == b'CONNECT':
            do_connect(clientConn, sock)
            return
        while True:
            reply = sock.recv(BUFFER_SIZE)
            if(len(reply) > 0):
                clientConn.send(reply)
                print('reply=', reply)
            else:
                break
        sock.close()
        clientConn.close()
    except socket.error:
        sock.close()
        clientConn.close()
        # sys.exit(1)

def fillter(webserver, url):
    pass

if __name__== "__main__":
    print('Clear system proxy')
    set_system_proxy(False)
    input('Press Enter to start Server')
    start()