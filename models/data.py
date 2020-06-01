from datetime import datetime
import os.path
import pickle

class Data():    
  filename = 'data.data'
  folders = []
  foldersWidth = 200
  currentFolder = None
  version = 0  

  def __init__(self):
    self.loadData()     

  def loadData(self):    
    self.currentFolder = 'C:\\tmp\\fmvpics' # Todo Remove.
    self.load()    
    self.updateVersion()

  def load(self):
    if os.path.exists(self.filename):
      with open(self.filename, 'rb') as filehandle:            
        data = pickle.load(filehandle)
        self.currentFolder = data.get('currentFolder', self.currentFolder)
        self.folders = data.get('folders', self.folders)        
        self.foldersWidth = data.get('foldersWidth', self.foldersWidth)  

  def save(self):
    data = {}
    data['currentFolder'] = self.currentFolder
    data['folders'] = self.folders
    data['foldersWidth'] = self.foldersWidth

    with open(self.filename, 'wb') as filehandle:            
      pickle.dump(data, filehandle)

  @property
  def currentWorkingFolder(self):
    return os.path.join(self.currentFolder, '.fmb')

  def updateVersion(self):
    self.version += 1
    self.save()

  def hasUpdated(self, version):
    return self.version > version  