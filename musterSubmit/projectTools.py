'''
Created on 07/02/2013

@author: Jesse Denton
'''

import os
import os.path

class PRAFileInfo(object):
    '''
    class that breaks a full path name down into its identifiable folders
    Using the split method from a full path name to return details.
    
    NB: this is not how I would usually create a fileInfo API.
    This is what i was asked for my the studio tech lead. its quick to write.
    
    Example useage:
    scenePath = r"Z:/Projects/1218_FN_Webisodes/Ep_03/ep03_seq17/3D_scenes/Lighting/seq_17_Lighting_v02.mb"
    myFile = PRAFileInfo(scenePath)
    print myFile.getProjectLocation()
    >>> "Z:/Projects"
    '''
    def __init__(self, path):
        
        self._path = path.replace("\\","/")
        
        self.fullPathType = False
        if "/" in self._path:
            self.fullPathType = True
            
        self.name, self.ext = os.path.splitext(self._path)
        self.name = os.path.basename(self.name)
            
        self.infoList = self._path.split("/")
            
       
    def getProjectLocation(self):
        '''returns project location'''
        if self.fullPathType:
            try:
                return ''.join(x + os.sep for x in self.infoList[0:2])[:-1]
            except:
                pass
        return None
    
    def getProject(self):
        '''returns project name'''
        if self.fullPathType:
            try:
                return self.infoList[2]
            except:
                pass
        return None
        
    def getEpisode(self):
        '''returns episode name'''
        if self.fullPathType:
            try:
                return self.infoList[3]
            except:
                pass
        return None
    
    def getShotName(self):
        '''returns shot sequence name'''
        if self.fullPathType:
            try:
                return self.infoList[4]
            except:
                pass
        return None
    
    def getEpShotName(self):
        '''returns episode and shotName joined'''
        if self.fullPathType:
            try:
                return ''.join(x + os.sep for x in self.infoList[3:5])[:-1]
            except:
                pass
        return None
    
    def getDepartment(self):
        '''returns given files' department'''
        if self.fullPathType:
            try:
                return self.infoList[6]
            except:
                pass
        return None