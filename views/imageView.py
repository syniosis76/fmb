from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.metrics import sp
from kivy.clock import Clock, mainthread
from kivy.uix.image import Image
from kivy.uix.video import Video
from kivy.core.window import Window, Keyboard
from PIL import Image as PILImage
from io import BytesIO

import os
import threading
import time

Builder.load_file('views/imageView.kv')

def sizeCallback(obj, value):
    obj.text_size = (value[0] - sp(30), sp(20))

class ImageView(Screen):
    app = None
    data = None
    currentVideo = None
    currentFrameRate = None

    def __init__(self, **kwargs):
        super(ImageView, self).__init__(**kwargs) 
        self.app = App.get_running_app()
        self.data = self.app.data
        Window.bind(on_key_up=self.on_key_up)
        Window.bind(on_key_down=self.on_key_down)                

    def on_pre_enter(self):        
        self.loadMedia()

    def loadMedia(self):
        path = self.app.thumbnailView.currentFile.path

        parts = os.path.splitext(path)
        if len(parts) == 2:
            extension = parts[1].lower()

            if extension in self.app.data.imageTypes:        
                self.showImage(path)              
            elif extension in self.app.data.videoTypes:
                self.showVideo(path)                
          
    def showImage(self, path):
        self.stopCurrentVideo()

        self.clearImageWidget()     
        
        imageGrid = self.ids.imageGrid
        image = Image()                            
        image.source = path
        image.allow_stretch = True
        imageGrid.add_widget(image)   
           
    def showVideo(self, path):
        self.stopCurrentVideo()

        if self.currentVideo != None:
            video = self.currentVideo
        else:
            self.clearImageWidget()         
            imageGrid = self.ids.imageGrid
        
            video = Video()
            imageGrid.add_widget(video)       
            video.bind(position=self.onPositionChange)
            video.bind(duration=self.onDurationChange)
            video.allow_stretch = True
            self.currentVideo = video
            self.currentFrameRate = 30
            
        video.source = path
        video.state = 'play'

    def clearImageWidget(self):
        imageGrid = self.ids.imageGrid
        imageGrid.clear_widgets()
        self.currentVideo = None

    def stopCurrentVideo(self):
        if self.currentVideo != None:
            self.currentVideo.state = 'stop'            
            self.currentVideo.unload()

    def clearImage(self):
        self.currentVideo = None
        imageGrid = self.ids.imageGrid
        imageGrid.clear_widgets()

    def goToThumbnailView(self):        
        self.stopCurrentVideo()
        self.clearImage()

        self.manager.transition.direction = 'right'
        self.manager.current = 'ThumbnailView'

    def selectImage(self, offset):        
        self.app.thumbnailView.selectImage(offset)
        self.loadMedia()

    def videoPlayPause(self):
        if self.currentVideo:
            video = self.currentVideo
            if video.state == 'play':
                video.state = 'pause'
            else:
                video.state = 'play'            
    
    def delete(self):
        self.app.thumbnailView.delete()
        self.loadMedia()

    def videoSeekBySeconds(self, seconds):
        if self.currentVideo:
            video = self.currentVideo
            duration = video.duration
            position = video.position
            newPosition = position + seconds
            newPositionPercent = newPosition / duration
            video.seek(newPositionPercent, precise = False)

    def videoNextFrame(self):
        if self.currentVideo:
            video = self.currentVideo
            if video.state == 'pause':
                ffVideo = video._video
                ffplayer = ffVideo._ffplayer
                ffplayer.set_pause(False)
                try:                                    
                    frame = None
                    while not frame:
                        frame, value = ffplayer.get_frame()
                        if not frame:
                            time.sleep(0.001)
                        if value in ('paused', 'eof'):
                            break
                    if frame:
                        ffVideo._next_frame = frame
                        ffVideo._redraw()
                finally:
                    ffplayer.set_pause(True)

    def onPositionChange(self, instance, value):
        pass #print('The position in the video is', value)

    def onDurationChange(self, instance, value):
        print('The duration of the video is', value)

    def backButtonClick(self, instance):
        print('Back button clicked.')        
        self.goToThumbnailView()

    def on_key_down(self, window, keycode, text, modifiers, x):        
        if self.manager.current == self.name:
            print('ImageView Key Down: ' + str(keycode))
            # Navigation
            if keycode == Keyboard.keycodes['escape']:
                self.goToThumbnailView()            
            elif keycode in [Keyboard.keycodes['left'], Keyboard.keycodes['numpad4']]:
                self.selectImage(1)
            elif keycode in [Keyboard.keycodes['right'], Keyboard.keycodes['numpad6']]:                
                self.selectImage(-1)
            elif keycode in [Keyboard.keycodes['delete'], Keyboard.keycodes['numpaddecimal']]:
                self.delete()
            # Video Controls
            elif keycode in [Keyboard.keycodes['spacebar'], Keyboard.keycodes['p'], Keyboard.keycodes['numpad2']]:
                self.videoPlayPause()
            elif keycode in [Keyboard.keycodes[','], Keyboard.keycodes['numpad1']]:
                self.videoSeekBySeconds(-5)
            elif keycode in [Keyboard.keycodes['.'], Keyboard.keycodes['numpad3']]:
                self.videoSeekBySeconds(10)
            elif keycode in [Keyboard.keycodes[';'], Keyboard.keycodes['numpad7']]:
                self.videoSeekBySeconds(-1)
            elif keycode in [Keyboard.keycodes['\''], Keyboard.keycodes['numpad9']]:
                self.videoNextFrame()
    
    def on_key_up(self, window, keycode, text):
        if self.manager.current == self.name:
            print('ImagveView Key Up: ' + str(keycode))