from ffpyplayer import player
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.metrics import sp
from kivy.graphics.texture import Texture
from kivy.uix.image import Image
from kivy.uix.video import Video
from kivy.core.window import Window, Keyboard
from kivy.animation import Animation
from kivy.clock import Clock
from PIL import Image as PILImage

import os
import time
import logging

from utilities import video_frame
from utilities import exifhandler
from widgets import imagebutton

Builder.load_file('views/imageView.kv')

def sizeCallback(obj, value):
    obj.text_size = (value[0] - sp(30), sp(20))

class FmbVideo(Video):
    def texture_update(self, *largs):
        pass

class ImageView(Screen):
    app = None
    data = None
    currentVideo = None
    currentFrameRate = None

    def __init__(self, **kwargs):
        super(ImageView, self).__init__(**kwargs) 
        self.app = App.get_running_app()
        self.data = self.app.data
        Window.bind(on_resize=self.on_window_resize)
        Window.bind(on_key_up=self.on_key_up)
        Window.bind(on_key_down=self.on_key_down)
        Window.bind(mouse_pos=self.on_mouse_pos)

        self.setupButtons()

        fadeInDuration = 0.5
        fadeOutDuration = 1.0
        fadeTimoutDuration = 3.0
        self.fadeInAnimation = Animation(opacity=0.8, duration=fadeInDuration)               
        self.fadeOutAnimation = Animation(opacity=0, duration=fadeOutDuration)
        self.fadeOutTrigger = Clock.create_trigger(self.onFadeOutTrigger, timeout=fadeTimoutDuration, interval=False, release_ref=False)

    def on_window_resize(self, window, width, height):
        if self.currentVideo == None:
            self.loadMedia()

    def on_enter(self):        
        self.loadMedia()
        self.fadeInOverlay()

    def loadMedia(self):
        if self.app.thumbnailView.currentFile:
            path = self.app.thumbnailView.currentFile.path

            parts = os.path.splitext(path)
            if len(parts) == 2:
                extension = parts[1].lower()

                if extension in self.app.data.imageTypes:        
                    self.showImage(path)              
                elif extension in self.app.data.videoTypes:
                    self.showVideo(path)                
          
    def showImage(self, path):
        self.ids.videoControls.opacity = 0

        self.stopCurrentVideo()
        self.clearImageWidget()

        imageGrid = self.ids.imageGrid

        #startTime = time.process_time() 

        pilImage = PILImage.open(path)        

        orientation = exifhandler.get_orientation(pilImage)

        if orientation in (6, 8):
            height, width = pilImage.size
        else:
            width, height = pilImage.size

        ratio = width / height

        displayWidth = imageGrid.size[0]
        displayHeight = imageGrid.size[1]
        displayRatio = displayWidth / displayHeight

        if ratio > displayRatio:
            newWidth = int(displayWidth)
            newHeight = int(displayWidth / ratio)
        else:
            newHeight = int(displayHeight)
            newWidth = int(displayHeight * ratio)            
        
        pilImage.draft("RGB", (newWidth, newHeight))
        #pilImage.resize((newWidth, newHeight), PILImage.BICUBIC)

        pilImage = exifhandler.rotate_image(pilImage)

        pilImage = pilImage.convert('RGBA')
        bytes = pilImage.tobytes()        
        texture = Texture.create(size = pilImage.size)
        texture.blit_buffer(bytes, colorfmt='rgba', bufferfmt='ubyte')        
        texture.flip_vertical()
                
        image = Image()
        image.texture = texture

        #endTime = time.process_time()
        #print(endTime - startTime)

        image.allow_stretch = True
        imageGrid.add_widget(image)   
           
    def showVideo(self, path):
        self.stopCurrentVideo()

        if self.currentVideo != None:
            video = self.currentVideo
        else:
            self.clearImageWidget()         
            imageGrid = self.ids.imageGrid
        
            video = FmbVideo()
            imageGrid.add_widget(video)       
            video.bind(position=self.onPositionChange)
            video.bind(duration=self.onDurationChange)
            video.allow_stretch = True
            self.currentVideo = video
            self.currentFrameRate = 30

        try:    
            video.source = path
        except Exception as e:
            logging.exception('Error Playing Video - %S', e)

        self.ids.videoControls.opacity = 1

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
        Window.show_cursor = True

        self.stopCurrentVideo()
        self.clearImage()

        self.manager.transition.direction = 'right'
        self.manager.current = 'ThumbnailView'

    def selectImage(self, offset):        
        if self.app.thumbnailView.selectImage(offset):
            self.loadMedia()

    def previousImage(self):
        self.selectImage(1)
    
    def nextImage(self):
        self.selectImage(-1)

    def videoPlayPause(self):
        if self.currentVideo:
            video = self.currentVideo            
            if video.state == 'play':
                newstate = 'pause'                
            else:                
                newstate = 'play'
            
            logging.info('Play/Pause ' + video.state + ' to ' + newstate)
            video.state = newstate
    
    def delete(self):
        self.app.thumbnailView.delete()
        self.loadMedia()

    def videoSeekBySeconds(self, seconds):
        if self.currentVideo:
            video = self.currentVideo
            duration = video.duration
            position = video.position
            newPosition = position + seconds

            if newPosition <= duration:
                newPositionPercent = newPosition / duration
            else:
                newPositionPercent = 1   

            if video.state in ('stop'):
                video.state = 'play'

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
                            time.sleep(0.005)
                        if value in ('paused', 'eof'):
                            break
                    if frame:                        
                        ffVideo._next_frame = frame
                        ffVideo._trigger()
                finally:
                    ffplayer.set_pause(True)

    def video_extract_frame(self):
        if self.currentVideo:
            video = self.currentVideo
            if video.state == 'pause':
                ff_video = video._video
                frame = ff_video._next_frame
                image = video_frame.get_frame_image(frame[0])

                path = self.app.thumbnailView.currentFile.path

                parts = os.path.splitext(path)
                extension = parts[1].lower()

                suffixNumber = 1
                while (True):
                    frame_path = parts[0] + ' ' + str(suffixNumber) + '.jpg'
                    if not os.path.exists(frame_path):
                        break
                    suffixNumber = suffixNumber + 1

                image.save(frame_path, format='jpeg')
                self.app.thumbnailView.insertThumbnail(frame_path)


    def onPositionChange(self, instance, value):
        if self.currentVideo:
            progress = self.ids.progress
            progress.value = value /  self.currentVideo.duration * progress.max

    def onDurationChange(self, instance, value):
        print('The duration of the video is', value)       
    
    def fadeOutOverlay(self):        
        if self.manager.current == 'ImageView' and self.ids.overlay.opacity > 0 and not self.fadeOutAnimation.have_properties_to_animate(self.ids.overlay):            
            self.fadeInAnimation.cancel(self.ids.overlay)
            self.fadeOutAnimation.start(self.ids.overlay)
            Window.show_cursor = False
    
    def fadeInOverlay(self):
        self.startOverlayTimeout()
        if self.ids.overlay.opacity < 0.8 and not self.fadeInAnimation.have_properties_to_animate(self.ids.overlay):            
            self.fadeOutAnimation.cancel(self.ids.overlay)
            self.fadeInAnimation.start(self.ids.overlay)
            Window.show_cursor = True

    def startOverlayTimeout(self):
        self.fadeOutTrigger.cancel()
        self.fadeOutTrigger()

    def onFadeOutTrigger(self, *args):
        self.fadeOutOverlay()

    def on_mouse_pos(self, *args):
        self.fadeInOverlay()

    def setupButtons(self):
        self.buttons = [(self.ids.backButton, self.goToThumbnailView)
            , (self.ids.previousButton, self.previousImage)
            , (self.ids.nextButton, self.nextImage)]

    def on_touch_down(self, touch):
        self.fadeInOverlay()    
    
    def on_touch_up(self, touch):
        touch.push()
        try:
            touch.apply_transform_2d(self.to_local)

            progress = self.ids.progress
            if self.currentVideo and progress.collide_point(*touch.pos):
                touch.apply_transform_2d(progress.to_local)
                position = touch.pos[0] / progress.width
                self.currentVideo.seek(position, False)

                return True
            else:            
                for (button, callback) in self.buttons:
                    if button.collide_point(*touch.pos):                
                        callback()
                        return True                            
        finally:
            touch.pop()    

    def on_key_down(self, window, keycode, text, modifiers, x):        
        if self.manager.current == self.name:
            #print('ImageView Key Down: ' + str(keycode))
            # Navigation
            if keycode == Keyboard.keycodes['escape']:
                self.goToThumbnailView()            
            elif keycode in [Keyboard.keycodes['left'], Keyboard.keycodes['numpad4']]:
                self.selectImage(1)
            elif keycode in [Keyboard.keycodes['right'], Keyboard.keycodes['numpad6']]:                
                self.selectImage(-1)
            elif keycode in [Keyboard.keycodes['home']]:
                self.selectImage(1000000) # Big number will stop at the first image (highest index).
            elif keycode in [Keyboard.keycodes['end']]:
                self.selectImage(-1000000) # Big negative number will stop at the last image (0 index).
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
            elif keycode in [Keyboard.keycodes['f']]:
                self.video_extract_frame()
            elif keycode == Keyboard.keycodes['f11']:
                self.toggle_full_screen()
    
    def on_key_up(self, window, keycode, text):
        if self.manager.current == self.name:
            pass #print('ImagveView Key Up: ' + str(keycode))

    def toggle_full_screen(self):
        if Window.fullscreen == False:
            Window.fullscreen = 'auto'
        else:
            Window.fullscreen = False