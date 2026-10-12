from kivy.app import App
from PIL import Image
import os
import sys
from utilities import exifhandler
from utilities import mpv_thumbnail

class Thumbnail():
  app = None
  data = None
  mediaFile = None
  thumbnailPath = None

  def __init__(self, mediaFile):
    self.app = App.get_running_app()
    self.data = self.app.data
    self.mediaFile = mediaFile    
    self.thumbnailPath = os.path.join(self.data.currentWorkingFolder, mediaFile.name + '.tn')

  def initialiseThumbnail(self):
    if not os.path.exists(self.thumbnailPath) or self.media_date > self.thumbnail_date:
      self.createThumbnailFile()    
  
  def createThumbnailFile(self):
    # Ensure Working folder exists:
    os.makedirs(self.app.data.currentWorkingFolder, exist_ok=True)    

    try:
      if self.mediaFile.extension in self.app.data.imageTypes:
        image = Image.open(self.mediaFile.path)
        image.thumbnail((self.data.thumbnailWidth, self.data.thumbnailHeight))
      else:
        image = self.createVideoThumbnail()

      image = exifhandler.auto_rotate_image(image)                

      if self.mediaFile.extension in self.app.data.videoTypes:
        if self.data.videoThumbnailOverlay == None:
          self.data.videoThumbnailOverlay = Image.open('images\\video-overlay.png')
        overlay = self.data.videoThumbnailOverlay
        image.paste(overlay, (4, image.height - 28), overlay)
    except:
      print(sys.exc_info()[0])
      image = Image.new(mode='RGBA',size=(int(self.data.thumbnailWidth), int(self.data.thumbnailHeight)),color=(128,0,0,128))       
    
    image.save(self.thumbnailPath, format='png')

  def createVideoThumbnail(self):
    # Decode a single frame with libmpv (uses the low resolution proxy when
    # one is available) instead of shelling out to ffmpeg.
    frame = mpv_thumbnail.grab_frame(self.mediaFile.proxy_or_path)

    if frame is None:
      return None

    frame.thumbnail((self.data.thumbnailWidth, self.data.thumbnailHeight))

    return frame

  @property
  def media_date(self):
    if os.path.exists(self.mediaFile.path):
      return os.path.getmtime(self.mediaFile.path) 
    
    return None

  @property
  def thumbnail_date(self):
    if os.path.exists(self.mediaFile.path):
      return os.path.getmtime(self.thumbnailPath) 
    
    return None
