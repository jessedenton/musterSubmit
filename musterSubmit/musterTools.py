'''
Created on 07/02/2013

@author: Jesse Denton
'''
import subprocess
import sqlite3
import os


MUSTER_LOCATION = r"\\SERVER\pra_server\PRA_Resource\Software\Muster"

MUSTER_ENV = os.getenv('Muster')
if not MUSTER_ENV:
    MUSTER_ENV = os.path.join(MUSTER_LOCATION, "Rollout\Muster6")

MUSTER_SERVER = '10.0.10.5'
MUSTER_PORT = '8681'
    

class MusterDatabase(object):
    
    
    MUSTER_DATABASE = os.path.join(MUSTER_LOCATION, "muster.db")
    
    def __init__(self, db = MUSTER_DATABASE):
        
        self._conn = sqlite3.connect(db)
        
    def getUsers(self):
        ''' returns list of muster users, ommits admin user'''
        
        with self._conn:
            cur = self._conn.cursor()
            cur.execute('SELECT username FROM db_users')
            users = cur.fetchall()
            
            return [x[0] for x in users if not "admin" in x]
        return list()

        
    def getPools(self):
        '''returns list of render pools'''
        
        with self._conn:
            cur = self._conn.cursor()
            cur.execute('SELECT pool_parent FROM db_pools')
            pools = cur.fetchall()
            
            return [x[0] for x in set(pools) if not x[0] == '']
        return list()
    
    
    def getUserPass(self, decode = True):
        '''returns dictionary of usernames and passwords'''
        
        with self._conn:
            cur = self._conn.cursor()
            cur.execute('SELECT username, encoded_password FROM db_users')
            feedback = cur.fetchall()
            
            if decode:
                import base64
                userPass = {}
                for data in feedback:
                    userPass[data[0]] = base64.decodestring(data[1])
                return userPass
                
            else:
                return dict(feedback)

        return dict()
        

        
        
class MusterTool(object):
    
    MRTOOL = os.path.join(MUSTER_ENV, 'mrtool')
    
    def __init__(self, user='admin', password = 'password'):
        self.server = MUSTER_SERVER
        self.port = MUSTER_PORT
        self._user = user
        self._password = password
    
    def checkConn(self):
        "Checks that the user can successfully connect to muster"
        
        cmd = ('"%s" -s %s -port %s -u %s -p %s -v 3 -b' % (MusterTool.MRTOOL, self.server, self.port, self._user, self._password))
        
        #open pipe
        mquery = os.popen(cmd, "r")       
        
        try:
            line = mquery.read()
            
            if line.find("Login succesfully") != -1:
                return [True, line]
            else:
                return [False, line]
            
        except:
            return None
        
        finally:
            try:
                mquery.close()
            except:
                pass
            
    def submit(self, cmd, verbosity=3):
        "Submit a command to muster, returns the output"     
        
        cmd = ('"%s" -s %s -port %s -u %s -p %s -v %d -b %s' % (MusterTool.MRTOOL, self.server, self.port, self._user, self._password, verbosity, cmd));
        print "sending to farm"
        print cmd
        
        #open pipe
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = subprocess.SW_HIDE
        
        proc = subprocess.Popen(cmd,
                               shell=False,
                               stdout=subprocess.PIPE,
                               startupinfo=info
                               )
        stdout_value = proc.communicate()[0]
        
        return stdout_value
            
        
    def createFld(self, parentId, name, priority=50):
        "Create a folder in muster, returns the id"
        
        cmd = ('"%s" -s %s -port %s -u %s -p %s -v 1 -b -folder -parent %d -n "%s" -pr %d' % (MusterTool.MRTOOL, self.server, self.port, self._user, self._password, parentId, name, priority));
       
        #open pipe
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = subprocess.SW_HIDE
        
        proc = subprocess.Popen(cmd,
                               shell=False,
                               stdout=subprocess.PIPE,
                               startupinfo=info
                               )
        
        #mquery = os.popen(cmd, "r")       
        
        try:
            stdout_value = proc.communicate()[0]
        
            #line = mquery.readline()
            #line = mquery.readline()
                    
            id = int(stdout_value.replace("new job has ID: ", ""))
            
            if id: return id
                            
        except:
            return None
        
        finally:
            try:
                mquery.close()
            except:
                pass
        
    def checkFld(self, parentId, name):
        "Check a folder exists in muster, returns the parent id"      
        
        cmd = ('"%s" -s %s -port %s -u %s -p %s -q j -jobparent %d -H 0 -C 0' % (MusterTool.MRTOOL, self.server, self.port, self._user, self._password, parentId));
        
        #open pipe
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = subprocess.SW_HIDE
        
        proc = subprocess.Popen(cmd,
                               shell=False,
                               stdout=subprocess.PIPE,
                               startupinfo=info
                               )
       
        try:
            stdout_value = proc.communicate()[0]
            splitLines = stdout_value.split("\n")
    
            for line in splitLines:
                line = line.replace(" ", "")    
                query = line.split("|")
            
                if len(query) > 1:
                    if query[1] == name: return int(query[0])
                    
        except:
            return None
        
        finally:
            try:
                mquery.close()
            except:
                pass
            
    def getTemplates(self):
        "Check a folder exists in muster, returns the parent id"      
        
        cmd = ('"%s" -s %s -port %s -u %s -p %s -q t' % (MusterTool.MRTOOL, self.server, self.port, self._user, self._password));
        
        #open pipe
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = subprocess.SW_HIDE
        
        proc = subprocess.Popen(cmd,
                               shell=False,
                               stdout=subprocess.PIPE,
                               startupinfo=info
                               )
       
        try:
            stdout_value = proc.communicate()[0]
            splitLines = stdout_value.split("\r\n")
    
            rtnDic = {}
            for line in splitLines:
                line = line.split("\t")
                
                if len(line) == 2:
                    if line[0] == '---' or line[0] == 'UID':
                        continue
                    rtnDic[line[1]] = line[0]
                    
            return rtnDic
                    
        except:
            return None
        
        finally:
            try:
                mquery.close()
            except:
                pass
    
    def updateUser(self, user, password):
        self._user = user
        self._password = password

