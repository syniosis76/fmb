from PIL import Image
from ffpyplayer.player import MediaPlayer
from ffpyplayer.pic import SWScale

def get_frame_image(frame):
  frame_size = frame.get_size()
  width = frame_size[0]
  height = frame_size[1]
  frame_converter = SWScale(width, height, frame.get_pixel_format(), ofmt='rgb24')
  new_frame = frame_converter.scale(frame)
  image_data = bytes(new_frame.to_bytearray()[0])

  return Image.frombuffer(mode='RGB', size=(width, height), data=image_data, decoder_name='raw')