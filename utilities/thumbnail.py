from kivy.app import App
from kivy.clock import Clock
from PIL import Image
from ffpyplayer.player import MediaPlayer
from ffpyplayer.pic import SWScale
import os
import sys
import time
import traceback

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
          image, duration = self.getVideoFrame(3) # Get Frame at 3 seconds
          if image == None:
            # The video is too short. Try again
            image, duration = self.getVideoFrame(duration / 2)
        except:
          traceback.print_exc()
          image = None
                
      image.thumbnail((self.data.thumbnailWidth, self.data.thumbnailHeight))
    except:
      image = Image.new(mode='RGBA',size=(int(self.data.thumbnailWidth), int(self.data.thumbnailHeight)),color=(128,0,0,128)) 
      print(sys.exc_info()[0])
    
    image.save(self.thumbnailPath, format='png') 
  
  def getVideoFrame(self, position):
    options = {'paused': True, 'vf': ['select=gte(t\,' + str(position) + ')'], 'an': True, 'fast': True}
    player = MediaPlayer(self.mediaFile.path, ff_opts=options)    

    while player.get_metadata()['duration'] == None:            
        time.sleep(0.01)
        
    metadata = player.get_metadata()    
    duration = metadata['duration']    

    if duration >= position:        
        player.set_size(500,-1)
        
        frame = None    
        while not frame:
            frame = player.get_frame(force_refresh=True)[0]
            time.sleep(0.01)
        
        player.close_player()
        if frame:
            frame = frame[0]
            frame_size = frame.get_size()
            width = frame_size[0]
            height = frame_size[1]
            frame_converter = SWScale(width, height, frame.get_pixel_format(), ofmt='rgb24')
            new_frame = frame_converter.scale(frame)
            image_data = bytes(new_frame.to_bytearray()[0])

            image = Image.frombuffer(mode='RGB', size=(width, height), data=image_data, decoder_name='raw')
            return image, duration

    return None, duration