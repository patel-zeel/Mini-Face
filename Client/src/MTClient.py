import socket
import os
from pprint import pprint

import sys
import msvcrt

def getpass():
    password = ''
    while True:
        x = msvcrt.getch()
        if x == '\r':
            break
        sys.stdout.write('*')
        password +=x

    return password

PORT = 12345
ADDRESS = '172.23.240.1'
LOGGED_IN = False

def enc(data):
    return str(data).encode()

def dec(data):
    return data.decode()

def init_connection():
    global sock
    try:
        sock.connect((ADDRESS, PORT))
        print('Client: Connected to main server....', ADDRESS, PORT)
    except ConnectionRefusedError:
        print("Client: Server is not up")
        return
#     try:
#         data = sock.recv(1024).decode()
#         subport = int(data)
#         sock.send(bytes("OK",'utf-8'))
#     except ValueError:
#         if data=="OVERLOAD":
#             print('Client: Server is overloaded. Try again after a while')
#     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     sock.connect((ADDRESS, subport))
#     print("Client: Connected to sub surver on port:", subport)
    call_l1(sock)
    return

# def sync_chat(USERNAME, sock):
#     sock.settimeout(300)
#     sock.send(enc('INIT_SYNC'))
#     isOK = dec(sock.recv(32))
#     if isOK == 'OK':
#         if not os.path.exists('./local_data/'+USERNAME):
#             sock.send(enc('BEGIN'))
#             isOK = dec(sock.recv(32))
#             if isOK == 'OK':
                
#     else:
#         print('Invalid response from server. Sync terminated.')
#         f_level(sock, 2)

def create_new_account(sock):
    sock.settimeout(300)
    sock.send(enc('SIGN_UP'))
    isOK = dec(sock.recv(32))
    if isOK=='OK':
        isValid = 'NO'
        while isValid != 'YES':
            USERNAME=input('Enter Unique UserName: ')
            sock.send(enc(USERNAME))
            isValid = dec(sock.recv(32))
        isValid = 'NO'
        while isValid != 'YES':
            PASSWORD=getpass('Enter password longer than 8 characters: ')
            sock.send(enc(PASSWORD))
            isValid = dec(sock.recv(32))
        print("Client: SIGN UP SUCCESSFULL")
        
        return call_l1(sock)

def log_in(sock):
    global LOGGED_IN
    sock.settimeout(300)
    sock.send(enc('LOG_IN'))
    isOK = dec(sock.recv(32))    
    if isOK=='OK':
        isValid = 'NO'
        while isValid != 'YES':
            USERNAME=input('Enter Unique UserName: ')
            sock.send(enc(USERNAME))
            isValid = dec(sock.recv(32))
        isValid = 'NO'
        while isValid != 'YES':
            PASSWORD=input('Enter password longer than 8 characters: ')
            sock.send(enc(PASSWORD))
            isValid = dec(sock.recv(32))
        print("Client: LOG IN SUCCESSFULL")
        LOGGED_IN = True
        return f_level(sock, 2)

def log_out(sock):
    sock.settimeout(300)
    sock.send(enc('LOG_OUT'))
    isOK = dec(sock.recv(32))    
    if isOK=='OK':
        print("Client: LOG OUT SUCCESSFULL")
        return f_level(sock, 1)
    else:
        print('Invalid response from server')

def post_timeline(sock):
    sock.settimeout(300)
    sock.send(enc('POST'))
    isOK = dec(sock.recv(32))
    if isOK=='OK':
        status = input('Enter your status: ')
        sock.send(enc(status))
        isUpdated = dec(sock.recv(32))
        if isUpdated=='YES':
            print("Client: Status updated")
            return f_level(sock, 2)

def get_feed(sock):
    pass

def search_usr(sock):
    sock.settimeout(300)
    sock.send(enc('SRCH'))
    N = int(dec(sock.recv(32))) # We assume N won't be zero
    print('\n\n')
    print('###############################################################')
    print('########## USERS')
    print('###############################################################\n')
    for usr in range(N):
        sock.send(enc('OK'))
        usrname = dec(sock.recv(64))
        print(usrname)
    f_level(sock, 3)

def chk_timeline(sock):
    sock.settimeout(300)
    sock.send(enc('CHKTIM'))
    N = int(dec(sock.recv(32)))
    print('\n\n')
    print('###############################################################')
    print('########## TIMELINE')
    print('###############################################################\n')
    if N==0:
        print("----Empty Timeline----")
        return f_level(sock, 2)
    for status in range(N):
        sock.send(enc('OK'))
        print(dec(sock.recv(1024)))
    return f_level(sock, 2)

############################## Friendship ##############################
def add_frnd(sock):
    sock.settimeout(300)
    sock.send(enc('ADDFRND'))
    isOK = dec(sock.recv(32))
    if isOK:
        query = input("Enter username of your future friend: ")
        sock.send(enc(query))
        resp = dec(sock.recv(64))
        if resp == 'ISFRND':
            print(query,'is already your friend')
        elif resp == 'OKAY':
            print('Friend request sent to',query)
        elif resp == 'NULL':
            print('No user found with name', query)
        else:
            print('Invalid response from server')
        return f_level(sock, 2)

def dlt_frnd(sock):
    sock.settimeout(300)
    sock.send(enc('DLTFRND'))
    isOK = dec(sock.recv(32))
    if isOK:
        query = input("Enter username of your past friend: ")
        sock.send(enc(query))
        resp = dec(sock.recv(64))
        if resp == 'ISNOTFRND':
            print(query,'is not your friend')
        elif resp == 'OKAY':
            print(query, 'is deleted from your friend list')
        elif resp == 'NULL':
            print('No user found with name', query)
        else:
            print('Invalid response from server')
        return f_level(sock, 2)
    
def acc_rqst(sock):
    sock.settimeout(300)
    sock.send(enc('ACCFRND'))
    isOK = dec(sock.recv(32))
    if isOK:
        query = input("Enter username of your future friend: ")
        sock.send(enc(query))
        resp = dec(sock.recv(64))
        if resp == 'FRND':
            print(query,'is already your friend')
        if resp == 'NORQST':
            print(query,'has not sent you a request')
        elif resp == 'OKAY':
            print('Congrats !!',query,'is added to your friend list')
        elif resp == 'NULL':
            print('No user found with name', query)
        else:
            print('Invalid response from server')
        return f_level(sock, 2)
########################################################################

########################### Chat and stuff ############################

def chk_active(sock):
    sock.settimeout(300)
    sock.send(enc('CHKACT'))
    N = int(dec(sock.recv(32)))
    print('\n\n')
    print(''.join(["#"]*30))
    print('Active Users')
    print(''.join(["#"]*30))
    print('\n')
    for online in range(N):
        sock.send(enc('OK'))
        print(dec(sock.recv(64)))
    f_level(sock, 4)

def get_response(sock):
    sock.send(enc('Ready'))
    N = int(dec(sock.recv(32)))
    print('\n\n')
    print(''.join(["#"]*30))
    print('Chat')
    print(''.join(["#"]*30))
    print('\n')
    if N != 0:
        for msg in range(N):
            sock.send(enc('OK'))
            print(dec(sock.recv(256)))
    return sock

def terminate(sock):
    sock.settimeout(300)
    sock.send(enc('FIN'))
    isFinished = dec(sock.recv(32))
    if isFinished == 'OK':
        print('Chat finished')
        f_level(sock, 2)
    else:
        print('Invalid response from server')
        f_level(sock, 2)
        
def refresh(sock):
    sock.settimeout(300)
    sock.send(enc('REFRESH'))
    isOK = dec(sock.recv(32))
    if isOK == 'OK':
        sock=get_response(sock)
    f_level(sock, 5)
    
def snd_msg(sock):
    sock.settimeout(300)
    sock.send(enc('SNDMSG'))
    isOK = dec(sock.recv(32))
    if isOK == 'OK':
        msg = input('What do you say? : ')
        sock.send(enc(msg))
        isSent = dec(sock.recv(32))
        if isSent == 'OK':
            pass
        else:
            print('MSG not delivered')
    f_level(sock, 5)

def init_chat(sock):
    sock.settimeout(300)
    sock.send(enc('CHAT'))
    isOK = dec(sock.recv(32))
    if isOK == 'OK':
        query = input("Enter username of your friend: ")
        sock.send(enc(query))
        resp = dec(sock.recv(64))
        if resp == 'NULL':
            print('No user found with name', query)
        if resp == 'NOFRND':
            print(query,'is not your friend. First send a request to create friendship.')
        elif resp == 'OKAY':
            sock = get_response(sock)
            return f_level(sock, 5)
        else:
            print('Bad response from server')
    else:
        print('Bad response from server')
    f_level(sock, 3)

#######################################################################

def f_level(sock, level):
    global levels
    global levels_
    print('\n\n')
    print(''.join(["#"]*30))
    print('Choose an option')
    print(''.join(["#"]*30))
    print('\n')
    pprint(levels[level])
    code = int(input('Enter your option: '))
    levels_[level][code](sock)
    return

def call_l1(sock):
    global LOGGED_IN
    if LOGGED_IN:
        return log_out(sock)
    return f_level(sock, 1)

def call_l2(sock):
    return f_level(sock, 2)

def call_l3(sock):
    return f_level(sock, 3)

l1 = ['Create New Account', 'Log In']
l1_ = [create_new_account, log_in]
level1 = {i:l1[i-1] for i in range(1,len(l1)+1)}
level1_ = {i:l1_[i-1] for i in range(1,len(l1)+1)}

l2 = ['Feed', 'Post On Timeline', 'Check Timeline', 'Active Users', 'Search Users', 'Log Out']
l2_ = [get_feed, post_timeline, chk_timeline, chk_active, search_usr, call_l1, call_l1]
level2 = {i:l2[i-1] for i in range(1,len(l2)+1)}
level2_ = {i:l2_[i-1] for i in range(1,len(l2)+1)}

l3 = ['Add Friend', 'Delete Friend', 'Accept Request', 'Go Back','Log Out']
l3_ = [add_frnd, dlt_frnd, acc_rqst, call_l2, call_l1]
level3 = {i:l3[i-1] for i in range(1,len(l3)+1)}
level3_ = {i:l3_[i-1] for i in range(1,len(l3)+1)}

l4 = ['Initiate Chat', 'Go to Main Menu', 'Log Out']
l4_ = [init_chat, call_l2, call_l1]
level4 = {i:l4[i-1] for i in range(1,len(l4)+1)}
level4_ = {i:l4_[i-1] for i in range(1,len(l4)+1)}

l5 = ['Send msg', 'Refresh', 'Terminate']
l5_ = [snd_msg, refresh, terminate]
level5 = {i:l5[i-1] for i in range(1,len(l5)+1)}
level5_ = {i:l5_[i-1] for i in range(1,len(l5)+1)}
      
levels = {1:level1, 2:level2, 3:level3, 4:level4, 5:level5}      
levels_ = {1:level1_, 2:level2_, 3:level3_, 4:level4_, 5:level5_}


###########################################
if __name__=='__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    init_connection()
