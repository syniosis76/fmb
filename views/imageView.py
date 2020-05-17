from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.metrics import sp

Builder.load_file('views/imageView.kv')

def sizeCallback(obj, value):
    obj.text_size = (value[0] - sp(30), sp(20))

class ImageView(Screen):
    def __init__(self, **kwargs):
        super(ImageView, self).__init__(**kwargs)                   

    def on_pre_enter(self):
        self.loadImage()

    def loadImage(self):
        pass        
    
    def backButtonClick(self, instance):
        print('Back button clicked.')

        self.manager.transition.direction = 'right'
        self.manager.current = 'ThumbnailView'