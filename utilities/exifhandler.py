from PIL import Image, ExifTags

orientation_index = -1
for index in ExifTags.TAGS.keys():
  if ExifTags.TAGS[index]=='Orientation':
    orientation_index = index
    break

def get_orientation(image):
  if orientation_index > -1:
    if hasattr(image, '_getexif'):
      exif = image._getexif()
      if exif:
        return exif.get(orientation_index, 0)

  return 0

def rotate_image(image):
  orientation = get_orientation(image)
  if orientation == 3:
    return image.transpose(Image.ROTATE_180)
  elif orientation == 6:
    return image.transpose(Image.ROTATE_270)
  elif orientation == 8:
    return image.transpose(Image.ROTATE_90)

  return image