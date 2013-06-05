'''
Created on 07/02/2013

@author: Jesse Denton

Ui functions for muster submission. for use with Autodesk Maya

Example:

from musterSubmit import musterUI
win = musterUI.open()

TODO:
1. still having issue with "allLayers" on/off switch not updating when main ui created, FIXED 06/03/2013
2. check post copy executable file exists. if not don't show option.
3. check support for Linux and OSX
4. add support for more renderers. currently only major support for Mental Ray (located in MusterSubmit_Tabs, function <Submit>)
5. check scene file is not local and is accessible to renderfarm nodes
6. add logging function as muster doesn't remember id with file names. when files are deleted in muster their id is only shown.
7. fix public and private variables (i know this is for looks, cleaner code)
8. need scriptjob to update musterUI when layer name is changed using normal maya editor.

WISH LIST:
1. install pyqt4 for PRA so we dont have to use maya ui commands. 

WIP:
1. allow for multiple tab colours for different render cameras.
2. Create singleton for tab objects that works based on layer and camera. cleanup singleton for main ui. <NB.Recent implementation>
'''
#internal
import os
import os.path
import re
import itertools
#import logging

#projectSpecific
import projectTools as PT
import musterTools as MT

#maya specific
import pymel.core as pm 




POST_COPY_EXE = 'Z:/PRA_Resource/praDev_repo/trunk/Maya/pyScripts/mBkupSnd/muster_bkup_snd.exe'




def open():
    '''
    ensures the scene is saved prior to opening UI
    can be bypassed by creating instance of MusterSubmit class then running ui function
    '''
    if pm.sceneName() == '':
        check = pm.confirmDialog( title='Save', message='       Scene not saved.\nDo you wish to save it now?', 
                                  button=['Yes','No'], 
                                  defaultButton='Yes', 
                                  cancelButton='No', 
                                  dismissString='No' )
        if check == 'Yes':
            pm.runtime.SaveSceneAs()
            open() #re-run to make sure the user didn't cancel the save dialog
    else:
        win = MusterSubmit()
        win.ui()
        return win
        


class MusterSubmit(object):
    
    renderDrive = "O:" + os.sep
    
    defaults = {
                'department':'3D_Maya',
                'PostCopy':True,
                'packet':2,
                'priority':50
                }
                
    _colours = {
                'red' : [[0.29,0.19,0.19],[0.38,0.28,0.28]],
                'green' : [[0.19,0.29,0.19],[0.28,0.38,0.28]],
                }
                
    def __init__(self):
        self.name = "MusterSubmitClass"
        self.widgets = {}
        self.pools = []
        self.userPass = {}
        self.renderers = []
        self.cameras = pm.ls(ca = True)
        self.scene = pm.sceneName()
        self.priority = self.__class__.defaults['priority']
        self.childrenTabs = []
        
        self.startFrame = pm.SCENE.defaultRenderGlobals.startFrame.get()
        self.endFrame = pm.SCENE.defaultRenderGlobals.endFrame.get()
        
        self.mustertool = None
        
        self._saveUser = None
        self._saveRenderer = None
        self._savePool = None
        
        self.fileInfo = PT.PRAFileInfo(self.scene)
        try:
            self.output = os.path.join(self.__class__.renderDrive, self.fileInfo.getProject(), self.fileInfo.getEpShotName()).replace("\\","/")
        except TypeError: #file info returned None
            self.output = ''
        
        try:
            self._getData() #this bit is slow. use threadding maybe?
        except:
            pm.confirmDialog(title = "Confirm", Message = "Error connecting to muster database / executable. Speak to your IT helpdesk. \nContinuing using Demo mode", buttonm = ['OK'] )
    
       
    def __repr__(self):
        return "<%s(MainUI) object id (%d)>" % (self.__class__.__name__, id(self))
        
    def _getData(self):
        '''gets data provided by muster database and exe'''
        
        db = MT.MusterDatabase()
        self.pools = db.getPools()
        self.userPass = db.getUserPass()

            
        if self.userPass.items() and 'admin' in self.userPass.keys():
            password = self.userPass.pop('admin', None)
            self.mustertool = MT.MusterTool('admin', password)
        else:
            self.mustertool = MT.MusterTool()
        
        if self.mustertool.checkConn()[0]:
            self.renderers = self.mustertool.getTemplates()

    def ui(self):
        '''
        main ui creator
        '''
        #TODO: only run once. use singleton instance
        
        if pm.window(self.name, q = True, ex = True):
            pm.deleteUI(self.name)
            
        #main window
        self.widgets['mainWindow'] = pm.window(self.name, title = self.name, widthHeight = (720, 400))
        self.widgets['mainForm']   = pm.formLayout(parent = self.widgets['mainWindow'])
        
        #top left column
        self.widgets['topLColumn'] = pm.columnLayout(adjustableColumn = True, parent = self.widgets['mainForm'], h = 168)
        self.widgets['cameraText'] = pm.text(label = "Cameras", h = 20)
        self.widgets['cameraList'] = pm.iconTextScrollList(h = 105, allowMultiSelection = True, selectCommand = pm.Callback(self.updateLayers))
        self.widgets['nameSep']    = pm.separator(horizontal = True, style = 'none', h = 13)
        self.widgets['sceneName']  = pm.textFieldGrp(label = 'Scene Name', text = self.scene.namebase, adjustableColumn = 2, columnWidth2 = [80, 0])
        
        #top right column
        self.widgets['topRColumn'] = pm.columnLayout(parent = self.widgets['mainForm'], h = 168, adjustableColumn = True, rowSpacing = 1)
        self.widgets['outputDir']  = pm.textFieldButtonGrp(label = 'Output Path', tx = self.output, adjustableColumn = 2, columnWidth = [1, 80], buttonLabel = 'Browse...', bc = pm.Callback(self.changeOutputDestination))
        self.widgets['project']    = pm.textFieldGrp(label = 'Project', adjustableColumn = 2, columnWidth = [1, 80], text = self.fileInfo.getProject())
        self.widgets['department'] = pm.textFieldGrp(label = 'Department', adjustableColumn = 2, columnWidth = [1, 80], text = MusterSubmit.defaults['department'])
        self.widgets['pool']       = pm.optionMenuGrp(label = 'Pool', adjustableColumn = 2, columnWidth = [1, 80], cc = pm.Callback(self.savePoolOpt))
        self.widgets['renderer']   = pm.optionMenuGrp(label = 'Renderer', adjustableColumn = 2, columnWidth = [1, 80], cc = pm.Callback(self.saveRendererOpt))
        self.widgets['user']       = pm.optionMenuGrp(label = 'User', adjustableColumn = 2, columnWidth = [1, 80], cc = pm.Callback(self.saveUserOpt))
        self.widgets['memPri']     = pm.rowLayout(parent = self.widgets['topRColumn'], numberOfColumns = 2, adjustableColumn2 = 1)
        self.widgets['memory']     = pm.intSliderGrp(parent = self.widgets['memPri'], label = 'Memory', columnWidth = [1,80], field = True, step = 512, value = 16384, maxValue = 65536, minValue = 512, w = 200)
        self.widgets['priority']   = pm.intFieldGrp(parent = self.widgets['memPri'], label = 'Priority', columnWidth = [1,50], value1 = self.priority)
        
        #top middle row
        self.widgets['topMRow']    = pm.rowLayout(parent = self.widgets['mainForm'], numberOfColumns = 6, adjustableColumn6 = 3)
        self.widgets['sep']        = pm.separator(style = "none", w = 15)
        self.widgets['allLayers']  = pm.checkBox(label = 'All Layers', w = 110, value = True, cc = pm.Callback(self.setAllRenderable))
        self.widgets['postCopy']   = pm.checkBox(label = 'Post Copy', w = 100, value = True)
        self.widgets['byFrame']    = pm.intFieldGrp(label = 'By Frame', columnWidth = [1, 50], value1 = int(pm.SCENE.defaultRenderGlobals.byFrame.get()))
        self.widgets['padding']    = pm.intFieldGrp(label = 'Padding', columnWidth = [1, 50], value1 = int(pm.SCENE.defaultRenderGlobals.extensionPadding.get()))
        self.widgets['packet']     = pm.intFieldGrp(label = 'Packet', columnWidth = [1, 50], value1 = int(MusterSubmit.defaults['packet']))
        
        #main layout
        self.widgets['scrollLayout'] = pm.scrollLayout(parent = self.widgets['mainForm'], childResizable = True)
                
        #bottom row
        self.widgets['bottomRow'] = pm.rowLayout(numberOfColumns = 3, parent = self.widgets['mainForm'], adjustableColumn = 1)
        self.widgets['progress']  = pm.progressBar(w = 300, progress = -1)
        self.widgets['paused']    = pm.checkBox(label = 'Paused', w = 60)
        self.widgets['Submit']    = pm.button(label = 'Submit', w = 150, c = pm.Callback(self.submit))
        
        #form Layout
        self.widgets['mainForm'].attachForm(self.widgets['topLColumn'], 'top', 0)
        self.widgets['mainForm'].attachForm(self.widgets['topLColumn'], 'left', 0)
        self.widgets['mainForm'].attachNone(self.widgets['topLColumn'], 'bottom')
        self.widgets['mainForm'].attachPosition(self.widgets['topLColumn'], 'right', 0, 40)
        
        self.widgets['mainForm'].attachForm(self.widgets['topRColumn'], 'top', 0)
        self.widgets['mainForm'].attachControl(self.widgets['topRColumn'], 'left', 0, self.widgets['topLColumn'])
        self.widgets['mainForm'].attachNone(self.widgets['topRColumn'], 'bottom')
        self.widgets['mainForm'].attachForm(self.widgets['topRColumn'], 'right', 0)
        
        self.widgets['mainForm'].attachControl(self.widgets['topMRow'], 'top', 0, self.widgets['topRColumn'])
        self.widgets['mainForm'].attachForm(self.widgets['topMRow'], 'left', 0)
        self.widgets['mainForm'].attachNone(self.widgets['topMRow'], 'bottom')
        self.widgets['mainForm'].attachForm(self.widgets['topMRow'], 'right', 0)
        
        self.widgets['mainForm'].attachControl(self.widgets['scrollLayout'], 'top', 0, self.widgets['topMRow'])
        self.widgets['mainForm'].attachForm(self.widgets['scrollLayout'], 'left', 0)
        self.widgets['mainForm'].attachControl(self.widgets['scrollLayout'], 'bottom', 0, self.widgets['bottomRow'])
        self.widgets['mainForm'].attachForm(self.widgets['scrollLayout'], 'right', 0)
        
        self.widgets['mainForm'].attachNone(self.widgets['bottomRow'], 'top')
        self.widgets['mainForm'].attachForm(self.widgets['bottomRow'], 'left', 0)
        self.widgets['mainForm'].attachForm(self.widgets['bottomRow'], 'bottom', 0)
        self.widgets['mainForm'].attachForm(self.widgets['bottomRow'], 'right', 0)
        #end form layout
        
        self._populateUI()
        
        pm.scriptJob(uiDeleted = [self.widgets['mainWindow'].name(), pm.Callback(self.saveUI)])                           #saves ui settings to optionVar
        pm.scriptJob(e = ['renderLayerChange', pm.Callback(self.updateLayers)], p = self.widgets['mainWindow'].name())    #reloads layers scroll when a layer is created or deleted

        #show created ui
        self.widgets['mainWindow'].show()
        self.getOptionVars()
        
    def _populateUI(self):
        '''run once to populate ui objects after their initial creation'''
        
        #cameras list
        self.widgets['cameraList'].removeAll()
        for cam in self.cameras:
            self.widgets['cameraList'].append(cam.name())
            if cam.renderable.get():
                self.widgets['cameraList'].setSelectItem(cam.name())
        
        #pools list        
        if self.pools:
            for pool in sorted(self.pools):
                pm.menuItem(label = pool, parent = (self.widgets['pool'] + '|OptionMenu'))
        
        #users list         
        if self.userPass:
            for user in sorted(self.userPass.keys()):
                pm.menuItem(label = user, parent = (self.widgets['user'] + '|OptionMenu'))
                
            compUser = os.getenv('USER') or os.getenv('USERNAME') #returns None if it does not exist
            if compUser in self.userPass.keys():
                self.widgets['user'].setValue(compUser)
        
        #renderers list         
        if self.renderers:
            for ren in sorted(self.renderers.keys()):
                pm.menuItem(label = ren, parent = (self.widgets['renderer'] + '|OptionMenu'))
            
        #layers list
        self.updateLayers()
                
    def updateLayers(self):
        '''refreshes layer scroll layout and children tabs'''
        
        allLayers = pm.nodetypes.RenderLayer.listAllRenderLayers()

        self.widgets['scrollLayout'].clear()

        self.childrenTabs = [] #empty children tabs
        
        colour = itertools.cycle(MusterSubmit._colours['red']) #create infinite colours iterator
        selectedCams = self.widgets['cameraList'].getSelectItem()
        
        onLayers = [x for x in allLayers if x.renderable.get()] #prioritize renderable layers tab creation. 
        offLayers = list(set(allLayers) - set(onLayers))
        allLayers = onLayers + offLayers
        
        if len(offLayers):
            self.widgets['allLayers'].setValue(False)
        
        if selectedCams:
            for layer in allLayers:
                for cam in selectedCams:
                    tab = MusterSubmit_Tabs(self, pm.PyNode(cam), layer, colour.next())
                    tab.build()
                    self.childrenTabs.append(tab)
                    
        self._updateSiblings()
                    
    def _updateSiblings(self):
        '''recursively search layers to update siblings variable'''
        #TODO: There must be a better way.
        for child in self.childrenTabs:
            for childListTwo in self.childrenTabs:
                if childListTwo.layer is child.layer:
                    child.siblings.append(childListTwo)
                    
    def changeOutputDestination(self, dest = None):
        '''updates the output location for muster renders'''
        #TODO: check access to proposed render location location
        if not dest:
            dest = pm.fileDialog2(fileMode = 3, dialogStyle = 1, startingDirectory = self.widgets['outputDir'].getFileName())
        if dest:
            self.widgets['outputDir'].setText(pm.Path(dest[0]))
                    
    def submit(self):
        '''
        Main ui submit function. 
        gets global options used for all render layers, passed to each tab object.
        creates folders for muster organisation.
        '''
        if not self.mustertool:
            raise RuntimeError, "couldn't find the muster tool for submission"
        
        if not self.mustertool.checkConn(): #TODO: currently only admin user returns connection success. need to check muster setup.
            raise RuntimeError, "could not connect to muster"
        
        sceneName =  self.widgets['sceneName'].getText()
        if not sceneName:
            raise NameError, "Scene does not have a name"
        
        outputDir = self.widgets['outputDir'].getText()
        if not outputDir:
            raise NameError, "No output location specified"
        
        renderableTabs = [x for x in self.childrenTabs if x.renderable]
            
        user = self.widgets['user'].getValue()
        password = self.userPass[user]
        self.mustertool.updateUser(user, password)
        
        self.widgets['progress'].setMaxValue(len(renderableTabs) + 2) #additional two steps used for folder creation.
        self.widgets['progress'].setProgress(0)
        
        project = self.widgets['project'].getText()
        
        projectFldId = self.mustertool.checkFld(-1, project)
        if not projectFldId:
            print 'creating project folder: %s' % project
            projectFldId = self.mustertool.createFld(-1, project)
            
        self.widgets['progress'].step()
        
        sceneFldId = self.mustertool.checkFld(projectFldId, sceneName)
        if not sceneFldId:
            print 'creating project folder: %s' % sceneName
            sceneFldId = self.mustertool.createFld(projectFldId, sceneName, priority = self.widgets['priority'].getValue1())
            
        self.widgets['progress'].step()
            
        globalCmds  = ''                                                                    #Batch Submit 
        globalCmds += '-e %s ' % self.renderers[self.widgets['renderer'].getValue()]        #Engine template ID       (MANDATORY)
        globalCmds += '-pr 50 '                                                             #Priority
        globalCmds += '-pk %s ' % self.widgets['packet'].getValue1()                        #Packet
        globalCmds += '-bf %s ' % self.widgets['byFrame'].getValue1()                       #By frame                 (MAPS TO by_frame VALUE)
        globalCmds += '-st %s ' % self.widgets['byFrame'].getValue1()                       #Numbering step           (MAPS TO step_by VALUE)
        globalCmds += '-f "%s" ' % self.scene                                               #Job file                 (MAPS TO job_file VALUE)
        globalCmds += '-proj "%s" ' % pm.workspace(q = True, active = True)                 #Project path             (MAPS TO job_project VALUE)
        globalCmds += '-dest "%s" ' % outputDir                                             #Frames destination       (MAPS TO output_folder VALUE
        globalCmds += '-pool "%s" ' % self.widgets['pool'].getValue()                       #Destination Pool
        globalCmds += '-group "%s" ' % project                                              #Job Group                (formerly job project) 
        globalCmds += '-parent %s ' % sceneFldId                                            #Parent ID
        globalCmds += '-department %s ' % self.widgets['department'].getText()              #Job department
        globalCmds += '-attr MAYADIGITS %s 0 ' %self.widgets['padding'].getValue1()         #Padding
        
        if self.widgets['paused'].getValue():
            globalCmds += '-ojs 2 '                                                         #Override job status      (0 - Disabled, 1 - Idle, 2 - Paused)
            
        if self.widgets['postCopy'].getValue():
            globalCmds += '-eca "%s ' % POST_COPY_EXE                                       #Post-chunk action
            globalCmds += '%ATTR(output_folder)" '                                          #Flags added to Post-chunk action script
            globalCmds += '-ecart 0 '                                                       #Post-chunk expected return code
            
        for layer in renderableTabs:
                layer.submit(cmds = globalCmds, memoryLimit = self.widgets['memory'].getValue())
                self.widgets['progress'].step()
                
        self.widgets['progress'].setProgress(0)
        
    def setAllRenderable(self):
        '''toggle all renderable layers on/off'''
        value = self.widgets['allLayers'].getValue()
        for child in self.childrenTabs:
            child.widgets['renderable'].setValue(value)
            child.layer.renderable.set(value)
            child.setRenderableState(value)
            child.renderable = value
            
    def checkAllRenderable(self):
        '''toggles all layers checkbox on/off depending on childern tabs'''
        
        if len([x for x in self.childrenTabs if x.renderable == True]) == len(self.childrenTabs):
            self.widgets['allLayers'].setValue(1)
        else:
            self.widgets['allLayers'].setValue(0)
            
    def saveUserOpt(self):
        '''run when option menu "user" has been changed'''
        self._saveUser = self.widgets['user'].getValue()
        
    def saveRendererOpt(self):
        '''run when option menu "renderer" has been changed'''
        self._saveRenderer = self.widgets['renderer'].getValue()
        
    def savePoolOpt(self):
        '''run when option menu "pool" has been changed'''
        self._savePool = self.widgets['pool'].getValue()
            
    def saveUI(self):
        '''saves current selected pool, renderer and user into option variables. re-used when loading UI'''
        print "Saving data for reloading Muster Submit UI"
        pm.optionVar['musterSubmitPool'] = self._savePool
        pm.optionVar['musterSubmitRenderer'] = self._saveRenderer
        pm.optionVar['musterSubmitUser'] = self._saveUser
        
    def getOptionVars(self):
        '''reload option variables into current ui'''
        
        if 'musterSubmitPool' in pm.optionVar.keys():
            try:
                self.widgets['pool'].setValue(pm.optionVar['musterSubmitPool'])
            except:
                pass
        
        if 'musterSubmitRenderer' in pm.optionVar.keys():
            try:
                self.widgets['renderer'].setValue(pm.optionVar['musterSubmitRenderer'])
            except:
                pass
        
        if 'musterSubmitUser' in pm.optionVar.keys():
            try:
                self.widgets['user'].setValue(pm.optionVar['musterSubmitUser'])
            except:
                pass
            
    @staticmethod
    def getMusterToolLocation():
        return os.path.join(MT.MUSTER_ENV, 'mrtool')
    
    @classmethod
    def updateColours(cls, **kwargs):
        '''change the colours used for muster ui'''
        #TODO: run check on value of kwarg. should only accept tupple (float, float, float) as a list.
        
        for value in kwarg.values():
            pass
            #checkColour(value)
        
        update = [x for x in cls._colours.keys() if x in kwargs.keys()]
        
        for oldKey in update:
            print "%s.. updating colours: %s = %s" % (cls.__name__, oldKey, kwargs[oldKey])
            cls._colours[oldKey] = kwargs[oldKey]
            kwargs.pop(oldKey)
        
        for newKey, value in kwargs.iteritems():
            print "%s.. adding colours: %s = %s" % (cls.__name__, newKey, value)
            cls._colours[newKey] = value
            

class MusterSubmit_Tabs(object):
    #__metaclass__ = Singleton
    #singleton should be based on camera and layer. 
    
    rangeCheck = re.compile(r'[\d-]+')
    
    def __init__(self, parent, camera, layer, bgc):

        self.parent = parent
        self.camera = camera
        self.layer = layer
        self.bgc = bgc
        
        self.renderable = True
                
        self.widgets = {}
        self.siblings = []
        
    def __repr__(self):
        return '%s(%s_%s)' % (self.__class__.__name__, self.camera.getParent().stripNamespace(), self.layer.name())
        
    def build(self):
        '''builds ui objects for tab'''
        self.widgets['mainRow'] = pm.rowLayout(parent = self.parent.widgets['scrollLayout'], numberOfColumns = 6, h = 50, adjustableColumn = 3, bgc = self.bgc)
        self.widgets['frontSpacer'] = pm.separator(style = 'none', w = 12)
        self.widgets['renderable'] = pm.checkBox(parent = self.widgets['mainRow'], value = self.layer.renderable.get(), w = 50, label = "", cc = pm.Callback(self.updateRenderable))
        self.widgets['cameraName'] = pm.text(parent = self.widgets['mainRow'], label = self.camera.getParent().stripNamespace(), w = 140)
        self.widgets['layerName'] = pm.iconTextButton(parent = self.widgets['mainRow'], label = self.layer.name(), w = 220, style = 'textOnly', c = pm.Callback(self.layer.setCurrent), dcc = pm.Callback(self.updateLayerName))
        self.widgets['frameRange'] = pm.textFieldGrp(parent = self.widgets['mainRow'], text = '%d - %d' % (self.parent.startFrame, self.parent.endFrame))
        self.widgets['backSpacer'] = pm.separator(style = 'none', w = 1)
        
        if not self.layer.renderable.get():
            self.updateRenderable()
            
    def updateLayerName(self):
        '''change layer name'''
        currentText = self.widgets['layerName'].getLabel()
        if currentText == 'defaultRenderLayer':
            return
        result = pm.promptDialog(title='Update layer Name', message='New name:', text = currentText, button=['OK', 'Cancel'], defaultButton='OK', cancelButton='Cancel', dismissString='Cancel')
        if result == 'OK':
            newName = pm.promptDialog(query = True, text = True)
            if not self.checkName(newName):
                print "Crap name mate. Try again"
                
            else:
                #self.widgets['layerName'].setLabel(newName)
                for sibling in self.siblings:
                    sibling.widgets['layerName'].setLabel(newName)
                self.layer.rename(newName)
    
    @staticmethod            
    def checkName(name):
        '''checks name is legible and contains characters accepted by Autodesk Maya'''
        #TODO: implement
        return True
                       
    def updateRenderable(self):
        '''updates instantce variables once layers' renderable state changes'''
        value = self.widgets['renderable'].getValue()
        self.setRenderableState(value)
        self.renderable = value
        
        #check sibling have the same renderable state before turning off
        if len([x for x in self.siblings if x.renderable == value]) == len(self.siblings):
            self.layer.renderable.set(value)
        
        self.parent.checkAllRenderable()
        
    def setRenderableState(self, value = False):
        '''set ui visibility features when layer is turned on/off'''
        self.widgets['frameRange'].setEnable(value)
        self.widgets['layerName'].setEnable(value)
        self.widgets['cameraName'].setEnable(value)
        
    def submit(self, cmds = None, memoryLimit = None):
        '''
        tab object level submit.
        Takes global commands from main ui submit function. 
        allows for multiple frame submission
        '''
        ranges = self.widgets['frameRange'].getText().replace(' ','')
        keepCmds = cmds
        for job in self.__class__.rangeCheck.findall(ranges):
            frames = job.split('-')
            size = len(frames)
            if size > 2:
                print "problem with layer string, return usage"
            
            if size == 1:
                cmds += '-sf %s ' % frames[0]
                cmds += '-ef %s ' % frames[0]
                cmds += '-se %s ' % frames[0]
                
            if size == 2:
                cmds += '-sf %s ' % frames[0]
                cmds += '-ef %s ' % frames[1]
                cmds += '-se %s ' % frames[0]
               
            renderSpecificFlags  = ''
            renderSpecificFlags += '-rl %s ' % self.layer
            renderSpecificFlags += '-cam %s ' % self.camera
            if memoryLimit:
                renderSpecificFlags += '-mem %s ' % memoryLimit
            
            cmds += '-add "%s" ' %  renderSpecificFlags
            cmds += '-n "%s_%s"' % (self.layer.name() , self.camera.getParent().stripNamespace())
            
            rtn = self.parent.mustertool.submit(cmds, verbosity = 1)
            print rtn
            print '-'*90
            cmds = keepCmds
            
            
class MusterTest(MusterSubmit):
    '''Testing inheritance, ignore'''
    def __init__(self):
        MusterSubmit.__init__(self)
        

