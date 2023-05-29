import logging
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy_garden.drag_n_drop import *
from kivy.graphics import *
from kivy.metrics import sp
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window, Keyboard

from send2trash import send2trash

import os
import threading
import json

from models.folder import Folder
from models.mediafile import MediaFile
from utilities.thumbnail import Thumbnail

drag_controller = DraggableController()

class DraggableGridLayout(DraggableLayoutBehavior, GridLayout):
    def __init__(self, **kwargs):
        super(DraggableGridLayout, self).__init__(**kwargs)
        self.register_event_type('on_drag_complete')

    def compare_pos_to_widget(self, widget, pos):
        return 'before' if pos[0] < widget.center_x else 'after'

    def handle_drag_release(self, index, drag_widget):
        current_index = self.children.index(drag_widget)
        if index > current_index:
            index = index - 1
        self.remove_widget(drag_widget)
        self.add_widget(drag_widget, index)
        self.dispatch('on_drag_complete')

    def get_drop_insertion_index_move(self, x, y):
        pass

    def on_drag_complete(self):
        pass

class ThumbnailImage(Image):    
    def __init__(self, **kwargs):
        super(ThumbnailImage, self).__init__(**kwargs)
        self.focused = False
        self.selected = False
        self.outline_offset = None
        self.outline_colour = None
        self.outline_line = None

        self.bind(pos=self.set_pos_callback)

    def clear_canvas_after_operations(self):
        logging.info(f'Clear Canvas After Operations for {self.mediaFile.name}')
        
        current_outline_line = self.outline_line
        current_outline_colour = self.outline_colour

        self.outline_offset = None
        self.outline_colour = None
        self.outline_line = None  
        
        if current_outline_line:
            self.canvas.after.remove(current_outline_line)
            
        if current_outline_colour:
            self.canvas.after.remove(current_outline_colour)                      

    def show_selected(self):
        self.selected = True            

        self.clear_canvas_after_operations()

        # Add blue outline.

        width = self.size[0]
        height = self.size[1]

        imageWidth = self.texture_size[0]
        imageHeight = self.texture_size[1]

        x_offset = ((width - imageWidth) / 2)
        y_offset = ((height - imageHeight) / 2)
        
        self.outline_offset = (x_offset, y_offset)
        self.outline_colour = Color(0.207, 0.463, 0.839, mode='rgb')
        self.outline_line = Line(width=sp(2), rectangle=(self.pos[0] + x_offset, self.pos[1] + y_offset, imageWidth, imageHeight))

        self.canvas.after.add(self.outline_colour)
        self.canvas.after.add(self.outline_line)

    def hide_selected(self):
        self.selected = False
        self.clear_canvas_after_operations()

    def set_pos_callback(self, obj, value):
        if self.outline_line and self.outline_line.rectangle:
            width = self.outline_line.rectangle[2]
            height = self.outline_line.rectangle[3]
            self.outline_line.rectangle = (self.pos[0] + self.outline_offset[0], self.pos[1] + self.outline_offset[1], width, height)

class ThumbnailWidget(DraggableObjectBehavior, FloatLayout):    
    def __init__(self, **kwargs):
        super(ThumbnailWidget, self).__init__(**kwargs, drag_controller=drag_controller)

Builder.load_file('views/thumbnailView.kv')

class ThumbnailView(Screen):
    app = None
    data = None
    columns = 1
    currentIndex = None
    shift_index = None
    currentImage = None
    currentFile = None
    folder = Folder()
    cancel_thread = None
    thread = None
    keyboard_modifiers = []

    def __init__(self, **kwargs):
        super(ThumbnailView, self).__init__(**kwargs)
        self.app = App.get_running_app()
        self.data = self.app.data
        self.version = 0
        self.cancel_thread = threading.Event()
        Window.bind(on_resize=self.on_window_resize)
        Window.bind(on_key_up=self.on_key_up)
        Window.bind(on_key_down=self.on_key_down)
        self.save_layout_trigger = Clock.create_trigger(self.on_save_layout_trigger, timeout=5, interval=False, release_ref=False)

    def on_enter(self):
        if self.data.hasUpdated(self.version):
            Clock.schedule_once(lambda x: self.buildUi(), 0.1)

    def on_window_resize(self, window, width, height):
        self.updateThumbnailGridSize(width)
        self.updateFolderGridSize()

    def changePath(self, path):
        self.data.currentFolder = path
        self.showThumbnails()
        self.data.save()

    def buildUi(self):
        self.showThumbnails()
        self.showFolders()

    def showThumbnails(self):
        if self.thread and not self.cancel_thread.is_set():
            logging.info('Thread Cancel')
            self.cancel_thread.set()
            logging.info('Thread Wait')
            self.thread.join() # Wait for completion.
            logging.info('Thread Complete')
            self.thread = None

        Clock.schedule_once(lambda dt: self.showThumbnailsSchedule())

    def showThumbnailsSchedule(self):
        thumbnailGrid = self.ids.thumbnailGrid
        thumbnailGrid.clear_widgets()
        self.cancel_thread.clear()
        self.thread = threading.Thread(target=self.showThumbnailsThread)
        self.thread.start()

    def showThumbnailsThread(self):
        self.version = self.data.version

        added_files = []

        folderBox = self.ids.folderBox
        folderBox.width = sp(self.data.foldersWidth)

        thumbnailGrid = self.ids.thumbnailGrid

        thumbnailGridWidth = Window.width - sp(self.data.foldersWidth)
        self.columns = int(thumbnailGridWidth / self.data.cellWidth)
        if self.columns < 1:
            self.columns = 1

        thumbnailGrid.cols = self.columns
        thumbnailGrid.col_default_width = self.data.cellWidth
        thumbnailGrid.col_force_default = True
        thumbnailGrid.row_default_height = self.data.cellHeight
        thumbnailGrid.row_force_default = True
        thumbnailGrid.size_hint_y = None

        path = self.data.currentFolder

        # First load from saved layout
        layout = self.load_layout()
        if layout:
            for file in layout['files']:
                if self.cancel_thread.is_set():
                    logging.info('Exit Thread on Cancel')
                    break
                if self.app.closing:
                    logging.info('Exit Thread on Close')
                    break
                mediaFile = MediaFile(os.path.join(path, file['name']))
                if mediaFile.exists and not mediaFile.name in added_files:
                    added_files.append(mediaFile.name)
                    mediaFile.readModified()
                    thumbnail = Thumbnail(mediaFile)
                    thumbnail.initialiseThumbnail()
                    mediaFile.thumbnailPath = thumbnail.thumbnailPath
                    coreImage = CoreImage(thumbnail.thumbnailPath)
                    self.addThumbnail(thumbnailGrid, mediaFile, coreImage, None)

        # Load any new files from disk
        self.folder.loadPath(path)
        self.folder.sortByModified()

        for file in self.folder.files:
            if self.cancel_thread.is_set():
                logging.info('Exit Thread on Cancel')
                break
            if self.app.closing:
                logging.info('Exit Thread on Close')
                break
            if not file.name in added_files:
                added_files.append(file.name)
                thumbnail = Thumbnail(file)
                thumbnail.initialiseThumbnail()
                file.thumbnailPath = thumbnail.thumbnailPath
                coreImage = CoreImage(thumbnail.thumbnailPath)
                self.addThumbnail(thumbnailGrid, file, coreImage, None)

        self.version = self.data.version

        self.trigger_save_layout()

        self.cancel_thread.clear()

    def thumbnail_exists(self, file_name):
        thumbnailGrid = self.ids.thumbnailGrid
        length = len(thumbnailGrid.children)

        for widget in thumbnailGrid.children:
            image = widget.children[0]
            media_file = image.mediaFile
            if media_file.name == file_name:
                return True

        return False

    @mainthread
    def addThumbnail(self, thumbnailGrid, mediaFile, coreImage, index):
        logging.info('Thumbnail - ' + mediaFile.name)
        thumbnailWidget = ThumbnailWidget()
        thumbnailWidget.drag_cls = 'thumbnailLayout'
        thumbnailWidget.bind(on_touch_down = self.thumbnailTouchDown)
        thumbnailWidget.thumbnailView = self

        thumbnailImage = ThumbnailImage()
        thumbnailWidget.drag_cls = 'thumbnailLayout'
        thumbnailImage.texture = coreImage.texture
        thumbnailImage.pos_hint = {'x': self.data.marginSize, 'y': self.data.marginSize}
        thumbnailImage.size_hint = (self.data.thumbnailSize, self.data.thumbnailSize)
        thumbnailImage.mediaFile = mediaFile
        thumbnailImage.bind(pos = self.thumbnailPosChanged)

        thumbnailWidget.add_widget(thumbnailImage)
        if index == None:
            thumbnailGrid.add_widget(thumbnailWidget)
        else:
            thumbnailGrid.add_widget(thumbnailWidget, index)

        if self.currentIndex:
            self.currentIndex = self.currentIndex + 1

        self.updateThumbnailGridSize(Window.width)

        #logging.info('Adding Complete - ' + mediaFile.name)

        return mediaFile.name

    def insertThumbnail(self, frame_path):
        thumbnailGrid = self.ids.thumbnailGrid

        file = MediaFile(frame_path)
        thumbnail = Thumbnail(file)
        thumbnail.initialiseThumbnail()
        file.thumbnailPath = thumbnail.thumbnailPath
        coreImage = CoreImage(thumbnail.thumbnailPath)
        self.addThumbnail(thumbnailGrid, file, coreImage, self.currentIndex)


    def showSelected(self, object):
        if object and not object.selected:
            logging.info('Select ' + object.mediaFile.name)

            object.show_selected()

    def hideSelected(self, object):
        if object and object.selected:
            logging.info('Deselect ' + object.mediaFile.name)           
            object.hide_selected()

    def clear_selected(self):        
        thumbnailGrid = self.ids.thumbnailGrid
        length = len(thumbnailGrid.children)

        for index in range(length - 1, -1, -1):
            widget = thumbnailGrid.children[index]
            image = widget.children[0]
            self.hideSelected(image)

    def thumbnailPosChanged(self, object, pos):
        if object == self.currentImage:
            self.showSelected(object)

    def updateThumbnailGridSize(self, width):
        thumbnailGrid = self.ids.thumbnailGrid
        thumbnailGridWidth = width - sp(self.data.foldersWidth)
        self.columns = int(thumbnailGridWidth / self.data.cellWidth)
        if self.columns < 1:
            self.columns = 1
        thumbnailGrid.cols = self.columns
        count = len(thumbnailGrid.children)
        rows = int(count / self.columns)
        if count % self.columns > 0:
            rows = rows + 1
        newHeight = self.data.cellHeight * rows
        if thumbnailGrid.height != newHeight:
            thumbnailGrid.height = newHeight

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
                    thumbnailGrid = self.ids.thumbnailGrid

                    if 'ctrl' not in self.keyboard_modifiers:
                        self.clear_selected()

                    if 'shift' in self.keyboard_modifiers:
                        self.shift_select(thumbnailGrid.children.index(widget))
                    else:
                        self.shift_index = None

                        self.currentIndex = thumbnailGrid.children.index(widget)
                        self.currentImage = image
                        self.currentFile = image.mediaFile

                        self.showSelected(image)

                        if touch.is_double_tap:
                            self.manager.transition.direction = 'left'
                            self.manager.current = 'ImageView'

                    super(ThumbnailWidget, widget).on_touch_down(touch)

                    return True

    def shift_select(self, selected_index):
        thumbnailGrid = self.ids.thumbnailGrid

        if self.shift_index == None:
            self.shift_index = self.currentIndex

        # Select all images beteen the initial and the current.
        start_index = min(selected_index, self.shift_index)
        end_index = max(selected_index, self.shift_index)
        for select_index in range(start_index, end_index + 1):
            select_widget = thumbnailGrid.children[select_index]
            select_image = select_widget.children[0]
            self.showSelected(select_image)

        # Focus the selected item
        current_widget = thumbnailGrid.children[selected_index]
        current_image = current_widget.children[0]
        self.currentIndex = selected_index
        self.currentImage = current_image
        self.currentFile = current_image.mediaFile

    def changeImage(self, offset):
        thumbnailGrid = self.ids.thumbnailGrid

        if len(thumbnailGrid.children) == 0:
            self.currentIndex = None
        else:
            if self.currentIndex == None:
                newIndex = 0
            else:
                newIndex = self.currentIndex + offset

            if 'ctrl' not in self.keyboard_modifiers:
                self.clear_selected()

            if 'shift' in self.keyboard_modifiers:
                self.shift_select(newIndex)
            else:
                self.shift_index = None

            return self.selectImage(newIndex)

        return False

    def selectImage(self, newIndex, force=False):
        thumbnailGrid = self.ids.thumbnailGrid

        if newIndex < 0:
            newIndex = 0
        elif newIndex > len(thumbnailGrid.children) - 1:
            newIndex = len(thumbnailGrid.children) - 1

        if force or self.currentImage == None or self.currentIndex != newIndex:
            if 'ctrl' not in self.keyboard_modifiers and 'shift' not in self.keyboard_modifiers:
                self.clear_selected()

            self.currentIndex = newIndex
            thumbnailWidget = thumbnailGrid.children[newIndex]
            image = thumbnailWidget.children[0]
            self.currentImage = image
            self.currentFile = image.mediaFile

            self.showSelected(image)

            return True

        return False

    def delete(self):
        if self.currentImage:
            threading.Thread(target=(lambda: self.deleteThread())).start()

    def deleteThread(self):
        currentIndex = self.currentIndex
        thumbnailGrid = self.ids.thumbnailGrid
        length = len(thumbnailGrid.children)

        for index in range(length - 1, -1, -1):
            widget = thumbnailGrid.children[index]
            image = widget.children[0]
            if image.selected:
                file = image.mediaFile
                self.deleteImage(image)
                self.deleteFile(file)
                currentIndex = index

        self.deleteComplete(currentIndex)

    @mainthread
    def deleteImage(self, image):
        widget = image.parent
        self.ids.thumbnailGrid.remove_widget(widget)

    def deleteFile(self, file):
        os.remove(file.thumbnailPath)
        send2trash(file.path)

    @mainthread
    def deleteComplete(self, index):
        self.selectImage(index - 1, True) # Select the next image.
        self.trigger_save_layout()

    def delete_current(self):
        if self.currentImage:
            currentImage = self.currentImage
            file = currentImage.mediaFile
            widget = self.currentImage.parent
            thumbnailGrid = self.ids.thumbnailGrid
            thumbnailGrid.remove_widget(widget)
            self.selectImage(self.currentIndex - 1, True) # Select the next image.            
            threading.Thread(target=(lambda: self.delete_current_thread(file))).start()
            self.trigger_save_layout()        
    
    def delete_current_thread(self, file):        
        os.remove(file.thumbnailPath)
        send2trash(file.path)

    def openHomeFolderClick(self):
        self.data.rootFolder = ''
        self.showFolders()
        self.data.save()

    def openParentFolderClick(self):
        parentFolder = os.path.dirname(self.data.rootFolder)
        if parentFolder == self.data.rootFolder or not os.path.exists(parentFolder):
            parentFolder = ''
        self.data.rootFolder = parentFolder
        self.showFolders()
        self.data.save()

    def onSelectRootFolder(self, selection):
        if selection:
            self.showRootFolder(selection[0])

    def showRootFolder(self, path):
        self.data.rootFolder = path
        self.data.currentFolder = path
        self.showFolders()
        self.showThumbnails()
        self.data.save()

    def on_key_down(self, window, keycode, text, modifiers, x):
        if self.manager.current == self.name:
            self.add_keyboard_modifier(keycode)

            #logging.info('ThumbnailView Key Down: ' + str(keycode))
            if keycode == Keyboard.keycodes['right']:
                self.changeImage(-1)
            elif keycode == Keyboard.keycodes['left']:
                self.changeImage(1)
            elif keycode == Keyboard.keycodes['down']:
                self.changeImage(-self.columns)
            elif keycode == Keyboard.keycodes['up']:
                self.changeImage(self.columns)
            elif keycode in [Keyboard.keycodes['home']]:
                self.changeImage(1000000) # Big number will stop at the first image (highest index).
            elif keycode in [Keyboard.keycodes['end']]:
                self.changeImage(-1000000) # Big negative number will stop at the last image (0 index).
            elif keycode == Keyboard.keycodes['enter']:
                self.manager.transition.direction = 'left'
                self.manager.current = 'ImageView'
            elif keycode == Keyboard.keycodes['delete']:
                self.delete()
            elif keycode == Keyboard.keycodes['f11']:
                self.toggle_full_screen()

    def on_key_up(self, window, keycode, text):
        if self.manager.current == self.name:
            self.remove_keyboard_modifier(keycode)
            #logging.info('ThumbnailView Key Up: ' + str(keycode))

    def add_keyboard_modifier(self, keycode):
        modifiers = self.get_keycode_modifiers(keycode)

        for modifier in modifiers:
            if modifier not in self.keyboard_modifiers:
                self.keyboard_modifiers.append(modifier)

    def remove_keyboard_modifier(self, keycode):
        modifiers = self.get_keycode_modifiers(keycode)

        for modifier in modifiers:
            if modifier in self.keyboard_modifiers:
                self.keyboard_modifiers.remove(modifier)

    def get_keycode_modifiers(self, keycode):
        if keycode == Keyboard.keycodes['rctrl']:
            return ['ctrl', 'rctrl']
        elif keycode == Keyboard.keycodes['lctrl']:
            return ['ctrl', 'lctrl']
        elif keycode == Keyboard.keycodes['shift']:
            return ['shift']

        return []

    def showFolders(self):
        folderGrid = self.ids.folderGrid
        folderGrid.clear_widgets()
        threading.Thread(target=self.showFoldersThread).start()

    def showFoldersThread(self):
        path = self.data.rootFolder
        folders = []
        if self.data.rootFolder == '':
            home = os.path.expanduser('~')

            entry = os.path.join(home, 'Pictures')
            if os.path.exists(entry):
                folders.append((entry, 'Pictures'))

            entry = os.path.join(home, 'Videos')
            if os.path.exists(entry):
                folders.append((entry, 'Videos'))

            entry = os.path.join(home, 'Documents')
            if os.path.exists(entry):
                folders.append((entry, 'Documents'))

            folders.append((home, 'Home'))
            for drive in range(ord('A'), ord('Z')):
                entry = chr(drive) + ':'
                if os.path.exists(entry):
                    folders.append((entry + '\\', entry))
        else:
            with os.scandir(path) as scandir:
                for entry in scandir:
                    if self.app.closing:
                        break
                    if entry.is_dir() and not entry.name.startswith('.'):
                        folders.append((entry.path, entry.name))

            folders.sort(key = lambda entry: entry[1])

        folderGrid = self.ids.folderGrid
        for (path, name) in folders:
            if self.app.closing:
                break
            self.addFolder(folderGrid, path, name)

    @mainthread
    def addFolder(self, foldersGrid, path, name):
        button = Button()
        button.text = name
        button.fmbPath = path
        button.size_hint = (1, None)
        button.height = self.data.folderHeight
        button.bind(on_press = self.folderButtonClick)

        foldersGrid.add_widget(button)

        self.updateFolderGridSize()

    def updateFolderGridSize(self):
        foldersGrid = self.ids.folderGrid
        rows = len(foldersGrid.children)
        newHeight = self.data.folderHeight * rows
        if foldersGrid.height != newHeight:
            foldersGrid.height = newHeight

    def folderButtonClick(self, widget):
        if widget.last_touch.is_double_tap:
            self.showRootFolder(widget.fmbPath)
        else:
            self.changePath(widget.fmbPath)

    def toggle_full_screen(self):
        if Window.fullscreen == False:
            Window.fullscreen = 'auto'
        else:
            Window.fullscreen = False

    def on_drag_complete(self):
        self.trigger_save_layout()

    def trigger_save_layout(self):
        self.save_layout_trigger.cancel()
        self.save_layout_trigger()

    def on_save_layout_trigger(self, *args):
        threading.Thread(target=self.save_layout).start()

    def save_layout(self):
        files = []

        thumbnailGrid = self.ids.thumbnailGrid
        length = len(thumbnailGrid.children)

        for index in range(length - 1, -1, -1):
            widget = thumbnailGrid.children[index]
            image = widget.children[0]
            media_file = image.mediaFile
            file_info = {}
            file_info['name'] = media_file.name
            files.append(file_info)

        layout = {}
        layout['version'] = 0.1
        layout['files'] = files

        with open(self.data.settings_file_name, 'w') as file:
            json.dump(layout, file)

    def load_layout(self):
        if os.path.exists(self.data.settings_file_name):
            with open(self.data.settings_file_name, 'r') as file:
                return json.load(file)
        return None


