import socket
import sys
import os
import pandas as pd
import datetime
from glob import glob
from pickle import PicklingError
import shutil

hostname = socket.gethostname()
addr = socket.gethostbyname(hostname)
port = int(sys.argv[1])
caddr = sys.argv[2]

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

sock.bind((addr, port))
sock.listen()

client, newaddr = sock.accept()
if newaddr[0]==caddr:
    print("Sub server: Connection established with", newaddr)
else:
    print("Sub server: Suspicious connection. Abort")
    sys.exit()
    
######### Methods

def enc(data):
    return str(data).encode()

def dec(data):
    return data.decode()

def get_empty_user():
    return {'USERNAME':None,
            'PASSWORD':None,
            'TIMELINE':pd.DataFrame(columns=['time','text','Flag']),
            'Friends':set(),
            'Limited Friends':set(),
            'Rcvd Requests':set(),
            'isOnline':False,
            'Chat':{}
            }

def sign_up(client):
    path = '../client_data/users/'
    USERNAME = dec(client.recv(512))
    while os.path.exists(path+USERNAME): # is valid??
        client.send(enc('EXISTS'))
        USERNAME = dec(client.recv(512))
    client.send(enc('YES'))
    PASSWORD = dec(client.recv(512))
    while len(PASSWORD)<3: # is valid??
        client.send(enc('LESS'))
        PASSWORD = dec(client.recv(512))
    client.send(enc('YES'))
    dct = get_empty_user()
    dct.update({'USERNAME':USERNAME,
                'PASSWORD':PASSWORD})
    pd.to_pickle(dct,path+USERNAME)

def log_in(client):
    path = '../client_data/users/'
    USERNAME = dec(client.recv(512))
    while not os.path.exists(path+USERNAME): # is valid??
        client.send(enc('NO'))
        USERNAME = dec(client.recv(512))
    client.send(enc('YES'))
    passchk = pd.read_pickle(path+USERNAME)['PASSWORD']
    PASSWORD = dec(client.recv(512))
    while PASSWORD!=passchk: # is valid??
        client.send(enc('NO'))
        PASSWORD = dec(client.recv(512))
    client.send(enc('YES'))
    dct = pd.read_pickle(path+USERNAME)
    dct['isOnline'] = True
    pd.to_pickle(dct,path+USERNAME)
    return USERNAME

def log_out(USERNAME, client):
    path = '../client_data/users/'
    dct = pd.read_pickle(path+USERNAME)
    dct['isOnline'] = False
    pd.to_pickle(dct, path+USERNAME)

def post(USERNAME, client):
    flags = {1:'isPublic', 2:'isFriends', 3:'isLimited', 4:'isPrivate'}
    path = '../client_data/users/'
    status = dec(client.recv(1024))
    client.send(enc('OK'))
    Flag = int(dec(client.recv(32)))
    dct = pd.read_pickle(path+USERNAME)
    ind = len(dct['TIMELINE'])
    dct['TIMELINE'].loc[ind, 'time'] = str(datetime.datetime.now())
    dct['TIMELINE'].loc[ind, 'text'] = status
    dct['TIMELINE'].loc[ind, 'Flag'] = flags[Flag]
    pd.to_pickle(dct, path+USERNAME)
    client.send(enc('YES'))

def status_chk(USERNAME, client, flag='isPrivate'):
    path = '../client_data/users/'
    dct = pd.read_pickle(path+USERNAME)['TIMELINE']
    ln = len(dct)
    N = min(10, ln)
    client.send(enc(N))
    print("N sent for status_chk",N,'of',ln)
    if N!=0:
        dct = dct.iloc[ln-N:ln]
        for ts, status, flag in zip(dct['time'], dct['text'], dct['Flag']):
            recv = dec(client.recv(32))
            if recv=='OK':
                client.send(enc(ts+' --- '+status+' --- '+flag))
                
def view_tl(USERNAME, client):
    path = '../client_data/users/'
    usrs = glob(path+'*')
    if '\\' in usrs[0]:
        SPCHR = '\\'
    elif '/' in usrs[0]:
        SPCHR = '/'
    names = [usr.split(SPCHR)[-1] for usr in usrs]
    name = dec(client.recv(64))
    if not name in names:
        client.send(enc('NULL'))
        print('NULL sent')
        return
    name_dct = pd.read_pickle(path+name)
    tl = name_dct['TIMELINE']
    flags = ['isPublic']
    if USERNAME in name_dct['Friends']:
        flags.append('isFriends')
    if USERNAME in name_dct['Limited Friends']:
        flags.append('isLimited')   
    if USERNAME == name_dct['USERNAME']:
        flags.append('isLimited')
        flags.append('isFriends')
        flags.append('isPrivate')
        
    client.send(enc('OKAY'))
    print(USERNAME,'has',flags,'flags')
    dct = tl[tl.Flag.isin(flags)]
    ln = len(dct)
    N = min(10, ln)
    isReady = dec(client.recv(32))
    if isReady=='Ready':
        client.send(enc(N))
        print("N sent for status_chk",N,'of',ln)
        if N!=0:
            dct = dct.iloc[ln-N:N]
            for ts, status in zip(dct['time'], dct['text']):
                recv = dec(client.recv(32))
                if recv=='OK':
                    client.send(enc(ts+' --- '+status))
    else:
        print('Client not ready')

def search_usr(USERNAME, client):
    path = '../client_data/users/'
    dct = pd.read_pickle(path+USERNAME)
    usrs = glob(path+'*')
    if '\\' in usrs[0]:
        SPCHR = '\\'
    elif '/' in usrs[0]:
        SPCHR = '/'
    N = len(usrs)
    print(usrs)
    client.send(enc(N)) # We assume N won't be zero
    for usr in usrs:
        recv = dec(client.recv(32))
        if recv=='OK':
            name = usr.split(SPCHR)[-1]
            isFriend = 'You' if name==USERNAME else\
                       'Friend' if name in dct['Friends'] else\
                       'Request Received' if name in dct['Rcvd Requests'] else\
                       'Add Friend'
            client.send(enc(name+'---'+isFriend))

def get_friends(USERNAME, client):
    path = '../client_data/users/'
    dct = pd.read_pickle(path+USERNAME)
    frnds = dct['Friends']
    N = len(frnds)
    client.send(enc(N))
    for frnd in frnds:
        recv = dec(client.recv(32))
        if recv=='OK':
            flag = 'Friend' if frnd not in dct['Limited Friends'] else 'Special Friend'
            client.send(enc(frnd+' --- '+flag))
############################### Friendship ############################

def add_frnd(USERNAME, client):
    path = '../client_data/users/'
    dct = pd.read_pickle(path+USERNAME)
    usrs = glob(path+'*')
    if '\\' in usrs[0]:
        SPCHR = '\\'
    elif '/' in usrs[0]:
        SPCHR = '/'
    names = [usr.split(SPCHR)[-1] for usr in usrs]
    name = dec(client.recv(64))
    if not name in names:
        client.send(enc('NULL'))
    elif name in dct['Friends']:
        client.send(enc('ISFRND'))
    else:
        dct = pd.read_pickle(path+name)
        dct['Rcvd Requests'].add(USERNAME)
        pd.to_pickle(dct, path+name)
        client.send(enc('OKAY'))
        
def dlt_frnd(USERNAME, client):
    path = '../client_data/users/'
    dct = pd.read_pickle(path+USERNAME)
    usrs = glob(path+'*')
    if '\\' in usrs[0]:
        SPCHR = '\\'
    elif '/' in usrs[0]:
        SPCHR = '/'
    names = [usr.split(SPCHR)[-1] for usr in usrs]
    name = dec(client.recv(64))
    if not name in names:
        client.send(enc('NULL'))
    elif name not in dct['Friends']:
        client.send(enc('ISNOTFRND'))
    else:
        frnd_dct = pd.read_pickle(path+name)
        dct['Friends'].remove(name)
        frnd_dct['Friends'].remove(USERNAME)
        dct['Chat'].pop(name)
        frnd_dct['Chat'].pop(USERNAME)
        pd.to_pickle(dct, path+USERNAME)
        pd.to_pickle(frnd_dct, path+name)
        client.send(enc('OKAY'))

def add_to_limited(USERNAME, client):
    path = '../client_data/users/'
    dct = pd.read_pickle(path+USERNAME)
    usrs = glob(path+'*')
    if '\\' in usrs[0]:
        SPCHR = '\\'
    elif '/' in usrs[0]:
        SPCHR = '/'
    names = [usr.split(SPCHR)[-1] for usr in usrs]
    name = dec(client.recv(64))
    if not name in names:
        client.send(enc('NULL'))
    elif name not in dct['Friends']:
        client.send(enc('ISNOTFRND'))
    else:
        dct['Limited Friends'].add(name)
        pd.to_pickle(dct, path+USERNAME)
        client.send(enc('OKAY'))
            
def del_from_limited(s,USERNAME, client):
    path = '../client_data/users/'
    dct = pd.read_pickle(path+USERNAME)
    usrs = glob(path+'*')
    if '\\' in usrs[0]:
        SPCHR = '\\'
    elif '/' in usrs[0]:
        SPCHR = '/'
    names = [usr.split(SPCHR)[-1] for usr in usrs]
    name = dec(client.recv(64))
    if not name in names:
        client.send(enc('NULL'))
    elif name not in dct['Friends']:
        client.send(enc('ISNOTFRND'))
    elif name not in dct['Limited Friends']:
        clinet.send(enc('ISNOTSPL'))
    else:
        dct['Limited Friends'].remove(name)
        pd.to_pickle(dct, path+USERNAME)
        client.send(enc('OKAY'))        

def acc_rqst(USERNAME, client):
    path = '../client_data/users/'
    dct = pd.read_pickle(path+USERNAME)
    usrs = glob(path+'*')
    if '\\' in usrs[0]:
        SPCHR = '\\'
    elif '/' in usrs[0]:
        SPCHR = '/'
    names = [usr.split(SPCHR)[-1] for usr in usrs]
    name = dec(client.recv(64))
    if not name in names:
        client.send(enc('NULL'))
    elif name in dct['Friends']:
        client.send(enc('FRND'))
    elif name not in dct['Rcvd Requests']:
        client.send('NORQST')
    else:
        frnd_dct = pd.read_pickle(path+name)
        dct['Rcvd Requests'].remove(name)
        dct['Friends'].add(name)
        frnd_dct['Friends'].add(USERNAME)
        dct['Chat'][name] = pd.DataFrame(columns=['time', 'usr', 'msg'])
        frnd_dct['Chat'][USERNAME] = pd.DataFrame(columns=['time', 'usr', 'msg'])
        pd.to_pickle(dct, path+USERNAME)
        pd.to_pickle(frnd_dct, path+name)
        client.send(enc('OKAY'))

#######################################################################

############## Chat and stuff #########################################

def chk_act(USERNAME, client):
    print('entered ')
    path = '../client_data/users/'
    dct = pd.read_pickle(path+USERNAME)
    usrs = glob(path+'*')
    if '\\' in usrs[0]:
        SPCHR = '\\'
    elif '/' in usrs[0]:
        SPCHR = '/'
    name_dict = {usr.split(SPCHR)[-1]:usr for usr in usrs}
    frnds = dct['Friends']
    online = []
    for frnd in frnds:
        isOnline = pd.read_pickle(name_dict[frnd])['isOnline']
        if isOnline:
            online.append(frnd)
    print('sending', len(online))
    client.send(enc(len(online)))
    for each in online:
        isOk = dec(client.recv(32))
        if isOk == 'OK':
            client.send(enc(each))

def send_response(USERNAME, name, client):
    path = '../client_data/users/'
    dct = pd.read_pickle(path+USERNAME)
    usrdf = dct['Chat'][name]
    ln = len(usrdf)
    N = min(10, ln)
    client.send(enc(N))
    if N!=0:
        usrdf = usrdf.iloc[ln-N:ln]
        for ts, usr, msg in zip(usrdf['time'], usrdf['usr'], usrdf['msg']):
            isOk = dec(client.recv(32))
            if isOk == 'OK':
                client.send(enc(ts+'---:'+usr+' : '+msg))
    return client  

def init_chat(USERNAME, client):
    path = '../client_data/users/'
    dct = pd.read_pickle(path+USERNAME)
    usrs = glob(path+'*')
    if '\\' in usrs[0]:
        SPCHR = '\\'
    elif '/' in usrs[0]:
        SPCHR = '/'
    names = [usr.split(SPCHR)[-1] for usr in usrs]
    name = dec(client.recv(64))
    if not name in names:
        client.send(enc('NULL'))
    elif not name in dct['Friends']:
        client.send(enc('NOFRND'))
    else:
        client.send(enc('OKAY'))
        isReady = dec(client.recv(32))
        if isReady == 'Ready':
            print('Client ready. Sending chat')
            client = send_response(USERNAME, name, client)
        resp = dec(client.recv(64))
        client.send(enc('OK'))
        while resp != 'FIN':
            if resp == 'REFRESH':
                isReady = dec(client.recv(32))
                if isReady == 'Ready':
                    client = send_response(USERNAME, name, client)
            elif resp == 'SNDMSG':
                msg = dec(client.recv(512))
                dct = pd.read_pickle(path+USERNAME)
                frnd_dct = pd.read_pickle(path+name)
                l_dct = len(dct['Chat'][name])
                l_frnd_dct = len(frnd_dct['Chat'][USERNAME])
                ts = str(datetime.datetime.now())
                print('Current len of chat', l_dct, l_frnd_dct)
                dct['Chat'][name].loc[l_dct, ['time','usr','msg']] = [ts, 'Me', msg]
                frnd_dct['Chat'][USERNAME].loc[l_frnd_dct, ['time','usr','msg']] = [ts, USERNAME, msg]
                pd.to_pickle(dct,path+USERNAME)
                pd.to_pickle(frnd_dct,path+name)
                client.send(enc('OK'))
            resp = dec(client.recv(64))
            client.send(enc('OK'))
    
        
    
######### Listening

USERNAME = None
while True:
    client.settimeout(3000)
    print('Receiving main action now')
    action = client.recv(512).decode()
    if action == 'SIGN_UP':
        client.send(enc('OK'))
        sign_up(client)
    elif action == 'LOG_IN':
        client.send(enc('OK'))
        USERNAME = log_in(client)
    elif action == 'LOG_OUT':
        client.send(enc('OK'))
        log_out(USERNAME, client)
        USERNAME = None
    elif action == 'POST':
        client.send(enc('OK'))
        post(USERNAME, client)
    elif action == 'CHKTIM':
        status_chk(USERNAME, client)
    elif action == 'VIEWTL':
        client.send(enc('OK'))
        view_tl(USERNAME, client)
    elif action == 'SRCH':
        search_usr(USERNAME, client)
    elif action == 'ADDFRND':
        client.send(enc('OK'))
        add_frnd(USERNAME, client)
    elif action == 'ACCFRND':
        client.send(enc('OK'))
        acc_rqst(USERNAME, client)
    elif action == 'DLTFRND':
        client.send(enc('OK'))
        dlt_frnd(USERNAME, client)
    elif action == 'ADDLIMITED':
        client.send(enc('OK'))
        add_to_limited(USERNAME, client)
    elif action == 'DELLIMITED':
        client.send(enc('OK'))
        del_from_limited(USERNAME, client)
    elif action == 'GETFRND':
        get_friends(USERNAME, client)
    elif action == 'CHKACT':
        chk_act(USERNAME, client)
    elif action == 'CHAT':
        client.send(enc('OK'))
        init_chat(USERNAME, client)
    else:
        print('Not matched with anything')
        break
        
if USERNAME:
    path = '../client_data/users/'
    dct = pd.read_pickle(path+USERNAME)
    dct['isOnline'] = False
    pd.to_pickle(dct, path+USERNAME)
print("EXIT :)")
