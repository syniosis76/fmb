import os

class MediaFile():
  def __init__(self, path):
    self.path = path
    self.thumbnailPath: str | None
    self.name: str | None
    self.extension: str | None
    self.modified: float | None
    self.captured: float | None
    self.processPath()

  def processPath(self):
    parts = os.path.split(self.path)
    length = len(parts)
    if length > 0:
      self.name = parts[length - 1]
      self.extension = MediaFile.getExtension(self.name)

  def readModified(self):
    if os.path.exists(self.path):
        self.modified = os.path.getmtime(self.path)

  @property
  def exists(self):
    return os.path.exists(self.path)

  @staticmethod
  def getExtension(path):
        parts = os.path.splitext(path)
        if len(parts) == 2:
            return parts[1].lower()            
        return None