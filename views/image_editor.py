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
import threading

from models.edit_parameters import edit_parameters
from utilities import exifhandler
from utilities.transform_image import transform_image

Builder.load_file('views/image_editor.kv')

class image_editor(Screen):
    app = None
    data = None
    base_image = None
    transformed_image = None
    parameters = edit_parameters()    

    def __init__(self, **kwargs):
        super(image_editor, self).__init__(**kwargs) 
        self.app = App.get_running_app()
        self.data = self.app.data
        Window.bind(on_resize=self.on_window_resize)
        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_key_up=self.on_key_up)

        fadeOutDuration = 2.0        
        self.fadeOutAnimation = Animation(opacity=0, duration=fadeOutDuration)
    
    def on_enter(self):
        self.load_image()              
        self.show_image(True)

    def load_image(self):
        if self.app.thumbnailView.currentFile:
            path = self.app.thumbnailView.currentFile.path                        

            self.base_image = PILImage.open(path)        
            orientation = exifhandler.get_orientation(self.base_image)
            if orientation in (6, 8):
                self.base_image = exifhandler.rotate_image(self.base_image, orientation)
            self.transformed_image = None

    def show_image(self, transform):        
        if self.base_image:
            self.clear_editor_image()

            if transform or not self.transformed_image:
                image = self.base_image.copy()                    

                box_width, box_height = self.ids.image_editor_box.size
                box_ratio = box_width / box_height
                width, height = image.size
                ratio = width / height

                if box_ratio < ratio:
                    size = box_width, box_width / ratio
                else:
                    size = box_height * ratio, box_height

                self.transformed_image = transform_image.transform(image, size, self.parameters)            
            
            image = self.transformed_image
            
            image = transform_image.apply_adjustment(image, self.parameters)        
            
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

    # Reload the Image on resize to scale to fit. 
    def on_window_resize(self, window, width, height):
        Clock.schedule_once(lambda x: self.show_image(True), 0.1)        
    
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

        self.app.imageView.no_back = True

        self.manager.transition.direction = 'right'
        self.manager.current = 'ImageView'

        # Clock trigger to allow mouse up to process
        Clock.schedule_once(lambda x: self.clear_no_back(), 1.01)

    def clear_no_back(self):
        self.app.imageView.no_back = False

    def adjust_position(self, amount):
        self.parameters.position = (self.parameters.position[0] + amount[0], self.parameters.position[1] + amount[1])
        self.show_image(True)
    
    def adjust_rotation(self, amount):
        self.parameters.rotation += amount
        self.show_image(True)
    
    def adjust_zoom(self, amount):
        zoom = self.parameters.zoom + amount
        if zoom <= 1:
            self.parameters.zoom = zoom
            self.show_image(True)

    def set_brightness(self, value):
        self.parameters.brightness = self.power(value, 2)
        self.show_image(False)

    def set_contrast(self, value):        
        self.parameters.contrast = self.power(value, 5)
        self.show_image(False)

    def set_saturation(self, value):
        self.parameters.saturation = self.power(value, 3)
        self.show_image(False)

    def set_gamma(self, value):
        self.parameters.gamma = self.power(value, 2)
        self.show_image(False)

    def power(self, value, exponent):      
      result = pow(value, exponent)
      if value < 0 and result > 0:
          result = result * -1

      return result

    def save(self):
        if self.base_image:
            save_label = self.ids.save_label
            save_label.opacity = 1
            save_label.text = 'Saving...'

            thread = threading.Thread(target=self.save_thread)        
            thread.start()
    
    def save_thread(self):
        if self.base_image:
            image = self.base_image.copy()                    

            # todo: Calculate Size
            box_width, box_height = image.size[0] * self.parameters.zoom, image.size[1] * self.parameters.zoom
            box_ratio = box_width / box_height
            width, height = image.size
            ratio = width / height

            if box_ratio < ratio:
                size = box_width, box_width / ratio
            else:
                size = box_height * ratio, box_height

            image = transform_image.transform(image, size, self.parameters)                                                
            image = transform_image.apply_adjustment(image, self.parameters)

            path = self.app.thumbnailView.currentFile.path
            parts = os.path.splitext(path)
            suffixNumber = 1
            while (True):
                frame_path = parts[0] + ' ' + str(suffixNumber) + '.jpg'
                if not os.path.exists(frame_path):
                    break
                suffixNumber = suffixNumber + 1                       

            image.save(frame_path)
            self.app.thumbnailView.insertThumbnail(frame_path)
            
            save_label = self.ids.save_label
            save_label.text = 'Saved'
            self.fadeOutAnimation.start(self.ids.save_label)

            self.app.thumbnailView.trigger_save_layout()

            

