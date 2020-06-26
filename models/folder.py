from kivy.app import App
import os
from models.mediafile import MediaFile

class Folder():
  path = None
  settingsFile = None
  files = []

  def loadPath(self, path):
    app = App.get_running_app()

    self.path = path
    self.settingFile = os.path.join(self.path, app.data.folderSettingsFileName)
    self.files = []
    self.listMediaFiles() 

  def listMediaFiles(self):
    app = App.get_running_app()

    with os.scandir(self.path) as scandir:
      for entry in scandir:
        if app.closing:
          break
        if entry.is_file:                    
          extension = MediaFile.getExtension(entry.name)
          if extension in app.data.allTypes:
            mediaFile = MediaFile(entry.path)
            mediaFile.readModified()
            self.files.append(mediaFile)

  def sortByName(self):
    self.files.sort(key = lambda mediaFile: mediaFile.name)

  def sortByModified(self):
    self.sortByName() # To sort by name after date
    self.files.sort(key = lambda mediaFile: mediaFile.modified)