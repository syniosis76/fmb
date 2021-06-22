import os
import json
from kivy.metrics import sp

class Data():
  userSettingsPath = os.getenv('LOCALAPPDATA')
  settingsPath = os.path.join(userSettingsPath, 'fmb-9220f09f-1c1b-4a65-b636-fe3996d18803') # UUID to ensure no conflict with other apps.
  settingsFile = os.path.join(settingsPath, 'data.data')  
  folders = []
  foldersWidth = 200
  rootFolder = None
  currentFolder = None
  currentFile = None  
  version = 0
  imageTypes = ['.jpg', '.png', '.jpeg', '.bmp', '.gif', '.pcx']
  videoTypes = ['.avi', '.mov', '.mp4', '.mpeg4', '.mts', '.mpg', '.mpeg', '.vob', '.mkv', '.flv', '.wmv']
  allTypes = imageTypes + videoTypes
  folderSettingsFileName = '.fmb'
  cellWidth = sp(160)
  cellHeight = cellWidth * 4 / 5
  marginSize = 0.04
  thumbnailSize = 1 - (marginSize * 2)
  thumbnailWidth = cellWidth * thumbnailSize
  thumbnailHeight = cellHeight * thumbnailSize
  folderHeight = sp(30)
  videoThumbnailOverlay = None

  def __init__(self):
    self.loadData()     

  def loadData(self):        
    self.load()    
    self.updateVersion()

  def load(self):
    if os.path.exists(self.settingsFile):
      with open(self.settingsFile, 'rb') as filehandle:            
        data = json.load(filehandle)
        self.rootFolder = data.get('rootFolder', self.rootFolder)
        self.currentFolder = data.get('currentFolder', self.currentFolder)
        self.folders = data.get('folders', self.folders)        
        self.foldersWidth = data.get('foldersWidth', self.foldersWidth)  

  def save(self):
    data = {}
    data['rootFolder'] = self.rootFolder
    data['currentFolder'] = self.currentFolder
    data['folders'] = self.folders
    data['foldersWidth'] = self.foldersWidth

    os.makedirs(self.settingsPath, exist_ok=True)

    with open(self.settingsFile, 'w') as filehandle:            
      json.dump(data, filehandle)

  @property
  def currentWorkingFolder(self):
    return os.path.join(self.currentFolder, '.fmb')

  @property
  def settings_file_name(self):
    return os.path.join(self.currentWorkingFolder, 'fmb.json') 

  def updateVersion(self):
    self.version += 1
    self.save()

  def hasUpdated(self, version):
    return self.version > version  