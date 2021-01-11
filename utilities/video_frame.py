from PIL import Image
from ffpyplayer.player import MediaPlayer
from ffpyplayer.pic import SWScale
import os
import sys
import time
import traceback

def get_frame_image(frame):
  frame_size = frame.get_size()
  width = frame_size[0]
  height = frame_size[1]
  frame_converter = SWScale(width, height, frame.get_pixel_format(), ofmt='rgb24')
  new_frame = frame_converter.scale(frame)
  image_data = bytes(new_frame.to_bytearray()[0])

  return Image.frombuffer(mode='RGB', size=(width, height), data=image_data, decoder_name='raw')

def get_video_frame(path, position):
  options = {'paused': True, 'vf': ['select=gte(t\,' + str(position) + ')'], 'an': True, 'fast': True}
  player = MediaPlayer(path, ff_opts=options)    

  count = 0
  while player.get_metadata()['duration'] == None:            
      time.sleep(0.01)
      count += 1
      if count > 200:
        raise TypeError('Invalid Video: ' + path)
      
  metadata = player.get_metadata()    
  duration = metadata['duration']    

  if duration >= position:        
      player.set_size(500,-1)
      
      frame = None    
      while not frame:
          frame = player.get_frame(force_refresh=True)[0]
          if not frame:
            time.sleep(0.01)
      
      player.close_player()
      if frame:
          frame = frame[0]
          image = get_frame_image(frame)
          return image, duration

  return None, duration