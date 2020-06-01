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

    def on_pre_enter(self):
        self.loadImage()

    def loadImage(self):
        threading.Thread(target=self.buildLoadImage).start()

    def buildLoadImage(self):
        app = App.get_running_app()                
        
        coreImage = self.getImage(app.data.currentFile)
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