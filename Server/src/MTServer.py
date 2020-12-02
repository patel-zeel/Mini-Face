import socket
import sys
import os
import pandas as pd
import datetime
from glob import glob
from threading import Thread 
from time import sleep
from pickle import PicklingError
import shutil

pairs = {}
box = []
Lock = False
# Multithreaded Python server : TCP Server Socket Thread Pool
class ServerThread(Thread): 
    def __init__(s, ip,port,num): 
        Thread.__init__(s) 
        s.ip = ip
        s.port = port 
        s.num = num
        print ("[+] New server socket thread started for " + ip + ":" + str(port))
 
    def enc(s,data):
        return str(data).encode()

    def dec(s,data):
        return data.decode()

    def get_empty_user(s,):
        return {'USERNAME':None,
                'PASSWORD':None,
                'TIMELINE':pd.DataFrame(columns=['time','text','Flag']),
                'Friends':set(),
                'Limited Friends':set(),
                'Rcvd Requests':set(),
                'isOnline':False,
                'Chat':{}
                }

    def sign_up(s,client):
        path = '../client_data/users/'
        USERNAME = s.dec(client.recv(512))
        while os.path.exists(path+USERNAME): # is valid??
            client.send(s.enc('EXISTS'))
            USERNAME = s.dec(client.recv(512))
        client.send(s.enc('YES'))
        PASSWORD = s.dec(client.recv(512))
        while len(PASSWORD)<3: # is valid??
            client.send(s.enc('LESS'))
            PASSWORD = s.dec(client.recv(512))
        client.send(s.enc('YES'))
        dct = s.get_empty_user()
        dct.update({'USERNAME':USERNAME,
                    'PASSWORD':PASSWORD})
        pd.to_pickle(dct,path+USERNAME)

    def log_in(s,client):
        path = '../client_data/users/'
        USERNAME = s.dec(client.recv(512))
        while not os.path.exists(path+USERNAME): # is valid??
            client.send(s.enc('NO'))
            USERNAME = s.dec(client.recv(512))
        client.send(s.enc('YES'))
        passchk = pd.read_pickle(path+USERNAME)['PASSWORD']
        PASSWORD = s.dec(client.recv(512))
        while PASSWORD!=passchk: # is valid??
            client.send(s.enc('NO'))
            PASSWORD = s.dec(client.recv(512))
        client.send(s.enc('YES'))
        dct = pd.read_pickle(path+USERNAME)
        dct['isOnline'] = True
        pairs.update({USERNAME:s.num})
        pd.to_pickle(dct,path+USERNAME)
        return USERNAME

    def log_out(s,USERNAME, client):
        path = '../client_data/users/'
        dct = pd.read_pickle(path+USERNAME)
        dct['isOnline'] = False
        pd.to_pickle(dct, path+USERNAME)

    def post(s,USERNAME, client):
        flags = {1:'isPublic', 2:'isFriends', 3:'isLimited', 4:'isPrivate'}
        path = '../client_data/users/'
        status = s.dec(client.recv(1024))
        client.send(s.enc('OK'))
        Flag = int(s.dec(client.recv(32)))
        dct = pd.read_pickle(path+USERNAME)
        ind = len(dct['TIMELINE'])
        dct['TIMELINE'].loc[ind, 'time'] = str(datetime.datetime.now())
        dct['TIMELINE'].loc[ind, 'text'] = status
        dct['TIMELINE'].loc[ind, 'Flag'] = flags[Flag]
        pd.to_pickle(dct, path+USERNAME)
        client.send(s.enc('YES'))

    def status_chk(s,USERNAME, client, flag='isPrivate'):
        path = '../client_data/users/'
        dct = pd.read_pickle(path+USERNAME)['TIMELINE']
        ln = len(dct)
        N = min(10, ln)
        client.send(s.enc(N))
        print("N sent for status_chk",N,'of',ln)
        if N!=0:
            dct = dct.iloc[ln-N:ln]
            for ts, status, flag in zip(dct['time'], dct['text'], dct['Flag']):
                recv = s.dec(client.recv(32))
                if recv=='OK':
                    client.send(s.enc(ts+' --- '+status+' --- '+flag))

    def view_tl(s,USERNAME, client):
        path = '../client_data/users/'
        usrs = glob(path+'*')
        if '\\' in usrs[0]:
            SPCHR = '\\'
        elif '/' in usrs[0]:
            SPCHR = '/'
        names = [usr.split(SPCHR)[-1] for usr in usrs]
        name = s.dec(client.recv(64))
        if not name in names:
            client.send(s.enc('NULL'))
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

        client.send(s.enc('OKAY'))
        print(USERNAME,'has',flags,'flags')
        dct = tl[tl.Flag.isin(flags)]
        ln = len(dct)
        N = min(10, ln)
        isReady = s.dec(client.recv(32))
        if isReady=='Ready':
            client.send(s.enc(N))
            print("N sent for status_chk",N,'of',ln)
            if N!=0:
                dct = dct.iloc[ln-N:N]
                for ts, status in zip(dct['time'], dct['text']):
                    recv = s.dec(client.recv(32))
                    if recv=='OK':
                        client.send(s.enc(ts+' --- '+status))
        else:
            print('Client not ready')

    def send_feed(s, USERNAME, client):
        path = '../client_data/users/'
        usrs = glob(path+'*')
        if '\\' in usrs[0]:
            SPCHR = '\\'
        elif '/' in usrs[0]:
            SPCHR = '/'
        names = [usr.split(SPCHR)[-1] for usr in usrs]
        feed = []
        for name in names:
            name_dct = pd.read_pickle(path+name)
            tl = name_dct['TIMELINE']
            tl['usr'] = name
            flags = ['isPublic']
            if USERNAME in name_dct['Friends']:
                flags.append('isFriends')
            if USERNAME in name_dct['Limited Friends']:
                flags.append('isLimited')   
            if USERNAME == name_dct['USERNAME']:
                flags.append('isLimited')
                flags.append('isFriends')
                flags.append('isPrivate')
            feed.append(tl[tl.Flag.isin(flags)])
        feed = pd.concat(feed).sort_values('time')
        ln = len(feed)
        N = min(10, ln)
        client.send(s.enc(N))
        print("N sent for status_chk",N,'of',ln)
        if N!=0:
            dct = feed.iloc[ln-N:N]
            for ts, usr, status in zip(dct['time'], dct['usr'], dct['text']):
                recv = s.dec(client.recv(32))
                if recv=='OK':
                    client.send(s.enc(ts+' --- : '+usr+' : '+status))
    
    def search_usr(s,USERNAME, client):
        path = '../client_data/users/'
        dct = pd.read_pickle(path+USERNAME)
        usrs = glob(path+'*')
        if '\\' in usrs[0]:
            SPCHR = '\\'
        elif '/' in usrs[0]:
            SPCHR = '/'
        N = len(usrs)
        print(usrs)
        client.send(s.enc(N)) # We assume N won't be zero
        for usr in usrs:
            recv = s.dec(client.recv(32))
            if recv=='OK':
                name = usr.split(SPCHR)[-1]
                isFriend = 'You' if name==USERNAME else\
                           'Friend' if name in dct['Friends'] else\
                           'Request Received' if name in dct['Rcvd Requests'] else\
                           'Add Friend'
                client.send(s.enc(name+'---'+isFriend))

    ############################### Friendship ############################

    def add_frnd(s,USERNAME, client):
        path = '../client_data/users/'
        dct = pd.read_pickle(path+USERNAME)
        usrs = glob(path+'*')
        if '\\' in usrs[0]:
            SPCHR = '\\'
        elif '/' in usrs[0]:
            SPCHR = '/'
        names = [usr.split(SPCHR)[-1] for usr in usrs]
        name = s.dec(client.recv(64))
        if not name in names:
            client.send(s.enc('NULL'))
        elif name in dct['Friends']:
            client.send(s.enc('ISFRND'))
        else:
            dct = pd.read_pickle(path+name)
            dct['Rcvd Requests'].add(USERNAME)
            pd.to_pickle(dct, path+name)
            client.send(s.enc('OKAY'))

    def dlt_frnd(s,USERNAME, client):
        path = '../client_data/users/'
        dct = pd.read_pickle(path+USERNAME)
        usrs = glob(path+'*')
        if '\\' in usrs[0]:
            SPCHR = '\\'
        elif '/' in usrs[0]:
            SPCHR = '/'
        names = [usr.split(SPCHR)[-1] for usr in usrs]
        name = s.dec(client.recv(64))
        if not name in names:
            client.send(s.enc('NULL'))
        elif name not in dct['Friends']:
            client.send(s.enc('ISNOTFRND'))
        else:
            frnd_dct = pd.read_pickle(path+name)
            dct['Friends'].remove(name)
            frnd_dct['Friends'].remove(USERNAME)
            dct['Chat'].pop(name)
            frnd_dct['Chat'].pop(USERNAME)
            pd.to_pickle(dct, path+USERNAME)
            pd.to_pickle(frnd_dct, path+name)
            client.send(s.enc('OKAY'))
            
    def add_to_limited(s,USERNAME, client):
        path = '../client_data/users/'
        dct = pd.read_pickle(path+USERNAME)
        usrs = glob(path+'*')
        if '\\' in usrs[0]:
            SPCHR = '\\'
        elif '/' in usrs[0]:
            SPCHR = '/'
        names = [usr.split(SPCHR)[-1] for usr in usrs]
        name = s.dec(client.recv(64))
        if not name in names:
            client.send(s.enc('NULL'))
        elif name not in dct['Friends']:
            client.send(s.enc('ISNOTFRND'))
        else:
            dct['Limited Friends'].add(name)
            pd.to_pickle(dct, path+USERNAME)
            client.send(s.enc('OKAY'))
            
    def f_of_f(s,USERNAME, client):
        path = '../client_data/users/'
        dct = pd.read_pickle(path+USERNAME)
        usrs = glob(path+'*')
        if '\\' in usrs[0]:
            SPCHR = '\\'
        elif '/' in usrs[0]:
            SPCHR = '/'
        names = [usr.split(SPCHR)[-1] for usr in usrs]
        name = s.dec(client.recv(64))
        if not name in names:
            client.send(s.enc('NULL'))
        elif name not in dct['Friends']:
            client.send(s.enc('ISNOTFRND'))
        else:
            client.send(s.enc('OKAY'))
            isOk = s.dec(client.recv(32))
            frdct = pd.read_pickle(path+name)
            N = len(frdct['Friends'])
            if isOk == 'OKAY':
                client.send(s.enc(N))
                for each in frdct['Friends']:
                    isOk = s.dec(client.recv(32))
                    if isOk == 'OK':
                        flag = 'Friend' if each in dct['Friends'] else 'You' if each==USERNAME else 'Add Friend'
                        client.send(s.enc(each+' --- '+flag))
                    
            
    def del_from_limited(s,USERNAME, client):
        path = '../client_data/users/'
        dct = pd.read_pickle(path+USERNAME)
        usrs = glob(path+'*')
        if '\\' in usrs[0]:
            SPCHR = '\\'
        elif '/' in usrs[0]:
            SPCHR = '/'
        names = [usr.split(SPCHR)[-1] for usr in usrs]
        name = s.dec(client.recv(64))
        if not name in names:
            client.send(s.enc('NULL'))
        elif name not in dct['Friends']:
            client.send(s.enc('ISNOTFRND'))
        elif name not in dct['Limited Friends']:
            clinet.send(s.enc('ISNOTSPL'))
        else:
            print('Limited are',dct['Limited Friends'])
            dct['Limited Friends'].remove(name)
            print('Limited are',dct['Limited Friends'])
            pd.to_pickle(dct, path+USERNAME)
            client.send(s.enc('OKAY'))

    def acc_rqst(s,USERNAME, client):
        path = '../client_data/users/'
        dct = pd.read_pickle(path+USERNAME)
        usrs = glob(path+'*')
        if '\\' in usrs[0]:
            SPCHR = '\\'
        elif '/' in usrs[0]:
            SPCHR = '/'
        names = [usr.split(SPCHR)[-1] for usr in usrs]
        name = s.dec(client.recv(64))
        if not name in names:
            client.send(s.enc('NULL'))
        elif name in dct['Friends']:
            client.send(s.enc('FRND'))
        elif name not in dct['Rcvd Requests']:
            client.send('NORQST')
        else:
            frnd_dct = pd.read_pickle(path+name)
            dct['Rcvd Requests'].remove(name)
            dct['Friends'].add(name)
            frnd_dct['Friends'].add(USERNAME)
            dct['Chat'][name] = pd.DataFrame(columns=['time', 'usr', 'msg', 'isSeen'])
            frnd_dct['Chat'][USERNAME] = pd.DataFrame(columns=['time', 'usr', 'msg', 'isSeen'])
            pd.to_pickle(dct, path+USERNAME)
            pd.to_pickle(frnd_dct, path+name)
            client.send(s.enc('OKAY'))
    
    def get_friends(s, USERNAME, client):
        path = '../client_data/users/'
        dct = pd.read_pickle(path+USERNAME)
        frnds = dct['Friends']
        N = len(frnds)
        client.send(s.enc(N))
        for frnd in frnds:
            recv = s.dec(client.recv(32))
            if recv=='OK':
                flag = 'Friend' if frnd not in dct['Limited Friends'] else 'Special Friend'
                client.send(s.enc(frnd+' --- '+flag))
    #######################################################################

    ############## Chat and stuff #########################################

    def chk_act(s,USERNAME, client):
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
        client.send(s.enc(len(online)))
        for each in online:
            isOk = s.dec(client.recv(32))
            if isOk == 'OK':
                client.send(s.enc(each))

    def send_response(s,USERNAME, name, client):
        path = '../client_data/users/'
        dct = pd.read_pickle(path+USERNAME)
        usrdf = dct['Chat'][name]
        ln = len(usrdf)
        N = min(10, ln)
        client.send(s.enc(N))
        if N!=0:
            usrdf = usrdf.iloc[ln-N:ln]
            i = ln-N
            for ts, usr, msg, seen in zip(usrdf['time'], usrdf['usr'], usrdf['msg'], usrdf['isSeen']):
                isOk = s.dec(client.recv(32))
                if isOk == 'OK':
                    client.send(s.enc(ts+'---:'+usr+' : '+msg+': '+seen))
            frnd = pd.read_pickle(path+name)
            frnd['Chat'][USERNAME]['isSeen'] = 'Seen'
            pd.to_pickle(frnd, path+name)
            
        return client  
    
    def save_it(s, myself, myFriend, ts, mymsg, frmsg):
        path = '../client_data/users/'
        my = pd.read_pickle(path+myself)
        fr = pd.read_pickle(path+myFriend)
        my_l = len(my['Chat'][myFriend])
        fr_l = len(fr['Chat'][myself])
        if mymsg:
            my['Chat'][myFriend].loc[my_l, ['time','usr','msg','isSeen']] = [ts, 'Me', mymsg, 'Seen']
            fr['Chat'][myself].loc[fr_l, ['time','usr','msg','isSeen']] = [ts, myself, mymsg, 'Seen']
        elif frmsg:
            fr['Chat'][myself].loc[fr_l, ['time','usr','msg','isSeen']] = [ts, 'Me', frmsg,'Seen']
            my['Chat'][myFriend].loc[my_l, ['time','usr','msg','isSeen']] = [ts, myself, frmsg, 'Seen']
        pd.to_pickle(my, path+myself)
        pd.to_pickle(fr, path+myFriend)
        
    
    def live_chat(s, USERNAME, client):
        path = '../client_data/users/'
        dct = pd.read_pickle(path+USERNAME)
        usrs = glob(path+'*')
        if '\\' in usrs[0]:
            SPCHR = '\\'
        elif '/' in usrs[0]:
            SPCHR = '/'
        names = [usr.split(SPCHR)[-1] for usr in usrs]
        name = s.dec(client.recv(64))
        if not name in names:
            client.send(s.enc('NULL'))
        elif not name in dct['Friends']:
            client.send(s.enc('NOFRND'))
        else:
            other = clients[pairs[name]]
            if not box[pairs[USERNAME]] is None:
                client.send(s.enc('RECV'))
                print('Othe connection came in')
                isOK = s.dec(client.recv(32))
                if isOK == 'OK':
                    client.send(s.enc(box[pairs[USERNAME]]))
                    ts = str(datetime.datetime.now())
                    s.save_it(USERNAME, name, ts, None, box[pairs[USERNAME]])
                    box[pairs[USERNAME]] = None
                    print('Started middle man')
                    s.middle_man(client, other, USERNAME, name)
            else:
                client.send(s.enc('SEND'))
                resp = s.dec(client.recv(1024))
                print('Init saved. should wait')
                box[pairs[name]] = resp
                pd.to_pickle(True, 'lock.file')
                while pd.read_pickle('lock.file'):
                    sleep(1)
                    print('waiting')
                
    def middle_man(s, s1, s2, USERNAME, name):
        print('Middle man: Hi')
        resp = s.dec(s1.recv(1024))
        while resp != '@end@':
            s2.send(s.enc(resp))
            ts = str(datetime.datetime.now())
            s.save_it(USERNAME, name, ts, resp, None)
            resp = s.dec(s2.recv(1024))
            if resp == '@end@':
                break
            s1.send(s.enc(resp))
            ts = str(datetime.datetime.now())
            s.save_it(USERNAME, name, ts, None, resp)
            resp = s.dec(s1.recv(1024))
        s1.send(s.enc('@end@'))
        s2.send(s.enc('@end@'))
        pd.to_pickle(False, 'lock.file')
    
    def init_chat(s,USERNAME, client):
        path = '../client_data/users/'
        dct = pd.read_pickle(path+USERNAME)
        usrs = glob(path+'*')
        if '\\' in usrs[0]:
            SPCHR = '\\'
        elif '/' in usrs[0]:
            SPCHR = '/'
        names = [usr.split(SPCHR)[-1] for usr in usrs]
        name = s.dec(client.recv(64))
        if not name in names:
            client.send(s.enc('NULL'))
        elif not name in dct['Friends']:
            client.send(s.enc('NOFRND'))
        else:
            client.send(s.enc('OKAY'))
            isReady = s.dec(client.recv(32))
            if isReady == 'Ready':
                print('Client ready. Sending chat')
                client = s.send_response(USERNAME, name, client)
            resp = s.dec(client.recv(64))
            client.send(s.enc('OK'))
            while resp != 'FIN':
                if resp == 'REFRESH':
                    isReady = s.dec(client.recv(32))
                    if isReady == 'Ready':
                        client = s.send_response(USERNAME, name, client)
                elif resp == 'SNDMSG':
                    msg = s.dec(client.recv(512))
                    dct = pd.read_pickle(path+USERNAME)
                    frnd_dct = pd.read_pickle(path+name)
                    l_dct = len(dct['Chat'][name])
                    l_frnd_dct = len(frnd_dct['Chat'][USERNAME])
                    ts = str(datetime.datetime.now())
                    print('Current len of chat', l_dct, l_frnd_dct)
                    dct['Chat'][name].loc[l_dct, ['time','usr','msg','isSeen']] = [ts, 'Me', msg, 'NotSeen']
                    frnd_dct['Chat'][USERNAME].loc[l_frnd_dct, ['time','usr','msg','isSeen']] = [ts, USERNAME, msg, 'NotSeen']
                    pd.to_pickle(dct,path+USERNAME)
                    pd.to_pickle(frnd_dct,path+name)
                    client.send(s.enc('OK'))
                resp = s.dec(client.recv(64))
                client.send(s.enc('OK'))

    def sync(s, USERNAME, client):
        print('Starting sync')
        path = '../client_data/users/'
        offpath = '../client_data/users_offline/'
        isOk = s.dec(client.recv(32))
        print(isOk, 'received')
        ### send
        if isOk == 'OK':
            with open(path+USERNAME, 'rb') as f:
                while True:
                    data = f.read(1024)
                    print(data)
                    if not data:
                        break
                    client.send(data)
                    print('sent')
                    isOk = s.dec(client.recv(32))
                    if isOk != 'OK':
                        break
                client.send(s.enc('END'))
        else:
            print('Sync aborted')
        ### recv
        resp = s.dec(client.recv(32))
        if resp == 'SYNC2':
            client.send(s.enc('BEGIN'))
            with open(offpath+USERNAME+'_C', 'wb') as f:
                while True:
                    print('Grtting data')
                    data = client.recv(1024)
                    print(data)
                    if data == b'END':
                        print('End received')
                        client.send(s.enc('END'))
                        break
                    f.write(data)
                    client.send(s.enc('OK'))
                    print('OK sent')
                    
            try:
                pd.read_pickle(offpath+USERNAME+'_C')
                s.fixdiff(USERNAME)
            except PicklingError:
                print('FIle currupted. Abort')
    def fixdiff(s, USERNAME):
        path = '../client_data/users/'
        offpath = '../client_data/users_offline/'
        main = pd.read_pickle(path+USERNAME)
        cdict = pd.read_pickle(offpath+USERNAME+'_C')
        for usr in main['Chat']:
            frnd = pd.read_pickle(path+usr)
            main['Chat'][usr] = pd.concat([main['Chat'][usr], cdict['Chat'][usr]]).sort_values('time').drop_duplicates()
            df = pd.concat([main['Chat'][usr], cdict['Chat'][usr]]).sort_values('time').drop_duplicates()
            df['usr'] = df['usr'].replace({'Me':USERNAME}).replace({usr:'Me'})
            frnd['Chat'][USERNAME] = df
            pd.to_pickle(frnd, path+usr)
        pd.to_pickle(main, path+USERNAME)
        print('Diff fixed')
            
######### Listening

    def run(s): 
        USERNAME = None
        while True:
            client = clients[s.num]
            client.settimeout(3000)
            print('Receiving main action now from', s.ip, s.port, s.num)
            action = client.recv(512).decode()
            if action == 'SIGN_UP':
                client.send(s.enc('OK'))
                s.sign_up(client)
            elif action == 'LOG_IN':
                client.send(s.enc('OK'))
                USERNAME = s.log_in(client)
            elif action == 'LOG_OUT':
                client.send(s.enc('OK'))
                s.log_out(USERNAME, client)
                USERNAME = None
            elif action == 'POST':
                client.send(s.enc('OK'))
                s.post(USERNAME, client)
            elif action == 'CHKTIM':
                s.status_chk(USERNAME, client)
            elif action == 'VIEWTL':
                client.send(s.enc('OK'))
                s.view_tl(USERNAME, client)
            elif action == 'FEED':
                s.send_feed(USERNAME, client)
            elif action == 'SRCH':
                s.search_usr(USERNAME, client)
            elif action == 'ADDFRND':
                client.send(s.enc('OK'))
                s.add_frnd(USERNAME, client)
            elif action == 'SYNC':
                client.send(s.enc('BEGIN'))
                s.sync(USERNAME, client)
            elif action == 'ADDLIMITED':
                client.send(s.enc('OK'))
                s.add_to_limited(USERNAME, client)
            elif action == 'FOFF':
                client.send(s.enc('OK'))
                s.f_of_f(USERNAME, client)
            elif action == 'DELLIMITED':
                client.send(s.enc('OK'))
                s.del_from_limited(USERNAME, client)
            elif action == 'ACCFRND':
                client.send(s.enc('OK'))
                s.acc_rqst(USERNAME, client)
            elif action == 'DLTFRND':
                client.send(s.enc('OK'))
                s.dlt_frnd(USERNAME, client)
            elif action == 'GETFRND':
                s.get_friends(USERNAME, client)
            elif action == 'CHKACT':
                s.chk_act(USERNAME, client)
            elif action == 'CHAT':
                client.send(s.enc('OK'))
                s.init_chat(USERNAME, client)
            elif action == 'LIVECHAT':
                client.send(s.enc('OK'))
                s.live_chat(USERNAME, client)
                print('Initial server came back')
            else:
                print(action, 'Not matched with anything')
                break
        if USERNAME:
            path = '../client_data/users/'
            dct = pd.read_pickle(path+USERNAME)
            dct['isOnline'] = False
            pd.to_pickle(dct, path+USERNAME)
        print("EXIT :)")

hostname = socket.gethostname()
addr = socket.gethostbyname(hostname)
port = 12345 #int(sys.argv[1])
#caddr = sys.argv[2]
print(addr)
tcpServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
#tcpServer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
tcpServer.bind((addr, port)) 
threads = [] 
client_pairs = {}
clients = []

while True: 
    tcpServer.listen(4) 
    print("Multithreaded Python server : Waiting for connections from TCP clients...")
    (conn, (ip,port)) = tcpServer.accept() 
    #print('MainServer Connected with', ip, port)
    clients.append(conn)
    box.append(None)
    newthread = ServerThread(ip, port, len(clients)-1)
    newthread.start() 
    threads.append(newthread) 
 
for t in threads: 
    t.join() 
    
######### Methods
