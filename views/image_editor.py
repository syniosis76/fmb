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
    pause_update = False
    parameters = None
    previous_zoom = None
    previous_transform = None
    brightness_factor = 2
    contrast_factor = 4
    saturation_factor = 2
    gamma_factor = 2

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
        self.parameters = edit_parameters()
        self.show_edit_parameters()
        self.load_image()              
        self.show_image(True)

    def show_edit_parameters(self):
        self.pause_update = True
        self.ids.brightness_slider.value = self.power(self.parameters.brightness, 1 / self.brightness_factor) * 100
        self.ids.contrast_slider.value = self.power(self.parameters.contrast, 1 / self.contrast_factor) * 100
        self.ids.saturation_slider.value = self.power(self.parameters.saturation, 1 / self.saturation_factor) * 100
        self.ids.gamma_slider.value = self.power(self.parameters.gamma, 1 / self.gamma_factor) * 100
        self.pause_update = False

    def load_image(self):
        if self.app.thumbnailView.currentFile:
            path = self.app.thumbnailView.currentFile.path                        

            self.base_image = PILImage.open(path)        
            orientation = exifhandler.get_orientation(self.base_image)
            if orientation in (6, 8):
                self.base_image = exifhandler.rotate_image(self.base_image, orientation)
            self.transformed_image = None

    def show_image(self, transform):        
        if not self.pause_update and self.base_image:
            self.clear_editor_image()

            if transform or not self.transformed_image:
                image = self.base_image.copy()                    

                box_width, box_height = self.ids.image_editor_box.size
                box_ratio = box_width / box_height
                width, height = image.size
                if self.parameters.ratio == None:
                    ratio = width / height
                else:
                    ratio = self.parameters.ratio

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
        self.app.imageView.no_back = True

        self.clear_editor_image()        

        self.manager.transition.direction = 'right'
        self.manager.current = 'ImageView'

    def set_ratio(self, ratio):
        self.parameters.ratio = ratio

        self.check_zoom()

        self.show_image(True)

    def check_zoom(self):
        if self.base_image:
            print('Initial', self.parameters.zoom, self.previous_zoom)
            max_zoom = self.parameters.zoom

            image = self.base_image
            image_ratio = image.size[0] / image.size[1]
            
            if self.parameters.ratio == None:
                ratio = image_ratio
            else:
                ratio = self.parameters.ratio

            if ratio > image_ratio:
                max_zoom = image_ratio / ratio

            if self.parameters.zoom > max_zoom:
                if self.previous_zoom == None:
                    self.previous_zoom = self.parameters.zoom
                self.parameters.zoom = max_zoom
                print('Zet Max', self.parameters.zoom, self.previous_zoom)
            else:
                if self.previous_zoom != None:
                    self.parameters.zoom = self.previous_zoom
                    self.previous_zoom = None
                    self.check_zoom()

    def adjust_position(self, amount):
        self.parameters.position = (self.parameters.position[0] + amount[0], self.parameters.position[1] + amount[1])
        self.show_image(True)
    
    def adjust_rotation(self, amount):
        self.parameters.rotation += amount
        self.show_image(True)
    
    def adjust_zoom(self, amount):
        self.previous_zoom = None # Clear Previous Zoom if manually set.
        zoom = self.parameters.zoom + amount
        if zoom <= 1:
            self.parameters.zoom = zoom
            self.show_image(True)

    def set_brightness(self, value):
        self.parameters.brightness = self.power(value, self.brightness_factor)
        self.show_image(False)
        self.transform_clear_redo()

    def set_contrast(self, value):        
        self.parameters.contrast = self.power(value, self.contrast_factor)
        self.show_image(False)
        self.transform_clear_redo()

    def set_saturation(self, value):
        self.parameters.saturation = self.power(value, self.saturation_factor)
        self.show_image(False)
        self.transform_clear_redo()

    def set_gamma(self, value):
        self.parameters.gamma = self.power(value, self.gamma_factor)
        self.show_image(False)
        self.transform_clear_redo()

    def power(self, value, exponent):      
      result = pow(abs(value), exponent)
      if value < 0.0:
          result = result * -1.0

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

            # Todo: Calculate Size
            box_width, box_height = image.size[0] * self.parameters.zoom, image.size[1] * self.parameters.zoom
            box_ratio = box_width / box_height
            width, height = image.size

            if self.parameters.ratio == None:
                ratio = width / height
            else:
                ratio = self.parameters.ratio

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
    
    def transform_undo_redo(self):
        if self.previous_transform == None:            
            # Backup the current parameters.            
            self.previous_transform = edit_parameters()
            self.previous_transform.assign_transform(self.parameters)

            # Reset the parameters
            self.parameters = edit_parameters()

            # Update the image
            self.show_edit_parameters()
            self.show_image(False)
            self.ids.transform_undo_redo_button.text = 'Redo'            
        else:
            # Restore the parameters and clear the backup
            self.parameters.assign_transform(self.previous_transform)
            self.previous_transform = None

            # Update the image
            self.show_edit_parameters()
            self.show_image(False)
            self.ids.transform_undo_redo_button.text = 'Undo'

    def transform_clear_redo(self):
        if not self.pause_update:
            self.previous_transform = None
            self.ids.transform_undo_redo_button.text = 'Undo'   

    def position_reset(self):
        self.parameters.reset_position()
        self.show_image(True)

            
            


            

