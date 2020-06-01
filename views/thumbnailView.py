from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import sp
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage
from PIL import Image as PILImage
from io import BytesIO

import os
import threading

class ImageButton(ButtonBehavior, Image):
    pass

Builder.load_file('views/thumbnailView.kv')

def sizeCallback(obj, value):
    obj.text_size = (value[0] - sp(30), sp(20))

class ThumbnailView(Screen):
    cellWidth = sp(160)
    cellHeight = cellWidth * 4 / 5
    marginSize = 0.06
    thumbnailSize = 1 - marginSize
    thumbnailWidth = cellWidth * thumbnailSize
    thumbnailHeight = cellHeight * thumbnailSize

    def __init__(self, **kwargs):        
        super(ThumbnailView, self).__init__(**kwargs)                   
        self.version = 0
        Window.bind(on_resize=self.on_window_resize)

    def on_enter(self):
        app = App.get_running_app()
        if app.data.hasUpdated(self.version):      
            Clock.schedule_once(lambda x: self.buildUi(), 0.1)        

    def on_window_resize(self, window, width, height):
        self.updateGridSize(width)

    def buildUi(self):
        threading.Thread(target=self.buildUiThread).start()

    def buildUiThread(self):
        app = App.get_running_app()        
        self.version = app.data.version
        
        folderBox = self.ids.folderBox
        folderBox.width = sp(app.data.foldersWidth)

        thumbnailGrid = self.ids.thumbnailGrid

        thumbnailGridWidth = Window.width - sp(app.data.foldersWidth)
        columns = int(thumbnailGridWidth / self.cellWidth)

        thumbnailGrid.cols = columns
        thumbnailGrid.col_default_width = self.cellWidth
        thumbnailGrid.col_force_default = True
        thumbnailGrid.row_default_height = self.cellHeight
        thumbnailGrid.row_force_default = True
        thumbnailGrid.size_hint_y = None 

        folder = app.data.currentFolder
    
        with os.scandir(folder) as scandir:
            for entry in scandir:
                if app.closing:
                    break
                if entry.is_file:
                    parts = os.path.splitext(entry.name)
                    if len(parts) == 2:
                        extension = parts[1].lower()
                        if extension == '.jpg':
                            coreImage = self.getThumbnailImage(entry.path)
                            self.addThumbnail(app, thumbnailGrid, entry.path, coreImage)

        self.version = app.data.version                      

    def getThumbnailImage(self, path):
        app = App.get_running_app()        

        fileName = os.path.basename(path)
        thumbnailPath = os.path.join(app.data.currentWorkingFolder, fileName + '.tn')
        
        if os.path.exists(thumbnailPath):
            return CoreImage(thumbnailPath)
        else:
            # Ensure Working folder exists:
            os.makedirs(app.data.currentWorkingFolder, exist_ok=True)
            # Load Image
            pilImage = PILImage.open(path)
            # Make Thumbnail
            pilImage.thumbnail((self.thumbnailWidth, self.thumbnailHeight))
            # Save to Stream
            data = BytesIO()
            pilImage.save(data, format='png')
            # Save Stream to File
            data.seek(0)
            with open(thumbnailPath, "wb") as outfile:                
                outfile.write(data.getbuffer())
            # Return Image 
            data.seek(0)          
            return CoreImage(BytesIO(data.read()), ext='png')

    @mainthread               
    def addThumbnail(self, app, thumbnailGrid, path, coreImage):        
        thumbnailWidget = FloatLayout()
        
        thumbnailImage = ImageButton()                            
        thumbnailImage.texture = coreImage.texture
        thumbnailImage.bind(on_press = self.thumbnailClick)
        thumbnailImage.pos_hint = {'x': self.marginSize, 'y': self.marginSize}
        thumbnailImage.size_hint = (self.thumbnailSize, self.thumbnailSize)
        thumbnailImage.filePath = path

        thumbnailWidget.add_widget(thumbnailImage)
        thumbnailGrid.add_widget(thumbnailWidget)

        self.updateGridSize(Window.width)

    def updateGridSize(self, width):
        app = App.get_running_app()  

        thumbnailGrid = self.ids.thumbnailGrid
        thumbnailGridWidth = width - sp(app.data.foldersWidth)
        columns = int(thumbnailGridWidth / self.cellWidth)
        if columns < 1:
            columns = 1
        thumbnailGrid.cols = columns
        thumbnailGrid.height = self.cellHeight * int(len(thumbnailGrid.children) / columns + 0.5)    

    def thumbnailClick(self, instance):        
        app = App.get_running_app()        
        app.data.currentFile = instance.filePath

        self.manager.transition.direction = 'left'
        self.manager.current = 'ImageView1'