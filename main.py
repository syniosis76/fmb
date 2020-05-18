import kivy
kivy.require('1.0.7')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window
from kivy.clock import mainthread

from models.data import Data

from views.thumbnailView import ThumbnailView
from views.imageView import ImageView

class FmbApp(App):
    closing = False

    def build(self):
        Window.clearcolor = (0.118, 0.118, 0.118, 1)

        self.data = Data()
        
        self.screenManager = ScreenManager()
        self.screenManager.add_widget(ThumbnailView(name='ThumbnailView'))
        self.screenManager.add_widget(ImageView(name='ImageView1'))
        self.screenManager.add_widget(ImageView(name='ImageView2'))

        return self.screenManager

    def on_stop(self):
        self.closing = True

if __name__ == '__main__':
    FmbApp().run()