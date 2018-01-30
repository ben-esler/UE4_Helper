###############################################
# Ben Esler                        10/11/2017 #
#                                             #
#                                             #
# Grid UI is based off                        #
# Joch Buck's jbu3grid v1.5 for UDK           #
###############################################

import maya.cmds as cmds
import maya.mel as mel
import ConfigParser
import operator
from os import path, listdir
from functools import partial

UE4HELPER_VERISION = 0.9 
UE4HELPER_SETTINGSPATH = cmds.internalVar(userPrefDir=True) + '/UE4Helper.ini'


class Settings(ConfigParser.RawConfigParser):
    def __init__(self, version, settingsPath):
        ConfigParser.RawConfigParser.__init__(self)
        self.version = version
        self.path = settingsPath
        #Checks if UE4Helper.ini exsits
        if not path.isfile(settingsPath):
            print('No Settings File Found')
            self._createDefaultConfig()
        #Parser reads in values from UE4Helper.ini
        self.readfp(open(self.path))
        #Checks if UE4Helper.ini is correct version
        if self.getfloat('Info', 'version') != version:
            print('Tool version and Settings File version do not match')
            self._createDefaultConfig()

    def _createDefaultConfig(self):
        """
        Creates default config and calls _updateConfigFile() to write file
        """
        print('Creating new Settings File')
        for section in self.sections():
            self.remove_section(section)
        self.add_section('Info')
        self.set('Info', 'version', self.version)
        self.add_section('settings')
        self.set('settings', 'modelRefDir', '')
        self.set('settings', 'exportDir', '')
        self.set('settings', 'exportFBX', 'true')
        self.set('settings', 'exportOBJ', 'false')
        self.set('settings', 'centerMeshes', 'true')
        self._updateConfigFile()

    def _updateConfigFile(self):
        """
        Writes current config to Pref/UE4Helper.ini
        """
        configFile = open(self.path, 'w')
        self.write(configFile)
        configFile.close()

    def updateConfig(self, menuRef, setting, *args):
        """
        Updates config and calls _updateConfigFile() to write file
        """
        menuLabel = cmds.menuItem(menuRef, q=True, l=True)
        #CheckBox Buttons
        if cmds.menuItem(menuRef, q=True, icb=True):
            #Parser requires lower case true and false to work
            value = str(cmds.menuItem(menuRef, q=True, cb=True)).lower()
        #Directory Buttons
        else:
            #Try is here incase the user cancels selecting a directory
            try:
                value = cmds.fileDialog2(ds= 2, fm = 3)[0] + '/'
            except TypeError:
                return 'canceled'
        #Sets and saves new values
        self.set('settings', setting, value)
        cmds.menuItem(menuRef, edit=True, ann=menuLabel + " - " + str(value))
        self._updateConfigFile()

    def referenceMeshes(self):
        """
        Finds all the files in the model reference directory that is a mesh.

        Returns:
            List of strings containing the filenames with extensions
        """
        #Checks if reference directory is set
        if not self.get('settings', 'modelrefdir'):
            return
        dirPath = self.get('settings', 'modelrefdir')
        if not path.isdir(dirPath):
            return []
        referenceFiles = []
        for file in listdir(dirPath):
            if any(file.endswith(ext) for ext in ['.fbx','.obj','.abc','.dae']):
                referenceFiles.append(file)
        return referenceFiles


class UE4Helper(object):
    def __init__(self):
        self._settings = Settings(version=UE4HELPER_VERISION, settingsPath=UE4HELPER_SETTINGSPATH)
        self._howToUse = UE4HelperHowToUse()
        self._buildUi()
        self._setupSettingsUi()
        mel.eval('FBXExportSmoothingGroups -v true')

    def _buildUi(self):
        #check to make sure window is not already open
        if cmds.window("UE4Helper", exists = True):
            cmds.deleteUI("UE4Helper")
        self._window = cmds.window("UE4Helper", t="UE4 Helper", mb=True, w=208, h=290,
                                mnb=False, mxb=False, s=False, rtf=True)
        #Menus
        #Create a function to auto generate the menus based off the settings / .ini file
        cmds.menu(l='Settings')
        self._menuModelRefDir = cmds.menuItem(l='Reference Folder')
        cmds.menuItem(self._menuModelRefDir, edit=True,
            c=partial(self._setReferenceFolder))
        cmds.menuItem(l='Refresh References',c=partial(self._updateReferenceUi))
        cmds.menuItem(d=True)
        self._menuExportDir = cmds.menuItem(l='Export Folder')
        cmds.menuItem(self._menuExportDir, edit=True,
            c=partial(self._settings.updateConfig,self._menuExportDir, 'exportDir'))
        self._menuExportFBX = cmds.menuItem(l='Export FBX', cb=False)
        cmds.menuItem(self._menuExportFBX, edit=True,
            c=partial(self._settings.updateConfig,self._menuExportFBX, 'exportFBX'))
        self._menuExportOBJ = cmds.menuItem(l='Export OBJ', cb=False)
        cmds.menuItem(self._menuExportOBJ, edit=True,
            c=partial(self._settings.updateConfig,self._menuExportOBJ, 'exportOBJ'))
        self._menuCenterMeshes = cmds.menuItem(l='Center Meshes', cb=False)
        cmds.menuItem(self._menuCenterMeshes, edit=True,
            c=partial(self._settings.updateConfig,self._menuCenterMeshes, 'centerMeshes'))

        cmds.menu(l='Help', hm=True)
        cmds.menuItem(l='How to Use', c=self._howToUse.toggle)
        cmds.menuItem(l='About', c=partial(self.helpAbout))
        #organize the GUI with some kind of layout
        cmds.columnLayout(cw=194, columnOffset=["both",5])
        #Set Grid
        cmds.rowLayout(nc=2)
        cmds.button(l="UE4 Grid", w=95, c=partial(self.setGridUE4))
        cmds.button(l="Default Grid",w=95, c=partial(self.setGridDefault))
        cmds.setParent('..')
        #Set Grid Spacing
        cmds.rowLayout(nc=5)
        self._gridCollection = cmds.radioCollection()
        self._gridRadio1 = cmds.radioButton(l='1', onc='maya.cmds.grid(spacing=1)')
        self._gridRadio5 = cmds.radioButton(l='5', onc='maya.cmds.grid(spacing=5)')
        self._gridRadio10 = cmds.radioButton(l='10', onc='maya.cmds.grid(spacing=10)')
        self._gridRadio50 = cmds.radioButton(l='50', onc='maya.cmds.grid(spacing=50)')
        self._gridRadio100 = cmds.radioButton(l='100', onc='maya.cmds.grid(spacing=100)')
        cmds.radioCollection( self._gridCollection, e=True, select=self._gridRadio10)
        cmds.setParent('..')
        #Adjust grid Scale
        cmds.rowLayout(nc=2)
        cmds.button(l="Larger", w=95, c=partial(self._adjustGridScale,50))
        cmds.button(l="Smaller", w=95, c=partial(self._adjustGridScale,-50))
        cmds.setParent('..')
        cmds.separator(w=194, h=20, st="double")
        #Reference Import
        cmds.rowLayout(nc=2)
        self._refOptionMenu = cmds.optionMenu(w=140, h=25)
        cmds.menuItem(l='Set Reference Folder')
        cmds.button(l="Import", w=50, c=partial(self._importReference))
        cmds.setParent('..')
        cmds.separator(w=194, h=5, st="none")
        #Rename Mesh
        self._renameMeshText = cmds.textField(
            tx="                 Rename Mesh", w=194, h=25,
            ann='Renames last selected object',
            cc=partial(self._renameMesh), rfc=partial(self._clearRenameMeshText))
        cmds.separator(w=194, h=5, st="none")
        #Assign assignLODs
        cmds.button(l="Assign LODs", w=194, 
          ann='Select meshes and click', 
          c=partial(self.assignLODs))
        cmds.separator(w=194, h=5, st= "none")
        #Assign Collision
        cmds.button(l="Assign Collision", w=194, 
          ann='Select collision meshes, then target mesh and click', 
          c=partial(self.assignCollision))
        cmds.separator(w=194, h=5, st="none")
        #Export
        cmds.button(l="Export", w=194, c=partial(self.export))
        cmds.separator(w=194, h=5, st= "none")
        #Length Converter
        cmds.frameLayout( l='Unit Converter', cll=1, w=194, cl=1,
            cc=partial(cmds.window, self._window, e=True, w=208, h=290),
            ec=partial(cmds.window, self._window, e=True, w=208, h=335))
        cmds.rowColumnLayout(nc=3, cw=[(1, 87), (2, 20), (3, 87)])
        self._unit1Val = cmds.textField("ConvertValue1",ec=partial(self._convertUnits,True))
        cmds.text(l="=")
        self._unit2Val = cmds.textField("ConvertValue2",ec=partial(self._convertUnits,False))
        cmds.separator(h=5, st="none")
        cmds.separator(h=5, st="none")
        cmds.separator(h=5, st="none")
        self._unit1Option = cmds.optionMenu(cc=partial(self._convertUnits,False))
        cmds.menuItem(l='Millimeter')
        cmds.menuItem(l='Centimeter')
        cmds.menuItem(l='Meter')
        cmds.menuItem(l='Kilometer')
        cmds.menuItem(l='Inch')
        cmds.menuItem(l='Foot')
        cmds.menuItem(l='Yard')
        cmds.menuItem(l='Mile')
        cmds.optionMenu(self._unit1Option, e=True, value='Inch')
        cmds.text(l="to")
        self._unit2Option = cmds.optionMenu(cc=partial(self._convertUnits,True))
        cmds.menuItem(l='Millimeter')
        cmds.menuItem(l='Centimeter')
        cmds.menuItem(l='Meter')
        cmds.menuItem(l='Kilometer')
        cmds.menuItem(l='Inch')
        cmds.menuItem(l='Foot')
        cmds.menuItem(l='Yard')
        cmds.menuItem(l='Mile')
        cmds.optionMenu(self._unit2Option, e=True, value='Centimeter')
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.showWindow()
        #Ensures window is the proper size
        cmds.window(self._window, e=True, w=208, h=290)

    def _setupSettingsUi(self, *args):
        for menuRef, setting in {self._menuModelRefDir:'modelRefDir',
                                self._menuExportDir:'exportDir',
                                self._menuExportFBX:'exportFBX',
                                self._menuExportOBJ:'exportOBJ',
                                self._menuCenterMeshes:'centerMeshes'}.items():
            menuVal = str(self._settings.get('settings', setting))
            menul = cmds.menuItem(menuRef, query=True, l=True)
            cmds.menuItem(menuRef, e=True, cb=menuVal=='true', ann=menul+" - "+menuVal)
        self._updateReferenceUi()

    def _hasSelection(self, *args):
        """
        Checks to see if the user has a current selection.

        Warnings:
            'No mesh selected'
        """
        if not cmds.ls(sl=True):
            cmds.warning('No mesh selected')
            return 0
        return 1

    def _checkRenderMeshName(self, sceneObj, *args):
        """
        Checks for render mesh name of the scene object.

        Naming Conventions:
        SM_[RenderMeshName] is renderMeshGroup
        UBX_[RenderMeshName]_## is a Box Collision
        USP_[RenderMeshName]_## is a Sphere Collision
        UCX_[RenderMeshName]_## is a Convex Collision
        UCP_[RenderMeshName]_## is a Capsule Collision
        LOD_[RenderMeshName]_## is a Level of Detail
        [RenderMeshName]_Collision is a Collision Group
        [RenderMeshName]_LOD is a Level of Detail Group

        Returns:
            String of the RenderMeshName
        """
        sceneObjShort = sceneObj.split('|')[-1]
        if sceneObjShort.startswith('SM_'):
            return sceneObjShort[3:]
        if sceneObjShort.endswith('_LOD'):
            return sceneObjShort[:-4]
        if sceneObjShort.endswith('_Collision'):
            return sceneObjShort[:-10]
        if any(sceneObjShort.startswith(nameConvention) for nameConvention in ['UBX_', 'USP_', 'UCX_', 'UCP_', 'LOD_']):
            return sceneObjShort[4:-3]
        return sceneObj

    def _getMeshes(self, renderMeshName):
        """
        Gets all meshes using primary mesh name.
        """
        meshes = []
        #renderMesh without groups
        if cmds.objExists('|%s' % renderMeshName):
            meshes.append('|%s' % renderMeshName)
        #renderMeshGroup
        if cmds.objExists('|SM_%s' % renderMeshName):
            meshes.append('|SM_%s' % renderMeshName)
        #renderMesh without LODs
        if cmds.objExists('|SM_%s|%s' % (renderMeshName, renderMeshName)):
            meshes.append('|SM_%s|%s' % (renderMeshName, renderMeshName))
        #Checks for LODs
        count = 1
        objExists = True
        lodGroup = '|SM_%s|%s_LOD|LOD_' % (renderMeshName, renderMeshName)
        while objExists:
            objExists = False
            objName = '%s%d|LOD_%s_%02d' % (lodGroup, count, renderMeshName, count)
            if cmds.objExists(objName):
                meshes.append(objName)
                count += 1
                objExists = True

        #Checks for Collision
        count = 0
        objExists = True
        objNameFormat = '{}{}{}_{:02d}'
        collisionGroup = '|SM_%s|%s_Collision|' % (renderMeshName, renderMeshName)
        while objExists:
            objExists = False
            for prefex in ['UCX_', 'UBX_', 'USP_', 'UCP_']:
                objName = objNameFormat.format(collisionGroup, prefex, renderMeshName, count)
                if cmds.objExists(objName):
                    meshes.append(objName)
                    count += 1
                    objExists = True
        return meshes

    def _findCollisionType(self, mesh, *args):
        """
        Using history to find what type of collision to use per mesh
        UBX_[RenderMeshName]_## is a Box Collision
        USP_[RenderMeshName]_## is a Sphere Collision
        UCP_[RenderMeshName]_## is a Capsule Collision 
        UCX_[RenderMeshName]_## is a Convex Collision
        """
        meshHistory = cmds.listHistory(mesh)
        if len(meshHistory) == 2:
            type = cmds.nodeType(meshHistory[1])
            if type == 'polyCube':
                return 'UBX_'
            if  type == 'polySphere':
                return 'USP_'
            if  type == 'polyCylinder':
                return 'UCP_'
        return 'UCX_'

    def _changeGrid(self, gSize, gSpacing, gDivisions, gcGridA, gcGridHl, gcGrid, fClipping, nClipping, trans, *args):
        """
        Sets several grid settings
        Color: gridAxis, gridHighlight, grid
        Distance: nearClipPlan, farClipPlan
        Camera: X,Y,Z
        """
        cmds.grid(size=gSize, spacing=gSpacing, divisions=gDivisions)
        cmds.displayColor('gridAxis', gcGridA, q=True, dormant=True)
        cmds.displayColor('gridHighlight', gcGridHl, q=True, dormant=True)
        cmds.displayColor('grid', gcGrid, q=True, dormant=True)
        cmds.setAttr('perspShape.farClipPlane', fClipping)
        cmds.setAttr('perspShape.nearClipPlane', nClipping)
        cmds.setAttr('top.translateY', trans)
        cmds.setAttr('front.translateZ', trans)
        cmds.setAttr('side.translateX', trans)
        cmds.viewSet(home=True, animate=True)

    def setGridUE4(self, *args):
        """
        Configures Maya for Unreal Engine 4
        """
        self._changeGrid(200,10,1,1,3,2,100000,1.5,1000)
        cmds.radioCollection(self._gridCollection, edit=True, select=self._gridRadio10)

    def setGridDefault(self, *args):
        """
        Configures Maya to defaults
        """
        self._changeGrid(12, 5, 5, 1, 3, 3, 10000, 0.1, 100.1)
        cmds.radioCollection(self._gridCollection, edit=True, select=self._gridRadio5)

    def _adjustGridScale(self, amount, *args):
        """
        Increase or decrease the grid scale by amount.
        This is not the grid spacing.
        """
        gridSize = cmds.grid(q=True, size=True)
        cmds.grid(size=gridSize+amount)

    def _setReferenceFolder(self, *args):
        """
        Calls settings to update reference directory and calls to update UI
        """
        self._settings.updateConfig(self._menuModelRefDir, 'modelRefDir')
        self._updateReferenceUi()

    def _updateReferenceUi(self, *args):
        """
        Clears the children of the reference import menu.
        Validates reference folder and generates menu items
        based on the model files in the folder.

        Warnings:
            'Mesh reference folder needs to be set'
            'No mesh references in reference folder'
        """
        menuItems = cmds.optionMenu(self._refOptionMenu, q=True, ill=True)
        if menuItems:
            cmds.deleteUI(menuItems)
        if not self._settings.get('settings', 'modelrefdir'):
            cmds.warning('Mesh reference folder needs to be set')
            cmds.menuItem(l='Set reference folder', p=self._refOptionMenu)
            return
        dirFiles = self._settings.referenceMeshes()
        if not dirFiles:
            cmds.warning('No mesh references in reference folder')
            cmds.menuItem(l='No models in folder', p=self._refOptionMenu)
        for dirFile in dirFiles:
            cmds.menuItem(l=dirFile, parent=self._refOptionMenu)

    def _importReference(self, *args):
        """
        Imports a reference from the reference directory

        Warnings:
            'File not found: '
        """
        modelrefdir = self._settings.get('settings', 'modelrefdir')
        #Check if reference directory is set
        if modelrefdir == '':
            if self._settings.updateConfig(self._menuModelRefDir, 'modelRefDir') == 'canceled':
                return
            else:
                self._updateReferenceUi()
        file = cmds.optionMenu(self._refOptionMenu, q=True, value=True)
        if file == 'No models in folder':
            self._updateReferenceUi()
            return
        filePath = modelrefdir + cmds.optionMenu(self._refOptionMenu, q=True, value=True)
        if not path.isfile(filePath):
            cmds.warning('File not found: %s' % filePath)
            self._updateReferenceUi()
            return
        cmds.file(filePath, i=True)

    def _renameMesh(self, *args):
        """
        Renames the last mesh selected and other meshes sharing the primary name.
        """
        if not self._hasSelection():
            return
        lastSelected = cmds.ls(sl=True, tl=1)[0]
        newRenderMeshName = cmds.textField(self._renameMeshText, q=True, tx=True)
        renderMeshName = self._checkRenderMeshName(lastSelected)
        meshes = self._getMeshes(renderMeshName)
        if cmds.objExists('|SM_%s' % newRenderMeshName):
            cfd = cmds.confirmDialog( title='Confirm', message='Another object has the same name in the root of the outliner', button=['Ok'], defaultButton='Ok')
            return
        #Checks if the first mesh using primary exists in meshes
        if meshes[0] == renderMeshName:
            cmds.rename(meshes[0], newRenderMeshName)
            return

        renderMesh = []
        renderMesh.append('|SM_%s|%s' % (renderMeshName, renderMeshName))
        renderMesh.append('|SM_%s|%s_LOD|LOD_0|%s' % (renderMeshName, renderMeshName,renderMeshName))
        for mesh in renderMesh:
            if cmds.objExists(mesh):
                cmds.rename(mesh, newRenderMeshName)
        #Renames the rest of meshes
        substring = '_' + renderMeshName + '_'
        newSubstring = '_' + newRenderMeshName + '_'
        for mesh in list(meshes):
            if substring in mesh:
                newMeshName = mesh.split('|')[-1].replace(substring, newSubstring)
                cmds.rename(mesh,newMeshName)
                meshes.remove(mesh)

        for mesh in meshes[::-1]:
            if mesh.split('|')[-1] == renderMeshName:
                cmds.rename(mesh,newRenderMeshName)
        #Rename groups
        for groupType in ['_LOD', '_Collision']:
            if cmds.objExists(renderMeshName + groupType):
                cmds.rename(renderMeshName + groupType, newRenderMeshName + groupType)
        if cmds.objExists('|SM_' + renderMeshName):
                cmds.rename('|SM_' + renderMeshName, 'SM_' + newRenderMeshName)
        cmds.textField(self._renameMeshText, e=True, tx='                 Rename Mesh')

    def _clearRenameMeshText(self, *args):
        """
        Changes the renameMeshText to the last selected object.
        """
        if not self._hasSelection():
            cmds.textField(self._renameMeshText, e=True, tx='                 Rename Mesh')
            cmds.setFocus(self._window)  #Prevents focus on textfield when no selection
            return
        lastSelected = cmds.ls(sl=True, tl=1)[0]
        renderMeshName = self._checkRenderMeshName(lastSelected)
        cmds.textField(self._renameMeshText, e=True, tx=renderMeshName)

    def _convertUnits(self, fromLeftToRight, *args):
        """
        Uses cmds.convertUnit to update textfields relating to units
        """
        units = {'Millimeter':'mm', 'Centimeter':'cm', 'Meter':'m', 'Kilometer':'km', 
             'Inch':'in', 'Foot':'ft', 'Yard':'yd', 'Mile':'mi'}
        value = 0
        unit1 = ''
        unit2 = ''
        if fromLeftToRight == True:
            value = cmds.textField("ConvertValue1", q=True, tx=True)
            unit1 = units[cmds.optionMenu(self._unit1Option, q=True, value=True)]
            unit2 = units[cmds.optionMenu(self._unit2Option, q=True, value=True)]
        else:
            value = cmds.textField("ConvertValue2", q=True, tx=True)
            unit1 = units[cmds.optionMenu(self._unit2Option, q=True, value=True)]
            unit2 = units[cmds.optionMenu(self._unit1Option, q=True, value=True)]
        converted = str(cmds.convertUnit(value, f=unit1, t=unit2))
        #Removes unit at end of string
        if converted[-2:].isalpha():  #CM already is removed
            converted = converted[:-2]
        if fromLeftToRight == True:
            cmds.textField("ConvertValue2", e=True, tx=converted)
        else:
            cmds.textField("ConvertValue1", e=True, tx=converted)

    def createMainGroup(self, renderMeshName='', *args):
        renderMeshGroup = '|SM_%s' % renderMeshName
        isGroup = True
        if cmds.objExists(renderMeshGroup):
            if cmds.nodeType(renderMeshGroup) == 'transform':
                children = cmds.listRelatives(renderMeshGroup, f=True, c=True) 
                if children == None:
                    isGroup = False
                else:
                    for child in children:
                        childType = cmds.nodeType(child)
                        if childType != 'transform' and childType != 'lodGroup':
                            isGroup = False
            else:
                isGroup = False
            if isGroup:
                return renderMeshGroup
        cmds.group(n=renderMeshGroup, em=True)
        if cmds.objExists('|'+renderMeshName):
            cmds.parent('|'+renderMeshName, renderMeshGroup)
        return renderMeshGroup

    def assignCollision(self, *args):
        """
        Assigns collision mesh to mesh
        """
        if not self._hasSelection():
            return
        selection = cmds.ls(sl=True)
        cmds.select(cl=True)
        renderMeshName = self._checkRenderMeshName(selection.pop())
        renderMeshGroup = self.createMainGroup(renderMeshName)
        collisionGroup = '%s_Collision' % renderMeshName
        if not cmds.objExists(collisionGroup):
            cmds.group(name=collisionGroup, empty=True, parent=renderMeshGroup)

        #Checks for collisions inside collisionGroup
        initCollisions = []
        newCollisions = selection
        groupRelatives = cmds.listRelatives(collisionGroup)
        if groupRelatives:
            #Validate if all are proper collision names per object
            for relative in groupRelatives:
                if any(relative.startswith(collisionType+renderMeshName) for collisionType in ['UBX_', 'USP_', 'UCP_', 'UCX_']): 
                    initCollisions.append(relative)
                    if relative in newCollisions:
                        newCollisions.remove(relative)
                else:
                    if relative not in newCollisions:
                        newCollisions.append(relative)

        #Insure intial collisions are in correct index order
        initCollisions.sort(key = lambda x: x[-2:])
        for i, collision in enumerate(initCollisions):
            cmds.reorder(collision, front=True )
            cmds.reorder(collision, r=i)
            correctNaming = collision[:-2]+'%02d' % i
            if collision != correctNaming:
                cmds.rename(collision, correctNaming)

        #Add new collision meshes and renames
        numCollisions = len(initCollisions)
        for i, newCollision in enumerate(newCollisions):
            collisionName = self._findCollisionType(newCollision) + renderMeshName + '_%02d' % (i + numCollisions)
            cmds.rename(newCollision, collisionName)
            if(cmds.listRelatives(collisionName, parent=True) != collisionGroup):
                cmds.parent(collisionName, collisionGroup)
            cmds.reorder(collisionName, front=True )
            cmds.reorder(collisionName, r= i + numCollisions)
        cmds.select(cl=True)

    def assignLODs(self, *args):
        """
        Creates LOD group based off triangle count of meshes selected

        Warnings:
            'Select more than one mesh to generate LODs'
            'Multiple lodGroups are parented to selected Meshes'
        """
        if not self._hasSelection():
            return
        selection = cmds.ls(sl=True, l=True)
        #Checks if the user has selected at least 2 meshes
        if len(selection) < 2:
            cmds.warning('Select more than one mesh to generate LODs')
            return
        
        #Checks for LOD groups
        lodGroups = []
        lodMeshes = []
        collisionGroups = []
        for selected in selection:
            selectedShort = selected.split('|')[-1]
            collisionGroup = '|SM_%s|%s_Collision' % (selectedShort, selectedShort)
            if cmds.objExists('|SM_%s|%s_Collision' % (selectedShort, selectedShort)):
                collisionGroups.append(collisionGroup)
            parent = cmds.listRelatives(selected, f=True, p=True)
            if parent:
                cleanParent = parent[0][:parent[0].rfind('|')]
                if cleanParent:
                    if cmds.nodeType(cleanParent) == 'lodGroup':
                        if parent not in lodGroups:
                            lodGroups.append(cleanParent)
        if  len(lodGroups) > 1:
            cmds.warning('Multiple LOD groups are parented to selected Meshes')
            return
        elif len(collisionGroups) > 1:
            cmds.warning('Multiple collision groups are parented to selected Meshes')
            return
        elif len(lodGroups) == 1:
            cfd = cmds.confirmDialog( title='Confirm', message='Are trying to add LODs to %s?' % lodGroups[0].split('|')[1], button=['Yes','No'], defaultButton='Yes', cancelButton='No', dismissString='No' )
            if cfd == 'No':
                return
            else:
                #Creates list of lodgroup relatives
                relatives = cmds.listRelatives('|%s' % lodGroups[0], f=True)
                for relative in relatives:
                    lod = str(cmds.listRelatives(relative, f=True))
                    for char in [' ','[',']']:
                        lod = lod.replace(char,"")
                    lod = lod.split(',')
                    for mesh in lod:
                        lodMeshes.append(unicode(mesh[2:-1]))
                #Removes duplicates
                for lodMesh in lodMeshes:
                    for selected in selection:
                        if selected in lodMesh:
                            selection.remove(selected)
                #need to research u'n' is in list when item under |lodGroup|lod_#|u'n' when mesh is deleted
                while 'n' in lodMeshes:     
                    lodMeshes.remove('n')
        elif len(collisionGroups) == 1:
            cfd = cmds.confirmDialog( title='Confirm', message='Are trying to add LODs to %s?' % collisionGroups[0].split('|')[1], button=['Yes','No'], defaultButton='Yes', cancelButton='No', dismissString='No' )
            if cfd == 'No':
                cmds.warning('Remove any selections under %s before trying to assign LODs')
                return
            else:
                pass

        lodMeshes = lodMeshes + selection
        #Gets triangle count of mesh
        meshesInfo = []
        for lodMesh in lodMeshes:
            cmds.select(lodMesh)
            meshInfo = {}
            meshInfo['object'] = lodMesh
            meshInfo['triangles'] = cmds.polyEvaluate(t=True)
            meshesInfo.append(meshInfo)
        cmds.select(cl=True)

        #Sorts array by triangle count from high to low
        meshesInfo = sorted(meshesInfo, 
                            key=operator.itemgetter('triangles'),
                            reverse=True)

        #Finds renderMeshName, lodGroup name, location in WS
        if lodGroups:
            renderMeshName = lodGroups[0].split('|')[1].replace('SM_','')
        elif collisionGroups:
            renderMeshName = collisionGroups[0].split('|')[1].replace('SM_','')
        else:
            renderMeshName = self._checkRenderMeshName(meshesInfo[0]['object'].split('|')[-1]) #shortname
        lodGroup = renderMeshName + '_LOD'
        cmds.select(meshesInfo[0]['object'])

        #Renames and moves meshes to 0,0,0 in world space
        if  cmds.listRelatives(meshesInfo[0]['object'], p=True):
            meshesInfo[0]['object'] = cmds.parent(meshesInfo[0]['object'], w=True)[0]
        meshesInfo[0]['object'] = cmds.rename(meshesInfo[0]['object'], renderMeshName)
        for i, meshInfo in enumerate(meshesInfo[1:]): 
            newName = 'LOD_%s_%02d' % (renderMeshName, i+1)
            mesh = cmds.rename(meshInfo['object'], newName)
            if  cmds.listRelatives(mesh, p=True):
                cmds.parent(mesh, w=True)
            meshInfo['object'] = newName

        #Deletes old LOD group
        if cmds.objExists('|SM_%s|%s' % (renderMeshName, lodGroup)):
            cmds.delete('|SM_%s|%s' % (renderMeshName, lodGroup))

        #Creates lodGroup based on triangle count
        for meshInfo in meshesInfo:
            cmds.select('|%s' % meshInfo['object'], add=True)
        cmds.xform(ws=True, t=(0,0,0))
        cmds.LevelOfDetailGroup()
        lodGroup = cmds.rename(lodGroup)
        for i in range(len(meshesInfo)):
            cmds.setAttr( '%s.displayLevel[%d]'%(lodGroup,i), 1)
        renderMeshGroup = self.createMainGroup(renderMeshName)
        cmds.parent(lodGroup, renderMeshGroup)
        cmds.select(cl=True)

    def export(self, *args):
        """
        Exports all meshes selected using ExportGroup Class and
        prompt the user to select export folder if it is not set.
        """
        if not self._hasSelection():
            return
        if self._settings.get('settings', 'exportdir') == '':
            if self._settings.updateConfig(menuExportDir, 'exportdir') == 'canceled':
                return
        exportMeshes = cmds.ls(selection=True, l=True)
        #Checks for duplicate objects selected
        for i in range(len(exportMeshes)):
            exportMeshes[i] = self._checkRenderMeshName(exportMeshes[i])

        #Removes duplicate items
        exportMeshes = list(set(exportMeshes))
        for renderMeshName in exportMeshes:
            meshes = self._getMeshes(renderMeshName)
            if meshes:
                mainMesh = meshes[0]
            else:
                mainMesh = renderMeshName
            fileName = mainMesh.split('|')[-1]
            path = self._settings.get('settings', 'exportDir') + fileName
            position = cmds.xform(mainMesh, ws=True, q=True, t=True)
            rotation = cmds.xform(mainMesh, ws=True, q=True, ro=True)
            cmds.select(d=True)
            #Center Meshes
            if self._settings.getboolean('settings', 'centerMeshes'):
               cmds.xform(mainMesh, r=True, t=([axis * -1 for axis in position]))
               cmds.xform(mainMesh, r=True, eu=True, ro=([axis * -1 for axis in rotation]))
            cmds.select(mainMesh)
            #FBX export
            if self._settings.getboolean('settings', 'exportFBX'):
                cmds.file(path + '.fbx', exportSelected=True, type='FBX export', force=True)
                print('Exported: ' + fileName + '.fbx')
            #OBJ export
            if self._settings.getboolean('settings', 'exportOBJ'):
                cmds.file(path + '.obj', exportSelected=True, type='OBJexport', force=True, op="materials=0")
                print('Exported: ' + fileName + '.obj')
            cmds.select(d=True)
            #Decenter Meshes
            if self._settings.getboolean('settings', 'centerMeshes'):
                cmds.xform(mainMesh, r=True, eu=True, ro=rotation)
                cmds.xform(mainMesh, r=True, t=position)
            cmds.select(d=True)

    def helpAbout(self, *args):
        """
        Prompts the About dialog
        """
        cmds.confirmDialog(t='about', icn='information', b=['Close'], db='Close',
            m='UE4 Helper\nversion:%.1f\nAuthor: Ben Esler\nhttp://benesler.net/'%(UE4HELPER_VERISION))

class UE4HelperHowToUse(object):
    def __init__(self):
        self._buildUi()
        self._changeInfo()

    def _buildUi(self):
        """
        Creates how to use UI
        """
        if cmds.window("UE4HelperHowToUse", exists = True):
            cmds.deleteUI("UE4HelperHowToUse")
        self._window = cmds.window(
                         "UE4HelperHowToUse", t="UE4 Helper How To Use", 
                           mb=True, w=300, h=200, mnb=False, mxb=False, s=False)
        cmds.columnLayout(cw=300, columnOffset=["both",10])
        cmds.separator(h=5, st="none")
        cmds.rowLayout(numberOfColumns=3)
        cmds.columnLayout(cw=300)
        self._sections = cmds.textScrollList( numberOfRows=8, allowMultiSelection=True,
                            append=['Introduction', 'Settings', 'Grid', 
                            'References', 'Renaming', 'Collision', 'LODs',
                            'Exporting', 'Converter'],
                            font="fixedWidthFont", h=149, w=100, ams=True,
                            showIndexedItem=1,selectItem='Introduction',
                            sc=self._changeInfo)
        cmds.separator(h=5, st="none")
        cmds.button(l='Close', w=100, c=self.toggle)
        cmds.setParent('..')
        cmds.separator(w=1, st="none")
        self._infoText = cmds.scrollField(h=177, w=280, ww=True, ed=False)
        cmds.setParent('..')

    def _changeInfo(self, *args):
        """
        Changes info text to user selection.
        """
        information = {
            'Introduction':"This tool is meant to help make meshes in Maya and"\
            " export to Unreal Engine 4.\n\nOn the side of this window is help"\
            " for each section of the tool.",
            'Settings':"Reference and export settings are found here. These ar"\
            "e saved in the /prefs/ folder and are loaded each time the tool i"\
            "s launched. \n\nWhen moving to a newer or older version of the to"\
            "ol these will be reset in case of changes.",
            'Grid':"You can either set the grid to be scaled to UE4 or Maya de"\
            "fault size. Change the spacing between each grid line by 1, 5, 10"\
            ", 50, 100 cm and increase or decrease the size of the grid.", 
            'References':"After setting a folder for references the drop down "\
            "will list all models in the folder. Clicking 'Import' will import"\
            " the current mesh in the drop down. If new files in the folder are"\
            " not showing click 'Refresh References' under settings", 
            'Renaming':"Select a mesh and click 'Rename Mesh'. It will give th"\
            "e current name of the mesh. Type what you want to change it to an"\
            "d press 'enter' to rename. If the mesh is part of an LOD or colli"\
            "sion it will rename all associated meshes.", 
            'Collision':"Select a single or multiple meshes for collision and "\
            "select target mesh, then click 'Assign Collision'. You do not nee"\
            "d to reselect meshes that are already collisions for the target m"\
            "esh.\n\nCollision is based off the construction history."\
            "\nUSP: Sphere\t\tUBX: Box\nUCP: Cylinder\tUCX: Anything else", 
            'LODs':"Select multiple meshes and press 'Assign LODs'. It will cre"\
            "ate an LOD group based off the triangle count of each selected me"\
            "sh and will be named based off the mesh with the most triangles.", 
            'Exporting':"Select a single or multiple meshes and click 'Export'"\
            ". It will export each mesh including LODs and Collision. All sett"\
            "ings for exporting can be found under the settings menu.", 
            'Converter':"Set the unit type to convert from and to. Type a numb"\
            "er into either text field and press 'enter' to convert."}
        section = cmds.textScrollList(self._sections, q=True, si=True)[0]
        cmds.scrollField(self._infoText, e=True, tx=information[section])

    def toggle(self, *args):
        """
        Toggles the how to use UI
        """
        if not cmds.window(self._window, exists=True):
            self._buildUi()
            self._changeInfo()
        cmds.toggleWindowVisibility(self._window)
