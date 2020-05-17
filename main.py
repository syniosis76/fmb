import kivy
kivy.require('1.0.7')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager

from models.data import Data

from views.thumbnailView import ThumbnailView
from views.imageView import ImageView

class BookerApp(App):    
    def build(self):
        self.data = Data()
        
        self.screenManager = ScreenManager()
        self.screenManager.add_widget(ThumbnailView(name='ThumbnailView'))
        self.screenManager.add_widget(ImageView(name='ImageView1'))
        self.screenManager.add_widget(ImageView(name='ImageView2'))

        return self.screenManager

if __name__ == '__main__':
    BookerApp().run()