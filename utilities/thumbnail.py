from kivy.app import App
from PIL import Image
from ffpyplayer.player import MediaPlayer
from ffpyplayer.pic import SWScale
import os
import sys
import time
import traceback
from utilities import video_frame
from utilities import exifhandler

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
      else:
        try:          
          image, duration = video_frame.get_video_frame(self.mediaFile.path, 3) # Get Frame at 3 seconds
          if image == None:
            # The video is too short. Try again
            image, duration = video_frame.get_video_frame(self.mediaFile.path, duration / 2)
        except:
          traceback.print_exc()
          image = None

      image = exifhandler.auto_rotate_image(image)          
      image.thumbnail((self.data.thumbnailWidth, self.data.thumbnailHeight))      

      if self.mediaFile.extension in self.app.data.videoTypes:
        if self.data.videoThumbnailOverlay == None:
          self.data.videoThumbnailOverlay = Image.open('images\\video-overlay.png')
        overlay = self.data.videoThumbnailOverlay
        image.paste(overlay, (4, image.height - 28), overlay)
    except:
      print(sys.exc_info()[0])
      image = Image.new(mode='RGBA',size=(int(self.data.thumbnailWidth), int(self.data.thumbnailHeight)),color=(128,0,0,128))       
    
    image.save(self.thumbnailPath, format='png')

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