from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.metrics import sp
from kivy.graphics.texture import Texture
from kivy.uix.image import Image
from kivy.core.window import Window, Keyboard
from kivy.clock import Clock
from PIL import Image as PILImage

import math

from utilities import exifhandler

Builder.load_file('views/image_editor.kv')

class image_editor(Screen):
    app = None
    data = None
    base_image = None
    position = 0, 0
    rotation = 0
    zoom = 1    

    def __init__(self, **kwargs):
        super(image_editor, self).__init__(**kwargs) 
        self.app = App.get_running_app()
        self.data = self.app.data
        Window.bind(on_resize=self.on_window_resize)
        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_key_up=self.on_key_up)
    
    def on_enter(self):
        self.load_image()              
        self.show_image()

    def load_image(self):
        if self.app.thumbnailView.currentFile:
            path = self.app.thumbnailView.currentFile.path                        

            self.base_image = PILImage.open(path)        
            orientation = exifhandler.get_orientation(self.base_image)
            if orientation in (6, 8):
                self.base_image = exifhandler.rotate_image(self.base_image, orientation)

    def show_image(self):        
        if self.base_image:
            self.clear_editor_image()            

            image = self.base_image.copy()                    

            box_width, box_height = self.ids.image_editor_box.size
            box_ratio = box_width / box_height
            width, height = image.size
            ratio = width / height

            if box_ratio < ratio:
                size = box_width, box_width / ratio
            else:
                size = box_height * ratio, box_height

            image = self.transform_image(image, size, self.position, self.rotation, self.zoom)          
            
            image = image.convert('RGBA')
            bytes = image.tobytes()        
            texture = Texture.create(size = image.size)
            texture.blit_buffer(bytes, colorfmt='rgba', bufferfmt='ubyte')        
            texture.flip_vertical()
                    
            image_widget = Image()
            image_widget.texture = texture
            
            self.ids.image_editor_box.add_widget(image_widget)   

    def clear_editor_image(self):             
        image_editor_box = self.ids.image_editor_box
        image_editor_box.clear_widgets()

    def transform_image(self, image, size, position, rotation, zoom):
        size = int(size[0]), int(size[1])

        angle = rotation / 180.0 * math.pi
        x, y = image.size[0] / 2, image.size[1] / 2
        nx, ny = size[0] / 2 + position[0], size[1] / 2 + position[1]

        zoom = size[1] / image.size[1] * (1 / zoom)
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

    # Reload the Image on resize to scale to fit. 
    def on_window_resize(self, window, width, height):
        Clock.schedule_once(lambda x: self.show_image(), 0.1)        
    
    def on_key_down(self, window, keycode, text, modifiers, x):        
        if self.manager.current == self.name:
            #print('ImageView Key Down: ' + str(keycode))
            # Navigation
            if keycode == Keyboard.keycodes['escape']:
                self.go_back()
            
            return True

        return False
    
    def on_key_up(self, window, keycode, text):
        pass
        #if self.manager.current == self.name:
        #    print('ImagveView Key Up: ' + str(keycode))

    def go_back(self):
        self.clear_editor_image()

        self.manager.transition.direction = 'left'
        self.manager.current = 'ImageView'

    def adjust_position(self, amount):
        self.position = (self.position[0] + amount[0], self.position[1] + amount[1])
        self.show_image()
    
    def adjust_rotation(self, amount):
        self.rotation += amount
        self.show_image()
    
    def adjust_zoom(self, amount):
        zoom = self.zoom + amount
        if zoom <= 1:
            self.zoom = zoom
            self.show_image()