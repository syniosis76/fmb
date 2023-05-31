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

Builder.load_file('views/image_view.kv')

class fmb_video(Video):
    def texture_update(self, *largs):
        pass

class image_view(Screen):
    app = None
    data = None
    current_video = None
    currentFrameRate = None
    no_back = False

    def __init__(self, **kwargs):
        super(image_view, self).__init__(**kwargs) 
        self.app = App.get_running_app()
        self.data = self.app.data
        self.seeked_frames = 0
        self.restart_position = None
        Window.bind(on_resize=self.on_window_resize)        
        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_key_up=self.on_key_up)
        Window.bind(mouse_pos=self.on_mouse_pos)

        self.setup_buttons()

        fade_in_duration = 0.5
        fade_out_duration = 1.0
        fade_timout_duration = 3.0
        self.fade_in_animation = Animation(opacity=0.8, duration=fade_in_duration)               
        self.fade_out_animation = Animation(opacity=0, duration=fade_out_duration)
        self.fade_out_trigger = Clock.create_trigger(self.on_fade_out_trigger, timeout=fade_timout_duration, interval=False, release_ref=False)

    # Reload the Image on resize to scale to fit.
    def on_window_resize(self, window, width, height):
        if self.current_video == None:
            self.loadMedia()

    def on_enter(self):               
        self.loadMedia()
        self.fade_in_overlay()

    def loadMedia(self):
        if self.app.thumbnail_view.currentFile:
            path = self.app.thumbnail_view.currentFile.path

            parts = os.path.splitext(path)
            if len(parts) == 2:
                extension = parts[1].lower()

                if extension in self.app.data.imageTypes:        
                    self.showImage(path)              
                elif extension in self.app.data.videoTypes:
                    self.showVideo(path)                
          
    def showImage(self, path):
        self.ids.video_controls.opacity = 0
        self.ids.edit_button.opacity = 1

        self.stop_current_video()
        self.clear_image_widget()

        image_grid = self.ids.image_grid

        #startTime = time.process_time() 

        pilImage = PILImage.open(path)        

        orientation = exifhandler.get_orientation(pilImage)

        if orientation in (6, 8):
            height, width = pilImage.size
        else:
            width, height = pilImage.size

        ratio = width / height

        displayWidth = image_grid.size[0]
        displayHeight = image_grid.size[1]
        displayRatio = displayWidth / displayHeight

        if ratio > displayRatio:
            newWidth = int(displayWidth)
            newHeight = int(displayWidth / ratio)
        else:
            newHeight = int(displayHeight)
            newWidth = int(displayHeight * ratio)            
        
        pilImage.draft("RGB", (newWidth, newHeight))
        #pilImage.resize((newWidth, newHeight), PILImage.BICUBIC)

        pilImage = exifhandler.auto_rotate_image(pilImage)

        pilImage = pilImage.convert('RGBA')
        bytes = pilImage.tobytes()        
        texture = Texture.create(size = pilImage.size)
        texture.blit_buffer(bytes, colorfmt='rgba', bufferfmt='ubyte')        
        texture.flip_vertical()
                
        image = Image()
        image.texture = texture

        #endTime = time.process_time()
        #print(endTime - startTime)

        #image.fit_mode = 'contain'
        image_grid.add_widget(image)   
           
    def showVideo(self, path, restart=False):
        self.stop_current_video()

        if not restart and self.current_video != None:
            video = self.current_video
        else:
            self.clear_image_widget()         
            image_grid = self.ids.image_grid
        
            video = fmb_video()
            image_grid.add_widget(video)       
            video.bind(position=self.on_position_change)
            video.bind(duration=self.on_duration_change)
            video.bind(state=self.on_state_change)
            video.bind(loaded=self.on_loaded)
            video.fit_mode = 'contain'
            self.current_video = video
            self.currentFrameRate = 30

        try:
            video.source = path
        except Exception as e:
            logging.exception('Error Playing Video - %S', e)
        
        self.ids.edit_button.opacity = 0
        self.ids.video_controls.opacity = 1

        video.state = 'play'    

    def clear_image_widget(self):
        image_grid = self.ids.image_grid
        image_grid.clear_widgets()
        self.current_video = None

    def stop_current_video(self):
        if self.current_video != None:
            self.current_video.state = 'stop'            
            self.current_video.unload()

    def clear_image(self):
        self.current_video = None
        image_grid = self.ids.image_grid
        image_grid.clear_widgets()

    def go_back(self):
        if self.no_back:
            self.no_back = False
        else:            
            Window.show_cursor = True

            self.stop_current_video()
            self.clear_image()

            self.manager.transition.direction = 'right'
            self.manager.current = 'thumbnail_view'

        return True

    def change_image(self, offset):        
        if self.app.thumbnail_view.change_image(offset):
            self.loadMedia()

    def previous_image(self):
        self.change_image(1)
        return True
    
    def next_image(self):
        self.change_image(-1)    
        return True

    def toggle_play_pause(self):
        if self.current_video:
            video = self.current_video            
            if video.state == 'play':
                newstate = 'pause'                
            else:                
                newstate = 'play'
            
            logging.info('Play/Pause ' + video.state + ' to ' + newstate)
            
            self.set_video_state(newstate)
            video.state = newstate

            return True
        
        return False

    def set_video_state(self, state):
        if self.current_video:
            video = self.current_video
            if video.state == 'pause' and state == 'play' and self.seeked_frames > 10:
                self.restart_video(True) # resume
            else:
                video.state = state

    def restart_video(self, resume):
        if self.current_video:
            self.seeked_frames = 0            

            video = self.current_video
                    
            self.restart_position = video.position / video.duration

            path = self.app.thumbnail_view.currentFile.path
            self.showVideo(path, True)

    def on_loaded(self, object, value):
        if value and self.current_video and self.restart_position != None:
            restart_position = self.restart_position
            self.restart_position = None
            
            self.current_video.seek(restart_position, precise = False)

    def edit_image(self):
        if not self.current_video:
            Window.show_cursor = True

            self.stop_current_video()
            self.clear_image()

            self.manager.transition.direction = 'left'
            self.manager.current = 'image_editor'

            return True
        
        return False
    
    def delete(self):
        self.app.thumbnail_view.delete_current()
        self.loadMedia()

    def video_seek_by_seconds(self, seconds):
        if self.current_video:
            video = self.current_video
            duration = video.duration
            position = video.position            
            newPosition = position + seconds

            if newPosition < 0:
                newPosition = 0
            elif newPosition > duration:
                newPosition = duration                        
            
            if newPosition < duration:
                newPositionPercent = newPosition / duration
            else:
                newPositionPercent = 1

            logging.info(f'Seek by {seconds:.2f}, Current {position:.2f} ({position / duration * 100:.2f}), New {newPosition:.2f} ({newPositionPercent * 100:.2f})')

            if abs(newPosition - position) > 0.1:
                if video.state in ('stop'):
                    video.state = 'play'

                video.seek(newPositionPercent, precise = False)

    def videoNextFrame(self):
        if self.current_video:            
            video = self.current_video
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
                    self.seeked_frames += 1

    def video_extract_frame(self):
        if self.current_video:
            video = self.current_video
            if video.state == 'pause':
                ff_video = video._video
                frame = ff_video._next_frame
                image = video_frame.get_frame_image(frame[0])

                path = self.app.thumbnail_view.currentFile.path

                parts = os.path.splitext(path)
                extension = parts[1].lower()

                suffixNumber = 1
                while (True):
                    frame_path = parts[0] + ' ' + str(suffixNumber) + '.jpg'
                    if not os.path.exists(frame_path):
                        break
                    suffixNumber = suffixNumber + 1

                image.save(frame_path, format='jpeg')
                self.app.thumbnail_view.insertThumbnail(frame_path)

    def video_extract_current_section(self):
        if self.current_video:
            video = self.current_video
            start = video.posotion # Todo - Set Markers
            end = start + 5
            self.video_extract_section(start, end)

    def video_extract_section(self, start, end):
        if self.current_video:
            video = self.current_video
            #if video.state == 'pause':



    def on_position_change(self, instance, value):
        if self.current_video:
            progress = self.ids.progress
            progress.value = value /  self.current_video.duration * progress.max

    def on_duration_change(self, instance, value):
        pass #print('The duration of the video is', value)       

    def on_state_change(self, instance, value):
        if self.current_video and value == 'play':
            self.ids.play_pause_button.source = 'images\\pause.png'
        else:
            self.ids.play_pause_button.source = 'images\\play.png'
            
    
    def fade_out_overlay(self):        
        if self.manager.current == 'ImageView' and self.ids.overlay.opacity > 0 and not self.fade_out_animation.have_properties_to_animate(self.ids.overlay):            
            self.fade_in_animation.cancel(self.ids.overlay)
            self.fade_out_animation.start(self.ids.overlay)
            Window.show_cursor = False
    
    def fade_in_overlay(self):
        self.start_overlay_timeout()
        if self.ids.overlay.opacity < 0.8 and not self.fade_in_animation.have_properties_to_animate(self.ids.overlay):            
            self.fade_out_animation.cancel(self.ids.overlay)
            self.fade_in_animation.start(self.ids.overlay)
            Window.show_cursor = True

    def start_overlay_timeout(self):
        self.fade_out_trigger.cancel()
        self.fade_out_trigger()

    def on_fade_out_trigger(self, *args):
        self.fade_out_overlay()

    def on_mouse_pos(self, *args):
        self.fade_in_overlay()

    def setup_buttons(self):
        self.buttons = [(self.ids.back_button, self.go_back)
            , (self.ids.previous_button, self.previous_image)
            , (self.ids.next_button, self.next_image)
            , (self.ids.full_screen_button, self.toggle_full_screen)
            , (self.ids.play_pause_button, self.toggle_play_pause)
            , (self.ids.edit_button, self.edit_image)]

    def on_touch_down(self, touch):
        self.fade_in_overlay()    
    
    def on_touch_up(self, touch):
        touch.push()
        try:
            touch.apply_transform_2d(self.to_local)

            progress = self.ids.progress
            if self.current_video and progress.collide_point(*touch.pos):
                touch.apply_transform_2d(progress.to_local)
                position = touch.pos[0] / progress.width
                self.seek_to_position(position)                

                return True
            else:            
                for (button, callback) in self.buttons:
                    if button.collide_point(*touch.pos):                
                        if callback():
                            return True                            
                
                return False
        finally:
            touch.pop()      

    def on_key_down(self, window, keycode, text, modifiers, x):        
        if self.manager.current == self.name:
            #print('image_view Key Down: ' + str(keycode))
            # Navigation
            if keycode == Keyboard.keycodes['escape']:
                self.go_back()            
            elif keycode in [Keyboard.keycodes['left'], Keyboard.keycodes['numpad4']]:
                self.change_image(1)
            elif keycode in [Keyboard.keycodes['right'], Keyboard.keycodes['numpad6']]:                
                self.change_image(-1)
            elif keycode in [Keyboard.keycodes['home']]:
                self.change_image(1000000) # Big number will stop at the first image (highest index).
            elif keycode in [Keyboard.keycodes['end']]:
                self.change_image(-1000000) # Big negative number will stop at the last image (0 index).
            elif keycode in [Keyboard.keycodes['delete'], Keyboard.keycodes['numpaddecimal']]:
                self.delete()
            # Video Controls
            elif keycode in [Keyboard.keycodes['spacebar'], Keyboard.keycodes['p'], Keyboard.keycodes['numpad2']]:
                self.toggle_play_pause()
            elif keycode in [Keyboard.keycodes[','], Keyboard.keycodes['numpad1']]:
                self.video_seek_by_seconds(-5)
            elif keycode in [Keyboard.keycodes['.'], Keyboard.keycodes['numpad3']]:
                self.video_seek_by_seconds(10)
            elif keycode in [Keyboard.keycodes[';'], Keyboard.keycodes['numpad7']]:
                self.video_seek_by_seconds(-1)
            elif keycode in [Keyboard.keycodes['\''], Keyboard.keycodes['numpad9']]:            
                self.videoNextFrame()
            elif keycode in [Keyboard.keycodes['f']]:
                self.video_extract_frame()
            elif keycode in [Keyboard.keycodes['g']]:
                self.video_extract_current_section()
            elif keycode == Keyboard.keycodes['f11']:
                self.toggle_full_screen()

            return True
        
        return False
    
    def on_key_up(self, window, keycode, text):
        pass
        #if self.manager.current == self.name:
        #    print('ImagveView Key Up: ' + str(keycode))

    def toggle_full_screen(self):
        if Window.fullscreen == False:
            Window.fullscreen = 'auto'
            self.ids.full_screen_button.source = 'images\\fullscreen-exit.png'
        else:
            Window.fullscreen = False
            self.ids.full_screen_button.source = 'images\\fullscreen.png'
        
        return True
    
    def seek_to_position(self, position):
        if self.current_video:            
            if self.current_video.state not in ['play', 'pause']:
                self.toggle_play_pause()
            self.current_video.seek(position, False)

            return True
        
        return False
        