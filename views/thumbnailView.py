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
import ffmpeg
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
    currentFile = None
    currentIndex = None

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

        fileIndex = 0
    
        with os.scandir(folder) as scandir:
            for entry in scandir:
                if app.closing:
                    break
                if entry.is_file:
                    parts = os.path.splitext(entry.name)
                    if len(parts) == 2:
                        extension = parts[1].lower()
                        if extension in app.data.allTypes:                            
                            coreImage = self.getThumbnailImage(entry.path, extension)                            
                            self.addThumbnail(app, thumbnailGrid, entry.path, fileIndex, coreImage)
                            fileIndex = fileIndex + 1

        self.version = app.data.version                      

    def getThumbnailImage(self, path, extension):
        app = App.get_running_app()        

        fileName = os.path.basename(path)
        thumbnailPath = os.path.join(app.data.currentWorkingFolder, fileName + '.tn')
        
        if os.path.exists(thumbnailPath):
            return CoreImage(thumbnailPath)
        else:
            # Ensure Working folder exists:
            os.makedirs(app.data.currentWorkingFolder, exist_ok=True)                        

            if extension in app.data.imageTypes:
                # Load Image
                pilImage = PILImage.open(path)                
            elif extension in app.data.videoTypes:
                buffer, error = (
                    ffmpeg
                    .input(path)
                    .filter('select', 'gte(n,{})'.format(60))
                    .output('pipe:', vframes=1, format='image2', vcodec='mjpeg')
                    .run(capture_stdout=True)
                )

                pilImage = PILImage.open(BytesIO(buffer))
            
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
    def addThumbnail(self, app, thumbnailGrid, path, fileIndex, coreImage):        
        thumbnailWidget = FloatLayout()
        
        thumbnailImage = ImageButton()                            
        thumbnailImage.texture = coreImage.texture
        thumbnailImage.bind(on_press = self.thumbnailClick)
        thumbnailImage.pos_hint = {'x': self.marginSize, 'y': self.marginSize}
        thumbnailImage.size_hint = (self.thumbnailSize, self.thumbnailSize)
        thumbnailImage.filePath = path
        thumbnailImage.fileIndex = fileIndex

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
        self.currentFile = instance.filePath
        self.currentIndex = instance.fileIndex

        self.manager.transition.direction = 'left'
        self.manager.current = 'ImageView'

    def selectImage(self, offset):
        thumbnailGrid = self.ids.thumbnailGrid

        if len(thumbnailGrid.children) == 0:
            self.currentIndex = None
        else:
            if self.currentIndex == None:            
                newIndex = 0
            else:
                newIndex = self.currentIndex + offset

            if newIndex < 0:
                newIndex = 0
            elif newIndex > len(thumbnailGrid.children) - 1:
                newIndex = len(thumbnailGrid.children) - 1

            self.currentIndex = newIndex
            thumbnailWidget = thumbnailGrid.children[len(thumbnailGrid.children) - 1 - newIndex]
            image = thumbnailWidget.children[0]
            self.currentFile = image.filePath

    def selectPreviousImage(self):
        pass
