from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy_garden.drag_n_drop import *
from kivy.graphics import *
from kivy.metrics import sp
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage
from PIL import Image as PILImage
from kivy.core.window import Window, Keyboard
import ffmpeg
from io import BytesIO

import os
import threading

drag_controller = DraggableController()

class DraggableGridLayout(DraggableLayoutBehavior, GridLayout):
    def compare_pos_to_widget(self, widget, pos):
        return 'before' if pos[0] < widget.center_x else 'after'

    def handle_drag_release(self, index, drag_widget):
        self.remove_widget(drag_widget)
        self.add_widget(drag_widget, index)

    def get_drop_insertion_index_move(self, x, y):
        pass
    
class ThumbnailImage(Image):
    pass

class ThumbnailWidget(DraggableObjectBehavior, FloatLayout):
    def __init__(self, **kwargs):
        super(ThumbnailWidget, self).__init__(
            **kwargs, drag_controller=drag_controller)

    def complete_drag(self):
        # during a drag, we remove the widget from the original location
        self.thumbnailView.thumbnailCompleteDrag(self)

Builder.load_file('views/thumbnailView.kv')

def sizeCallback(obj, value):
    obj.text_size = (value[0] - sp(30), sp(20))

class ThumbnailView(Screen):
    cellWidth = sp(160)
    cellHeight = cellWidth * 4 / 5
    marginSize = 0.04
    thumbnailSize = 1 - (marginSize * 2)
    thumbnailWidth = cellWidth * thumbnailSize
    thumbnailHeight = cellHeight * thumbnailSize
    columns = 1
    currentIndex = None
    currentImage = None
    currentFile = None    

    def __init__(self, **kwargs):        
        super(ThumbnailView, self).__init__(**kwargs)                   
        self.version = 0
        Window.bind(on_resize=self.on_window_resize)
        Window.bind(on_key_up=self.on_key_up)
        Window.bind(on_key_down=self.on_key_down)

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
        self.columns = int(thumbnailGridWidth / self.cellWidth)
        if self.columns < 1:
            self.columns = 1

        thumbnailGrid.cols = self.columns
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
                        if extension in app.data.allTypes:                            
                            coreImage = self.getThumbnailImage(entry.path, extension)                            
                            self.addThumbnail(app, thumbnailGrid, entry.path, coreImage)

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
    def addThumbnail(self, app, thumbnailGrid, path, coreImage):        
        thumbnailWidget = ThumbnailWidget()
        thumbnailWidget.drag_cls = 'thumbnailLayout'        
        thumbnailWidget.bind(on_touch_down = self.thumbnailTouchDown)        
        thumbnailWidget.thumbnailView = self
        
        thumbnailImage = ThumbnailImage() 
        thumbnailWidget.drag_cls = 'thumbnailLayout'                         
        thumbnailImage.texture = coreImage.texture        
        thumbnailImage.pos_hint = {'x': self.marginSize, 'y': self.marginSize}
        thumbnailImage.size_hint = (self.thumbnailSize, self.thumbnailSize)    
        thumbnailImage.filePath = path

        thumbnailWidget.add_widget(thumbnailImage)
        thumbnailGrid.add_widget(thumbnailWidget)

        self.updateGridSize(Window.width)

    def showSelected(self, object):
        if object:
            object.canvas.after.clear()

            width = object.size[0]
            height = object.size[1]

            imageWidth = object.texture_size[0]
            imageHeight = object.texture_size[1]

            x = object.pos[0] + ((width - imageWidth) / 2)
            y = object.pos[1] + ((height - imageHeight) / 2)

            with object.canvas.after:
                Color(0.207, 0.463, 0.839, mode='rgb')
                Line(width=sp(2), rectangle=(x, y, imageWidth, imageHeight))

    def hideSelected(self, object):
        if object:
            object.canvas.after.clear()

    def updateGridSize(self, width):
        app = App.get_running_app()  

        thumbnailGrid = self.ids.thumbnailGrid
        thumbnailGridWidth = width - sp(app.data.foldersWidth)
        self.columns = int(thumbnailGridWidth / self.cellWidth)
        if self.columns < 1:
            self.columns = 1
        thumbnailGrid.cols = self.columns
        thumbnailGrid.height = self.cellHeight * int(len(thumbnailGrid.children) / self.columns + 0.5)

        # The selection dissappears on resize so show again.
        Clock.schedule_once(lambda x: self.showSelected(self.currentImage), 0.1)         

    def getWidgetAt(self, x, y):
        thumbnailGrid = self.ids.thumbnailGrid
        for widget in thumbnailGrid.children:
            if widget.collide_point(x, y):
                return widget
        return None

    def thumbnailTouchDown(self, instance, touch):                               
        if touch.grab_current == None:
            widget = self.getWidgetAt(touch.x, touch.y)
            if widget:
                image = widget.children[0]
                
                if touch.is_double_tap or image != self.currentImage:
                    self.hideSelected(self.currentImage)
                            
                    thumbnailGrid = self.ids.thumbnailGrid
                    self.currentIndex = thumbnailGrid.children.index(widget)
                    self.currentImage = image
                    self.currentFile = image.filePath

                    self.showSelected(image)

                    if touch.is_double_tap:
                        self.manager.transition.direction = 'left'
                        self.manager.current = 'ImageView'
                                        
                    super(ThumbnailWidget, widget).on_touch_down(touch)

                    return True
   
    def thumbnailCompleteDrag(self, instance):                               
        if self.currentImage:
            self.hideSelected(self.currentImage)
            Clock.schedule_once(lambda x: self.showSelected(self.currentImage), 0.1)            

    def selectImage(self, offset):
        self.hideSelected(self.currentImage)
        
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
            thumbnailWidget = thumbnailGrid.children[newIndex]
            image = thumbnailWidget.children[0]
            self.currentImage = image
            self.currentFile = image.filePath

            self.showSelected(image)

    def on_key_down(self, window, keycode, text, modifiers, x):
        if self.manager.current == self.name:
            print('ThumbnailView Key Down: ' + str(keycode))
            if keycode == Keyboard.keycodes['right']:
                self.selectImage(-1)
            elif keycode == Keyboard.keycodes['left']:
                self.selectImage(1)
            elif keycode == Keyboard.keycodes['down']:
                self.selectImage(-self.columns)
            elif keycode == Keyboard.keycodes['up']:
                self.selectImage(self.columns)
            elif keycode == Keyboard.keycodes['enter']:
                self.manager.transition.direction = 'left'
                self.manager.current = 'ImageView'   
    
    def on_key_up(self, window, keycode, text):
        if self.manager.current == self.name:
            print('ThumbnailView Key Up: ' + str(keycode))
