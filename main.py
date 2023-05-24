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

    def on_stop(self):
        self.closing = True

if __name__ == '__main__':
    FmbApp().run()