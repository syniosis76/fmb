from kivy.app import App
from kivy.clock import Clock
from PIL import Image
import ffmpeg
from io import BytesIO
import os
import sys

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
    if not os.path.exists(self.thumbnailPath):
      self.createThumbnailFile()
  
  def createThumbnailFile(self):
    # Ensure Working folder exists:
    os.makedirs(self.app.data.currentWorkingFolder, exist_ok=True)                        

    try:
      if self.mediaFile.extension in self.app.data.imageTypes:
        image = Image.open(self.mediaFile.path)
      else:
        try:
          # Read frame 60 (at about 2 seconds)
          image = self.getVideoFrame(60) 
        except:
          # The video may be to short. Try the first frame.
          image = self.getVideoFrame(0)              
                
      image.thumbnail((self.data.thumbnailWidth, self.data.thumbnailHeight))
    except:
      image = Image.new(mode='RGBA',size=(int(self.data.thumbnailWidth), int(self.data.thumbnailHeight)),color=(128,0,0,128)) 
      print(sys.exc_info()[0])
    
    image.save(self.thumbnailPath, format='png') 
  
  def getVideoFrame(self, position):
    buffer, error = (
        ffmpeg
        .input(self.mediaFile.path)
        .filter('select', 'gte(n,{})'.format(position))
        .output('pipe:', vframes=1, format='image2', vcodec='mjpeg')
        .run(capture_stdout=True)
    )

    return Image.open(BytesIO(buffer))