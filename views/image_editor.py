from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.metrics import sp
from kivy.graphics.texture import Texture
from kivy.uix.image import Image
from kivy.core.window import Window, Keyboard
from kivy.animation import Animation
from kivy.clock import Clock
from PIL import Image as PILImage

import os
import time
import logging

from utilities import exifhandler

Builder.load_file('views/image_editor.kv')

class image_editor(Screen):
    app = None
    data = None
    base_image = None
    rotation = 0  

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

            # Rotate
            if self.rotation != 0:
                image = image.rotate(self.rotation)#, PILImage.BICUBIC)                  

            # Display Image
            width, height = image.size
            ratio = width / height
            
            image_editor_box = self.ids.image_editor_box  

            displayWidth = image_editor_box.size[0]
            displayHeight = image_editor_box.size[1]
            displayRatio = displayWidth / displayHeight

            if ratio > displayRatio:
                newWidth = int(displayWidth)
                newHeight = int(displayWidth / ratio)
            else:
                newHeight = int(displayHeight)
                newWidth = int(displayHeight * ratio)            
            
            image.resize((newWidth, newHeight), PILImage.BICUBIC)            
            
            image = image.convert('RGBA')
            bytes = image.tobytes()        
            texture = Texture.create(size = image.size)
            texture.blit_buffer(bytes, colorfmt='rgba', bufferfmt='ubyte')        
            texture.flip_vertical()
                    
            image = Image()
            image.texture = texture
            
            image_editor_box.add_widget(image)   

    def clear_editor_image(self):             
        image_editor_box = self.ids.image_editor_box
        image_editor_box.clear_widgets()

    # Reload the Image on resize to scale to fit. 
    def on_window_resize(self, window, width, height):
        self.show_image()
    
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

    def adjust_rotation(self, amount):
        self.rotation += amount
        self.show_image()