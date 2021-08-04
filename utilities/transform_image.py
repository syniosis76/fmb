from PIL import Image as PILImage, ImageEnhance, ImageFilter
from pillow_lut import load_hald_image, rgb_color_enhance
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
    def interpolate(x, values):
        length = len(values)

        for index in range(length - 1):
            (x1, y1) = values[index]
            (x2, y2) = values[index + 1]
            if x <= x1: return y1
            if x > x1 and x < x2:
                factor = (y2 - y1) / (x2 - x1)                
                return ((x - x1) * factor) + y1
        
        return values[length - 1][1]

    @staticmethod
    def apply_adjustment(image, parameters):
        adjusted_image = image        

        exposure = transform_image.interpolate(parameters.brightness, [(-1, -5), (0, 0), (1, 5)])
        contrast = transform_image.interpolate(parameters.contrast, [(-1, -1), (0, 0), (1, 5)])
        saturation = transform_image.interpolate(parameters.saturation, [(-1, -1), (0, 0), (1, 5)])
        gamma = transform_image.interpolate(parameters.gamma * -1, [(-1, 0), (0, 1), (1, 10)])
        # warmth -1.0 to 1.0
        # vibrance -1.0 to 5.0.
        # hue 0.0 to 1.0

        lut = rgb_color_enhance(5, exposure=exposure, contrast=contrast, saturation=saturation, gamma=gamma)        
        return adjusted_image.filter(lut)
    