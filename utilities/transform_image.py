from PIL import Image as PILImage, ImageEnhance
import math

class transform_image():
    @staticmethod
    def transform(image, size, parameters):
        size = int(size[0]), int(size[1])

        angle = parameters.rotation / 180.0 * math.pi
        x, y = image.size[0] / 2, image.size[1] / 2
        nx, ny = size[0] / 2 + parameters.position[0], size[1] / 2 + parameters.position[1]

        zoom = size[1] / image.size[1] * (1 / parameters.zoom)
        sx, sy = zoom, zoom
        
        cosine = math.cos(angle)
        sine = math.sin(angle)
        a = cosine / sx
        b = sine / sx
        c = x - nx * a - ny * b
        d = -sine / sy
        e = cosine / sy
        f = y - nx * d - ny * e

        return image.transform(size, PILImage.AFFINE, (a,b,c,d,e,f), resample=PILImage.BICUBIC)    

    @staticmethod
    def apply_adjustment(image, parameters):
        adjusted_image = image

        #Brightness
        if parameters.brightness != 1:
            brightness_enhancer = ImageEnhance.Brightness(adjusted_image)            
            adjusted_image = brightness_enhancer.enhance(parameters.brightness)
        if parameters.contrast != 1:
            contrast_enhancer = ImageEnhance.Contrast(adjusted_image)            
            adjusted_image = contrast_enhancer.enhance(parameters.contrast)
        
        return adjusted_image