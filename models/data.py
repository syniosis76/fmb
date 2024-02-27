import os
import json
from kivy.metrics import sp

class Data():
  def __init__(self):
    self.userSettingsPath = os.getenv('LOCALAPPDATA') # pylint: disable=no-member
    self.settingsPath = os.path.join(self.userSettingsPath, 'fmb-9220f09f-1c1b-4a65-b636-fe3996d18803') # pylint: disable=no-member # UUID to ensure no conflict with other apps.
    self.settingsFile = os.path.join(self.settingsPath, 'data.data')  
    self.folders = []

    self.foldersWidth = 200
    self.rootFolder = None
    self.currentFolder = None
    self.currentFile = None  
    self.version = 0
    self.imageTypes = ['.jpg', '.png', '.jpeg', '.bmp', '.gif', '.pcx']
    self.videoTypes = ['.avi', '.mov', '.mp4', '.mpeg4', '.mts', '.mpg', '.mpeg', '.vob', '.mkv', '.flv', '.wmv']
    self.allTypes = self.imageTypes + self.videoTypes
    self.folderSettingsFileName = '.fmb'
    self.cellWidth = sp(160)
    self.cellHeight = self.cellWidth * 4 / 5
    self.marginSize = 0.04
    self.thumbnailSize = 1 - (self.marginSize * 2)
    self.thumbnailWidth = self.cellWidth * self.thumbnailSize
    self.thumbnailHeight = self.cellHeight * self.thumbnailSize
    self.folderHeight = sp(30)
    self.videoThumbnailOverlay = None
    self.window_position = {}
  
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
        self.window_position = data.get('window_position', self.window_position) 

  def save(self):
    data = {}
    data['rootFolder'] = self.rootFolder
    data['currentFolder'] = self.currentFolder
    data['folders'] = self.folders
    data['foldersWidth'] = self.foldersWidth
    data['window_position'] = self.window_position

    os.makedirs(self.settingsPath, exist_ok=True)

    with open(self.settingsFile, 'w') as filehandle:            
      json.dump(data, filehandle)

  @property
  def currentWorkingFolder(self):
    return os.path.join(self.currentFolder, '.fmb') # pylint: disable=no-member

  @property
  def settings_file_name(self):
    return os.path.join(self.currentWorkingFolder, 'fmb.json') 

  def updateVersion(self):
    self.version += 1
    self.save()

  def hasUpdated(self, version):
    return self.version > version