import socket
import pandas as pd
import os
import sys
import datetime
import shutil
from pprint import pprint
from getpass import getpass
from pickle import UnpicklingError

PORT = 12345
ADDRESS = '172.23.240.1'
LOGGED_IN = False
USERNAME = None

def enc(data):
    return str(data).encode()

def dec(data):
    return data.decode()

def mypprint(*title):
    global USERNAME
    os.system('cls')
    print(''.join(["#"]*30))
    print('Session :', USERNAME)
    print(*title)
    print(''.join(["#"]*30))
    print('\n')

def init_connection():
    global sock
    call_l1(sock)
    return

def establish(sock):
    try:
        sock.connect((ADDRESS, PORT))
        mypprint('Client: Connected to main server....')
    except ConnectionRefusedError:
        mypprint("Client: Server is not up")
        return f_level(sock, 1)
    if sys.argv[1] != 'MT':
        try:
            data = sock.recv(1024).decode()
            subport = int(data)
            print('Sending this okay')
            sock.send(bytes("OK",'utf-8'))
        except ValueError:
            if data=="OVERLOAD":
                mypprint('Client: Server is overloaded. Try again after a while')
                return sock
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ADDRESS, subport))
        mypprint("Client: Connected to sub surver on port:", subport)
    return sock

def create_new_account(sock):
    sock.close()
    sock = socket.socket()
    sock = establish(sock)
    sock.settimeout(3000)
    sock.send(enc('SIGN_UP'))
    isOK = dec(sock.recv(32))
    if isOK=='OK':
        isValid = 'NO'
        while isValid != 'YES':
            USERNAME=input('Enter Unique UserName: ')
            sock.send(enc(USERNAME))
            isValid = dec(sock.recv(32))
            if isValid == 'EXISTS':
                mypprint('User already exists')
        isValid = 'NO'
        while isValid != 'YES':
            PASSWORD=getpass('Enter password longer or eqaul to 3 characters: ')
            sock.send(enc(PASSWORD))
            isValid = dec(sock.recv(32))
            if isValid == 'LESS':
                mypprint('Password is less than 3 charactacters')
        mypprint("SIGN UP SUCCESSFULL")
        
        return call_l1(sock)

def log_in(sock):
    global LOGGED_IN
    global USERNAME
    sock.close()
    sock = socket.socket()
    sock = establish(sock)
    sock.settimeout(3000)
    sock.send(enc('LOG_IN'))
    isOK = dec(sock.recv(32))    
    if isOK=='OK':
        isValid = 'NO'
        while isValid != 'YES':
            USERNAME=input('Enter UserName: ')
            sock.send(enc(USERNAME))
            isValid = dec(sock.recv(32))
        isValid = 'NO'
        while isValid != 'YES':
            PASSWORD=getpass('Enter password: ')
            sock.send(enc(PASSWORD))
            isValid = dec(sock.recv(32))
            if isValid == 'NO':
                print('Incorrect Password')
        mypprint("Client: LOG IN SUCCESSFULL")
        LOGGED_IN = True
        sock = sync(sock)
        return f_level(sock, 2)

def sync(sock):
    global USERNAME
    path = '../local_data/'+USERNAME+'_S'
    ####### Receive
    sock.settimeout(3000)
    sock.send(enc('SYNC'))
    resp = dec(sock.recv(32))
    if resp == 'BEGIN':
        print('Got begin')
        with open(path, 'wb') as f:
            while True:
                print('Sending OK')
                sock.send(enc('OK'))
                msg = sock.recv(1024)
                #print(msg);print('\n\n\n')
                if msg == b'END':
                    break
                f.write(msg)
        try:
            pd.read_pickle(path)
        except UnpicklingError:
            print('File currupted. Abort')
            return sock
    else:
        print('Sync failed')
        return sock
    sock = fixdiff(USERNAME, sock)
    ####### Send
    path = '../local_data/'+USERNAME
    sock.send(enc('SYNC2'))
    resp = dec(sock.recv(32))
    if resp == 'BEGIN':
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(1024)
                if chunk == b'':
                    sock.send(enc('END'))
                    print('End sent')
                    isEnd = dec(sock.recv(32))
                    if isEnd == 'END':
                        mypprint('SYNC COMPLETE')
                        break
                sock.send(chunk)
                isOk = dec(sock.recv(32))
                if not isOk == 'OK':
                    print('Sync aborted abnormaly')
                    break
                print('OK received')
                print(chunk)
    else:
        print('Sync failed')
        return sock
    return sock

def fixdiff(USERNAME, sock):
    path = '../local_data/'
    if os.path.exists(path+USERNAME):
        main = pd.read_pickle(path+USERNAME)
        sdict = pd.read_pickle(path+USERNAME+'_S')
        for usr in sdict['Chat']:
            if usr in main['Chat']:
                main['Chat'][usr] = pd.concat([main['Chat'][usr], sdict['Chat'][usr]]).sort_values('time').drop_duplicates()
            else:
                main['Chat'][usr] = sdict['Chat'][usr]
        for usr in main['Chat']:
            if usr not in sdict['Chat']:
                main['Chat'].pop(usr)
        main['Friends'] = sdict['Friends']
        pd.to_pickle(main, path+USERNAME)
    else:
        shutil.copyfile(path+USERNAME+'_S', path+USERNAME)
    return sock
    
def log_out(sock):
    global USERNAME
    sock.settimeout(3000)
    sock = sync(sock)
    sock.send(enc('LOG_OUT'))
    isOK = dec(sock.recv(32))    
    if isOK=='OK':
        USERNAME = None
        mypprint("Client: LOG OUT SUCCESSFULL")
        return f_level(sock, 1)
    else:
        mypprint('Invalid response from server')

def post_timeline(sock):
    sock.settimeout(3000)
    sock.send(enc('POST'))
    isOK = dec(sock.recv(32))
    if isOK=='OK':
        status = input('Enter your status: ')
        sock.send(enc(status))
        isOk = dec(sock.recv(32))
        if isOk=='OK':
            sock.send(enc(input('Permission: 1. Public, 2. Friends, 3. Limited, 4. Private: ')))
            isUpdated = dec(sock.recv(32))
            if isUpdated=='YES':
                mypprint("Client: Status updated")
    return f_level(sock, 2)

def get_feed(sock):
    sock.settimeout(3000)
    sock.send(enc('FEED'))
    N = int(dec(sock.recv(32))) # We assume N won't be zero
    mypprint('########## FEED')
    if N==0:
        print('--- Nothing to show ---')
        return f_level(sock, 2)
    for usr in range(N):
        sock.send(enc('OK'))
        feed = dec(sock.recv(256))
        print(feed)
    return f_level(sock, 2)

def search_usr(sock):
    sock.settimeout(3000)
    sock.send(enc('SRCH'))
    N = int(dec(sock.recv(32))) # We assume N won't be zero
    mypprint('########## USERS')
    for usr in range(N):
        sock.send(enc('OK'))
        usrname = dec(sock.recv(64))
        print(usrname)
    return f_level(sock, 3)

def chk_timeline(sock):
    sock.settimeout(3000)
    sock.send(enc('CHKTIM'))
    N = int(dec(sock.recv(32)))
    mypprint('########## TIMELINE')
    if N==0:
        print("----Empty Timeline----")
        return f_level(sock, 2)
    for status in range(N):
        sock.send(enc('OK'))
        print(dec(sock.recv(1024)))
    return f_level(sock, 2)

############################## Friendship ##############################

def add_frnd(sock):
    sock.settimeout(3000)
    sock.send(enc('ADDFRND'))
    isOK = dec(sock.recv(32))
    if isOK:
        query = input("Enter username of your future friend: ")
        sock.send(enc(query))
        resp = dec(sock.recv(64))
        if resp == 'ISFRND':
            mypprint(query,'is already your friend')
        elif resp == 'OKAY':
            mypprint('Friend request sent to',query)
        elif resp == 'NULL':
            mypprint('No user found with name', query)
        else:
            mypprint('Invalid response from server')
        return f_level(sock, 2)
    
def view_tl(sock):
    sock.settimeout(3000)
    sock.send(enc('VIEWTL'))
    isOK = dec(sock.recv(32))
    if isOK:
        query = input("Enter username of user: ")
        sock.send(enc(query))
        resp = dec(sock.recv(64))
        if resp == 'OKAY':
            sock = get_response(sock, query+'\'s Timeline')
        elif resp == 'NULL':
            mypprint('No user found with name', query)
        else:
            mypprint('Invalid response from server')
        return f_level(sock, 2)
    
def dlt_frnd(sock):
    sock.settimeout(3000)
    sock.send(enc('DLTFRND'))
    isOK = dec(sock.recv(32))
    if isOK:
        query = input("Enter username of your past friend: ")
        sock.send(enc(query))
        resp = dec(sock.recv(64))
        if resp == 'ISNOTFRND':
            mypprint(query,'is not your friend')
        elif resp == 'OKAY':
            mypprint(query, 'is deleted from your friend list')
        elif resp == 'NULL':
            mypprint('No user found with name', query)
        else:
            mypprint('Invalid response from server')
        return f_level(sock, 2)
    
def add_to_limited(sock):
    sock.settimeout(3000)
    sock.send(enc('ADDLIMITED'))
    isOK = dec(sock.recv(32))
    if isOK:
        query = input("Enter username of your special friend: ")
        sock.send(enc(query))
        resp = dec(sock.recv(64))
        if resp == 'ISNOTFRND':
            mypprint(query,'is not your friend')
        elif resp == 'OKAY':
            mypprint(query, 'is added to your limited friend list')
        elif resp == 'NULL':
            mypprint('No user found with name', query)
        else:
            mypprint('Invalid response from server')
        return f_level(sock, 2)

def remove_from_limited(sock):
    sock.settimeout(3000)
    sock.send(enc('DELLIMITED'))
    isOK = dec(sock.recv(32))
    if isOK:
        query = input("Enter username of your not special anymore friend: ")
        sock.send(enc(query))
        resp = dec(sock.recv(64))
        if resp == 'ISNOTFRND':
            mypprint(query,'is not your friend')
        elif resp == 'OKAY':
            mypprint(query, 'is removed from your limited friend list')
        elif resp == 'ISNOTSPL':
            mypprint(query, 'is not in your special friends list')
        elif resp == 'NULL':
            mypprint('No user found with name', query)
        else:
            mypprint('Invalid response from server')
        return f_level(sock, 2)
    
def acc_rqst(sock):
    sock.settimeout(3000)
    sock.send(enc('ACCFRND'))
    isOK = dec(sock.recv(32))
    if isOK:
        query = input("Enter username of your future friend: ")
        sock.send(enc(query))
        resp = dec(sock.recv(64))
        if resp == 'FRND':
            mypprint(query,'is already your friend')
        if resp == 'NORQST':
            mypprint(query,'has not sent you a request')
        elif resp == 'OKAY':
            mypprint('Congrats !!',query,'is added to your friend list')
        elif resp == 'NULL':
            mypprint('No user found with name', query)
        else:
            mypprint('Invalid response from server')
        return f_level(sock, 2)
    
def get_friends(sock):
    sock.settimeout(3000)
    sock.send(enc('GETFRND'))
    N = int(dec(sock.recv(32)))
    mypprint('########## FRIENDS')
    if N==0:
        print("---- Nothing here ----")
        return f_level(sock, 2)
    for frnd in range(N):
        sock.send(enc('OK'))
        print(dec(sock.recv(1024)))
    return f_level(sock, 4)

def f_of_f(sock):
    sock.settimeout(3000)
    sock.send(enc('FOFF'))
    isOK = dec(sock.recv(32))
    if isOK:
        query = input("Enter username of your friend: ")
        sock.send(enc(query))
        resp = dec(sock.recv(64))
        if resp == 'ISNOTFRND':
            mypprint(query,'is not your friend')
        elif resp == 'OKAY':
            sock.send(enc('OKAY'))
            N = int(dec(sock.recv(32)))
            mypprint('########## Friends of',query)
            if N==0:
                print("---- Nothing here ----")
                return f_level(sock, 2)
            for frnd in range(N):
                sock.send(enc('OK'))
                print(dec(sock.recv(512)))
            return f_level(sock, 4)
        elif resp == 'NULL':
            mypprint('No user found with name', query)
        else:
            mypprint('Invalid response from server')
            return f_level(sock, 2)
########################################################################

########################### Chat and stuff ############################

def chk_active(sock):
    sock.settimeout(3000)
    sock.send(enc('CHKACT'))
    N = int(dec(sock.recv(32)))
    mypprint('Active Users')
    for online in range(N):
        sock.send(enc('OK'))
        print(dec(sock.recv(64)))
    return f_level(sock, 4)

def get_response(sock, title):
    sock.send(enc('Ready'))
    N = int(dec(sock.recv(32)))
    mypprint(title)
    if N == 0:
        print('-----Nothing to show here-----')
    else:    
        for msg in range(N):
            sock.send(enc('OK'))
            print(dec(sock.recv(256)))
    return sock

def terminate(sock):
    sock.settimeout(3000)
    sock.send(enc('FIN'))
    isFinished = dec(sock.recv(32))
    if isFinished == 'OK':
        mypprint('Chat finished')
        return f_level(sock, 2)
    else:
        mypprint('Invalid response from server')
        return f_level(sock, 2)
        
def refresh(sock):
    sock.settimeout(3000)
    sock.send(enc('REFRESH'))
    isOK = dec(sock.recv(32))
    if isOK == 'OK':
        sock=get_response(sock, 'Chat')
    return f_level(sock, 5)
    
def snd_msg(sock):
    sock.settimeout(3000)
    sock.send(enc('SNDMSG'))
    isOK = dec(sock.recv(32))
    if isOK == 'OK':
        msg = input('What do you say? : ')
        sock.send(enc(msg))
        isSent = dec(sock.recv(32))
        if isSent == 'OK':
            pass
        else:
            mypprint('MSG not delivered')
    return f_level(sock, 5)

def live_chat(sock):
    if sys.argv[1] != 'MT':
        print('Not implemented here sorry')
        return f_level(sock, 3)
    sock.settimeout(3000)
    sock.send(enc('LIVECHAT'))
    isOK = dec(sock.recv(32))
    if isOK == 'OK':
        query = input("Enter username of your friend: ")
        sock.send(enc(query))
        resp = dec(sock.recv(64))
        if resp == 'NULL':
            mypprint('No user found with name', query)
        elif resp == 'NOFRND':
            mypprint(query,'is not your friend. First send a request to create friendship.')
        elif resp == 'SEND':
            live = ''
            respback = ''
            mypprint('Please enter "@end@" (without quotes) to end this chat. Enjoy :)')
            while respback != '@end@':
                live = input('Me: ')
                sock.send(enc(live))
                respback = dec(sock.recv(1024))
                print(query+':',respback)
        elif resp == 'RECV':
            live = 'OK'
            sock.send(enc(live))
            respback = dec(sock.recv(1024))
            print(query+':',respback)
            while respback != '@end@':
                live = input('Me: ')
                sock.send(enc(live))
                respback = dec(sock.recv(1024))
                print(query+':',respback)
            return f_level(sock, 3)
        else:
            mypprint('Bad response from server')
    else:
        mypprint('Bad response from server')
    return f_level(sock, 3)

def init_chat(sock):
    sock.settimeout(3000)
    sock.send(enc('CHAT'))
    isOK = dec(sock.recv(32))
    if isOK == 'OK':
        query = input("Enter username of your friend: ")
        sock.send(enc(query))
        resp = dec(sock.recv(64))
        if resp == 'NULL':
            mypprint('No user found with name', query)
        if resp == 'NOFRND':
            mypprint(query,'is not your friend. First send a request to create friendship.')
        elif resp == 'OKAY':
            sock = get_response(sock, 'Chat')
            return f_level(sock, 5)
        else:
            mypprint('Bad response from server')
    else:
        mypprint('Bad response from server')
    return f_level(sock, 3)

#######################################################################

def f_level(sock, level):
    global levels
    global levels_
    print('\n\rChoose an option')
    pprint(levels[level])
    code = int(input('Enter your option: '))
    levels_[level][code](sock)
    return

def call_l1(sock):
    os.system('cls')
    global LOGGED_IN
    if LOGGED_IN:
        return log_out(sock)
    mypprint('Welcome to Mini-Face')
    return f_level(sock, 1)

def call_l2(sock):
    os.system('cls')
    return f_level(sock, 2)

def call_l3(sock):
    os.system('cls')
    return f_level(sock, 3)


def offline_chat(sock):
    path = '../local_data/'
    mypprint('Welcome to Mini-Face Offline')
    USERNAME = input('Enter Username: ')
    Password = getpass('Enter secure password: ')
    try:
        dct = pd.read_pickle(path+USERNAME)
    except FileNotFoundError:
        print('You do not exist on this system. go online first.')
        return f_level(sock, 1)
    mypprint(' Enter friend name to start interaction or @end@ to go back')
    for frnd in dct['Friends']:
        print(frnd)
    print()
    name = input('Your response: ')
    if name == '@end@':
        print('Good bye');return f_level(sock, 1)
    else:
        if name not in dct['Friends']:
            print(name,'is not your friend CMon')
            return f_level(sock, 1)
        else:
            cht = dct['Chat'][name]
            for ts, usr, msg in zip(cht['time'], cht['usr'], cht['msg']):
                print(ts+' --- :'+usr+' : '+msg)
            print()
            print('Send msg to',name,'. Enter @end@ to exit')
            msg = input('Me: ')
            while msg != '@end@':
                ln = len(dct['Chat'][name])
                ts = str(datetime.datetime.now())
                dct['Chat'][name].loc[ln, ['time','usr','msg','isSeen']] = [ts, 'Me', msg, 'NotSeen']
                msg = input('Me: ')
            pd.to_pickle(dct, path+USERNAME)
            print('Ok good bye')
            return f_level(sock, 1)
            
            

l1 = ['Create New Account', 'Log In', 'Offline Chat']
l1_ = [create_new_account, log_in, offline_chat]
level1 = {i:l1[i-1] for i in range(1,len(l1)+1)}
level1_ = {i:l1_[i-1] for i in range(1,len(l1)+1)}

l2 = ['Feed', 'Post On Timeline', 'Check Timeline', 'Active Users', 'Search Users', 'Friends', 'Log Out']
l2_ = [get_feed, post_timeline, chk_timeline, chk_active, search_usr, get_friends, call_l1, call_l1]
level2 = {i:l2[i-1] for i in range(1,len(l2)+1)}
level2_ = {i:l2_[i-1] for i in range(1,len(l2)+1)}

l3 = ['Add Friend', 'View Timeline', 'Delete Friend', 'Accept Request', 'Go Back','Log Out']
l3_ = [add_frnd, view_tl, dlt_frnd, acc_rqst, call_l2, call_l1]
level3 = {i:l3[i-1] for i in range(1,len(l3)+1)}
level3_ = {i:l3_[i-1] for i in range(1,len(l3)+1)}

# Live chat implemented on multithreded server only
l4 = ['Live chat', 'Chat', 'View Timeline', 'Delete Friend', 'Add to Limited Friends', 
      'Delete from Limited Friends', 'Friends of Friends', 'Go to Main Menu', 'Log Out']
l4_ = [live_chat, init_chat, view_tl, dlt_frnd, add_to_limited, remove_from_limited, f_of_f, call_l2, call_l1]
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
