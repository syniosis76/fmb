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

from views.thumbnail_view import thumbnail_view
from views.image_view import image_view
from views.image_editor import image_editor

from kivy.logger import Logger, LOG_LEVELS
Logger.setLevel(LOG_LEVELS["info"]) # trace, debug, info, warning, error, critical

class fmb_app(App):
    closing = False
    thumbnail_view = None
    image_view = None
    image_editor = None

    def build(self):
        Window.clearcolor = (0.118, 0.118, 0.118, 1)

        self.maximized = False

        Window.bind(on_request_close=self.window_request_close)
        Window.bind(on_maximize=self.on_maximize)
        Window.bind(on_minimize=self.on_minimize)
        Window.bind(on_restore=self.on_restore)        

        self.data = Data()
        
        self.screenManager = ScreenManager()
        self.screenManager.transition = NoTransition()

        self.thumbnail_view = thumbnail_view(name='thumbnail_view')
        self.screenManager.add_widget(self.thumbnail_view)
        
        self.image_view = image_view(name='image_view')
        self.screenManager.add_widget(self.image_view)

        self.image_editor = image_editor(name='image_editor')                
        self.screenManager.add_widget(self.image_editor)

        return self.screenManager        

    def on_start(self):
        self.restore_window_position()

    def on_stop(self):
        self.closing = True
        self.config.write()

    def on_maximize(self, *largs):
        self.maximized = True

    def on_minimize(self, *largs):
        self.maximized = True

    def on_restore(self, *largs):
        self.maximized = False

    def window_request_close(self, win):                
        self.store_window_position()    
        return False
    
    def store_window_position(self):
        # Window.size is automatically adjusted for density, must divide by density when saving size        
        window_position = self.data.window_position
        window_position['width'] = int(Window.size[0]/Metrics.density)
        window_position['height'] = int(Window.size[1]/Metrics.density)
        window_position['top'] = Window.top
        window_position['left'] = Window.left        
        window_position['maximised'] = self.maximized

        self.data.save()
        
    def restore_window_position(self):
        window_position = self.data.window_position       
        width = window_position.get('width', 800)
        height = window_position.get('height', 600)
        Window.size = (int(width), int(height))
        Window.top = int(window_position.get('top', 40))
        Window.left = int(window_position.get('left', 40))

        if window_position.get('maximised', False):
            Window.maximize()

if __name__ == '__main__':
    fmb_app().run()