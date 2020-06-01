from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.metrics import sp
from kivy.clock import Clock, mainthread
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window, Keyboard
from PIL import Image as PILImage
from io import BytesIO

import os
import threading

Builder.load_file('views/imageView.kv')

def sizeCallback(obj, value):
    obj.text_size = (value[0] - sp(30), sp(20))

class ImageView(Screen):
    def __init__(self, **kwargs):
        super(ImageView, self).__init__(**kwargs) 
        Window.bind(on_key_up=self.on_key_up)
        Window.bind(on_key_down=self.on_key_down)                

    def on_pre_enter(self):
        imageGrid = self.ids.imageGrid
        imageGrid.clear_widgets()
        self.loadImage()

    def loadImage(self):
        threading.Thread(target=self.buildLoadImage).start()

    def buildLoadImage(self):
        app = App.get_running_app()                
        
        coreImage = self.getImage(app.thumbnailView.currentFile)
        self.showImage(app, coreImage)

    def getImage(self, path):
        # Load Image
        pilImage = PILImage.open(path)
        # Save to Stream
        data = BytesIO()
        pilImage.save(data, format='jpeg')
        # Return Image 
        data.seek(0)          
        return CoreImage(BytesIO(data.read()), ext='jpg')

    @mainthread               
    def showImage(self, app, coreImage):        
        imageGrid = self.ids.imageGrid
        imageGrid.clear_widgets()        
        
        image = Image()                            
        image.texture = coreImage.texture
        imageGrid.add_widget(image)   
    
    def backButtonClick(self, instance):
        print('Back button clicked.')

        self.manager.transition.direction = 'right'
        self.manager.current = 'ThumbnailView'

    def selectImage(self, offset):
        app = App.get_running_app()                
        app.thumbnailView.selectImage(offset)
        self.loadImage()

    def on_key_down(self, window, keycode, text, modifiers, x):
        print('Key Down: ' + str(keycode))
        if keycode == Keyboard.keycodes['right']:
            self.selectImage(1)
        elif keycode == Keyboard.keycodes['left']:
            self.selectImage(-1)
    
    def on_key_up(self, window, keycode, text):
        print('Key Up: ' + str(keycode))