from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.metrics import sp
from kivy.clock import Clock, mainthread
from kivy.uix.image import Image
#from kivy.uix.videoplayer import VideoPlayer
from kivy.uix.video import Video
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
    currentVideo = None

    def __init__(self, **kwargs):
        super(ImageView, self).__init__(**kwargs) 
        Window.bind(on_key_up=self.on_key_up)
        Window.bind(on_key_down=self.on_key_down)                

    def on_pre_enter(self):
        imageGrid = self.ids.imageGrid
        imageGrid.clear_widgets()
        self.loadMedia()

    def loadMedia(self):
        app = App.get_running_app()

        path = app.thumbnailView.currentFile

        parts = os.path.splitext(path)
        if len(parts) == 2:
            extension = parts[1].lower()

            if extension in app.data.imageTypes:        
                self.showImage(path)              
            elif extension in app.data.videoTypes:
                self.showVideo(path)                

    @mainthread               
    def showImage(self, path):
        self.stopCurrentVideo()

        imageGrid = self.ids.imageGrid
        imageGrid.clear_widgets()        
        
        image = Image()                            
        image.source = path
        imageGrid.add_widget(image)   
    
    @mainthread               
    def showVideo(self, path):
        self.stopCurrentVideo()

        if self.currentVideo != None:
            video = self.currentVideo
        else:
            imageGrid = self.ids.imageGrid
            imageGrid.clear_widgets()        
        
            video = Video()                            
            imageGrid.add_widget(video)       
            video.options['allow_stretch'] = True
        
        video.source = path
        video.state = 'play'

    @mainthread
    def stopCurrentVideo(self):
        if self.currentVideo != None:
            self.currentVideo.state = 'stop'

    def goToThumbnailView(self):
        self.stopCurrentVideo()

        self.manager.transition.direction = 'right'
        self.manager.current = 'ThumbnailView'

    def selectImage(self, offset):
        app = App.get_running_app()                
        app.thumbnailView.selectImage(offset)
        self.loadMedia()

    def backButtonClick(self, instance):
        print('Back button clicked.')

        self.goToThumbnailView()

    def on_key_down(self, window, keycode, text, modifiers, x):
        print('Key Down: ' + str(keycode))
        if keycode == Keyboard.keycodes['escape']:
            self.goToThumbnailView()
        if keycode == Keyboard.keycodes['right']:
            self.selectImage(1)
        elif keycode == Keyboard.keycodes['left']:
            self.selectImage(-1)
    
    def on_key_up(self, window, keycode, text):
        print('Key Up: ' + str(keycode))