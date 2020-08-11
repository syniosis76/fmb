import os
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['KIVY_VIDEO'] = 'ffpyplayer'

import kivy
kivy.require('1.11.1')

from kivy.config import Config
Config.set('kivy', 'exit_on_escape', 0)

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, NoTransition
from kivy.core.window import Window

from models.data import Data

from views.thumbnailView import ThumbnailView
from views.imageView import ImageView

class FmbApp(App):
    closing = False
    thumbnailView = None
    imageView = None

    def build(self):
        Window.clearcolor = (0.118, 0.118, 0.118, 1)

        self.data = Data()
        
        self.screenManager = ScreenManager()
        self.screenManager.transition = NoTransition()
        self.thumbnailView = ThumbnailView(name='ThumbnailView')
        self.imageView = ImageView(name='ImageView')
        self.screenManager.add_widget(self.thumbnailView)
        self.screenManager.add_widget(self.imageView)

        return self.screenManager

    def on_stop(self):
        self.closing = True

if __name__ == '__main__':
    FmbApp().run()