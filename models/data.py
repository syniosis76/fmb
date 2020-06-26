from datetime import datetime
import os
import json

class Data():
  userSettingsPath = os.getenv('LOCALAPPDATA')
  settingsPath = os.path.join(userSettingsPath, 'fmb-9220f09f-1c1b-4a65-b636-fe3996d18803') # UUID to ensure no conflict with other apps.
  settingsFile = os.path.join(settingsPath, 'data.data')  
  folders = []
  foldersWidth = 200
  currentFolder = None
  currentFile = None  
  version = 0
  imageTypes = ['.jpg', '.png', '.jpeg', '.bmp', '.gif', '.pcx']
  videoTypes = ['.avi', '.mov', '.mp4', '.mpeg4', '.mts', '.mpg', '.mpeg', '.vob', '.mkv']
  allTypes = imageTypes + videoTypes
  folderSettingsFileName = '.fmb'

  def __init__(self):
    self.loadData()     

  def loadData(self):    
    #self.currentFolder = 'C:\\tmp\\fmbpics' # Todo Remove.
    self.load()    
    self.updateVersion()

  def load(self):
    if os.path.exists(self.settingsFile):
      with open(self.settingsFile, 'rb') as filehandle:            
        data = json.load(filehandle)
        self.currentFolder = data.get('currentFolder', self.currentFolder)
        self.folders = data.get('folders', self.folders)        
        self.foldersWidth = data.get('foldersWidth', self.foldersWidth)  

  def save(self):
    data = {}
    data['currentFolder'] = self.currentFolder
    data['folders'] = self.folders
    data['foldersWidth'] = self.foldersWidth

    if not os.path.exists(self.settingsPath):
      os.makedirs(self.settingsPath)

    with open(self.settingsFile, 'w') as filehandle:            
      json.dump(data, filehandle)

  @property

  def currentWorkingFolder(self):
    return os.path.join(self.currentFolder, '.fmb')

  def updateVersion(self):
    self.version += 1
    self.save()

  def hasUpdated(self, version):
    return self.version > version  