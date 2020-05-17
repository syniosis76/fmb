from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.metrics import sp
from kivy.clock import Clock
from kivy.core.window import Window

import os

Builder.load_file('views/thumbnailView.kv')

def sizeCallback(obj, value):
    obj.text_size = (value[0] - sp(30), sp(20))

class ThumbnailView(Screen):
    iconWidth = sp(160)
    iconHeight = iconWidth * 4 / 5

    def __init__(self, **kwargs):        
        super(ThumbnailView, self).__init__(**kwargs)                   
        self.version = 0
        Window.bind(on_resize=self.on_window_resize)

    def on_enter(self):
        app = App.get_running_app()
        if app.data.hasUpdated(self.version):      
            Clock.schedule_once(lambda x: self.buildUi(), 0.1)        

    def on_window_resize(self, window, width, height):
        app = App.get_running_app()  

        thumbnailGrid = self.ids.thumbnailGrid
        thumbnailGridWidth = width - sp(app.data.foldersWidth)
        columns = int(thumbnailGridWidth / self.iconWidth)
        thumbnailGrid.cols = columns
        thumbnailGrid.height = self.iconHeight * int(len(thumbnailGrid.children) / columns + 0.5)

    def buildUi(self):        
        app = App.get_running_app()        
        
        folderBox = self.ids.folderBox
        folderBox.width = sp(app.data.foldersWidth)

        thumbnailGrid = self.ids.thumbnailGrid

        thumbnailGridWidth = Window.width - sp(app.data.foldersWidth)
        columns = int(thumbnailGridWidth / self.iconWidth)

        thumbnailGrid.cols = columns
        thumbnailGrid.col_default_width = self.iconWidth
        thumbnailGrid.col_force_default = True
        thumbnailGrid.row_default_height = self.iconHeight
        thumbnailGrid.row_force_default = True
        thumbnailGrid.size_hint_y = None 

        folder = app.data.currentFolder
    
        with os.scandir(folder) as scandir:
            for entry in scandir:
                entry.name
                thumbnailWidget = Button()
                thumbnailWidget.text = entry.name
                thumbnailGrid.add_widget(thumbnailWidget)
                thumbnailGrid.height = self.iconHeight * int(len(thumbnailGrid.children) / columns + 0.5)

        self.version = app.data.version              
                      
    def thumbnailClick(self, instance):
        print('Image <%s> clicked.' % instance.text)
        #app = App.get_running_app()        

        self.manager.transition.direction = 'left'
        self.manager.current = 'ImageView1'    