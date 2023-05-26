from startup_config import window_height, window_width, window_left, window_top

import utilities.loghandler

import os
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['KIVY_VIDEO'] = 'ffpyplayer'

import kivy
kivy.require('2.0.0')

from kivy.config import Config
Config.set('kivy', 'exit_on_escape', 0)
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, NoTransition
from kivy.metrics import Metrics
from kivy.core.window import Window

from models.data import Data

from views.thumbnailView import ThumbnailView
from views.imageView import ImageView
from views.image_editor import image_editor

from kivy.logger import Logger, LOG_LEVELS
Logger.setLevel(LOG_LEVELS["info"]) # trace, debug, info, warning, error, critical

class FmbApp(App):
    closing = False
    thumbnailView = None
    imageView = None
    image_editor = None

    def build(self):
        Window.clearcolor = (0.118, 0.118, 0.118, 1)

        Window.bind(on_request_close=self.window_request_close)

        self.data = Data()
        
        self.screenManager = ScreenManager()
        self.screenManager.transition = NoTransition()

        self.thumbnailView = ThumbnailView(name='ThumbnailView')
        self.screenManager.add_widget(self.thumbnailView)
        
        self.imageView = ImageView(name='ImageView')
        self.screenManager.add_widget(self.imageView)

        self.image_editor = image_editor(name='image_editor')                
        self.screenManager.add_widget(self.image_editor)

        return self.screenManager        

    def on_start(self):
        self.restore_window_position()

    def on_stop(self):
        self.closing = True
        self.config.write()

    def window_request_close(self, win):        
        self.store_window_position()
        return False
    
    def build_config(self, config):
        config.setdefaults('Window', {'width': window_width, 'height': window_height, 'top': window_top, 'left': window_left})
    
    def store_window_position(self):
        # Window.size is automatically adjusted for density, must divide by density when saving size        
        self.config.set('Window', 'width', int(Window.size[0]/Metrics.density))
        self.config.set('Window', 'height', int(Window.size[1]/Metrics.density))
        self.config.set('Window', 'top', Window.top)
        self.config.set('Window', 'left', Window.left)

    def restore_window_position(self):        
        width = self.config.getdefault('Window', 'width', window_width)
        height = self.config.getdefault('Window', 'height', window_height)
        Window.size = (int(width), int(height))
        Window.top = int(self.config.getdefault('Window', 'top', window_top))
        Window.left = int(self.config.getdefault('Window', 'left', window_left))

if __name__ == '__main__':
    FmbApp().run()