import socket
import subprocess
import sys

class FaceServer():
    def __init__(self, ALLOWED_CONNECTIONS=7):
        ### Global variables
        self.PORT = 12345
        self.ALLOWED_CONNECTIONS = ALLOWED_CONNECTIONS
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        hostname = socket.gethostname()    
        self.IPAddr = socket.gethostbyname(hostname)
        print('#'*30)
        print('Server IP is: ', self.IPAddr)
        print('#'*30)
        self.sock.bind((self.IPAddr, self.PORT))
        
    def get_subsocket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        for port in range(12346,12346+self.ALLOWED_CONNECTIONS):
            try:
                sock.bind((self.IPAddr, port))
                sock.close()
                return port
            except OSError:
                continue
        return None
    
    def start_main_server(self):
        self.sock.listen()
        while True:
            print("Main server: Listening for new connections")
            client, addr = self.sock.accept()
            subport = self.get_subsocket()
            
            if subport is None:
                msg = 'OVERLOAD'
                print(msg)
                client.send(msg.encode());client.close()
                continue
            
            client.send(bytes(str(subport), 'utf-8'))
            client.settimeout(1)
            try:
                isOK = client.recv(32).decode()
            except socket.timeout:
                print("Main server: No responce from client. Reset")
                continue
            if isOK=='OK':
                client.close()
                pid = subprocess.Popen(['python','SubServer.py',str(subport),addr[0]])
                print("Main server: redirected to port:",subport)
            else:
                print("Main server: Failed to redirect client")
                continue
                
                
#########################################
server = FaceServer()
server.start_main_server()
