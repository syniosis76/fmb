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
import logging

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

class thumbnail_image(Image):    
    def __init__(self, **kwargs):
        super(thumbnail_image, self).__init__(**kwargs)
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

class thumbnail_widget(DraggableObjectBehavior, FloatLayout):    
    def __init__(self, **kwargs):
        super(thumbnail_widget, self).__init__(**kwargs, drag_controller=drag_controller)

Builder.load_file('views/thumbnail_view.kv')

class thumbnail_view(Screen):
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
        super(thumbnail_view, self).__init__(**kwargs)
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
        self.update_thumbnail_grid_size(width)
        self.update_folder_grid_size()

    def changePath(self, path):
        self.data.currentFolder = path
        self.show_thumbnails()
        self.data.save()

    def buildUi(self):
        self.show_thumbnails()
        self.show_folders()

    def show_thumbnails(self):
        if self.thread and not self.cancel_thread.is_set():
            logging.info('Thread Cancel')
            self.cancel_thread.set()
            logging.info('Thread Wait')
            self.thread.join() # Wait for completion.
            logging.info('Thread Complete')
            self.thread = None

        Clock.schedule_once(lambda dt: self.show_thumbnails_schedule())

    def show_thumbnails_schedule(self):
        thumbnailGrid = self.ids.thumbnailGrid
        thumbnailGrid.clear_widgets()
        self.cancel_thread.clear()
        self.thread = threading.Thread(target=self.show_thumbnails_thread)
        self.thread.start()

    def show_thumbnails_thread(self):
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
                    self.add_thumbnail(thumbnailGrid, mediaFile, coreImage, None)

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
                self.add_thumbnail(thumbnailGrid, file, coreImage, None)

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
    def add_thumbnail(self, thumbnailGrid, mediaFile, coreImage, index):
        logging.info('Thumbnail - ' + mediaFile.name)
        thumbnailWidget = thumbnail_widget()
        thumbnailWidget.drag_cls = 'thumbnail_layout'
        thumbnailWidget.bind(on_touch_down = self.thumbnail_touch_down)
        thumbnailWidget.thumbnail_view = self

        thumbnailImage = thumbnail_image()
        thumbnailWidget.drag_cls = 'thumbnail_layout'
        thumbnailImage.texture = coreImage.texture
        thumbnailImage.pos_hint = {'x': self.data.marginSize, 'y': self.data.marginSize}
        thumbnailImage.size_hint = (self.data.thumbnailSize, self.data.thumbnailSize)
        thumbnailImage.mediaFile = mediaFile
        thumbnailImage.bind(pos = self.thumbnail_pos_changed)

        thumbnailWidget.add_widget(thumbnailImage)
        if index == None:
            thumbnailGrid.add_widget(thumbnailWidget)
        else:
            thumbnailGrid.add_widget(thumbnailWidget, index)

        if self.currentIndex:
            self.currentIndex = self.currentIndex + 1

        self.update_thumbnail_grid_size(Window.width)

        #logging.info('Adding Complete - ' + mediaFile.name)

        return mediaFile.name

    def insert_thumbnail(self, frame_path):
        thumbnailGrid = self.ids.thumbnailGrid

        file = MediaFile(frame_path)
        thumbnail = Thumbnail(file)
        thumbnail.initialiseThumbnail()
        file.thumbnailPath = thumbnail.thumbnailPath
        coreImage = CoreImage(thumbnail.thumbnailPath)
        self.add_thumbnail(thumbnailGrid, file, coreImage, self.currentIndex)


    def show_selected(self, object):
        if object and not object.selected:
            logging.info('Select ' + object.mediaFile.name)

            object.show_selected()

    def hide_selected(self, object):
        if object and object.selected:
            logging.info('Deselect ' + object.mediaFile.name)           
            object.hide_selected()

    def clear_selected(self):        
        thumbnailGrid = self.ids.thumbnailGrid
        length = len(thumbnailGrid.children)

        for index in range(length - 1, -1, -1):
            widget = thumbnailGrid.children[index]
            image = widget.children[0]
            self.hide_selected(image)

    def thumbnail_pos_changed(self, object, pos):
        if object == self.currentImage:
            self.show_selected(object)

    def update_thumbnail_grid_size(self, width):
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

    def get_widget_at(self, x, y):
        thumbnailGrid = self.ids.thumbnailGrid
        for widget in thumbnailGrid.children:
            if widget.collide_point(x, y):
                return widget
        return None

    def thumbnail_touch_down(self, instance, touch):
        if touch.grab_current == None:
            widget = self.get_widget_at(touch.x, touch.y)
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
                        self.update_title()

                        self.show_selected(image)

                        if touch.is_double_tap:
                            self.manager.transition.direction = 'left'
                            self.manager.current = 'image_view'

                    super(thumbnail_widget, widget).on_touch_down(touch)

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
            self.show_selected(select_image)

        # Focus the selected item
        current_widget = thumbnailGrid.children[selected_index]
        current_image = current_widget.children[0]
        self.currentIndex = selected_index
        self.currentImage = current_image
        self.currentFile = current_image.mediaFile
        self.update_title()

    def change_image(self, offset):
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

            return self.select_image(newIndex)

        return False

    def select_image(self, newIndex, force=False):
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
            self.update_title()

            self.show_selected(image)

            return True

        return False

    def delete(self):
        if self.currentImage:
            threading.Thread(target=(lambda: self.delete_thread())).start()

    def delete_thread(self):
        currentIndex = self.currentIndex
        thumbnailGrid = self.ids.thumbnailGrid
        length = len(thumbnailGrid.children)

        for index in range(length - 1, -1, -1):
            widget = thumbnailGrid.children[index]
            image = widget.children[0]
            if image.selected:
                file = image.mediaFile
                self.delete_image(image)
                self.delete_file(file)
                currentIndex = index

        self.delete_complete(currentIndex)

    @mainthread
    def delete_image(self, image):
        widget = image.parent
        self.ids.thumbnailGrid.remove_widget(widget)

    def delete_file(self, file):
        os.remove(file.thumbnailPath)
        send2trash(file.path)

    @mainthread
    def delete_complete(self, index):
        self.select_image(index - 1, True) # Select the next image.
        self.trigger_save_layout()

    def delete_current(self):
        if self.currentImage:
            currentImage = self.currentImage
            file = currentImage.mediaFile
            widget = self.currentImage.parent
            thumbnailGrid = self.ids.thumbnailGrid
            thumbnailGrid.remove_widget(widget)
            self.select_image(self.currentIndex - 1, True) # Select the next image.            
            threading.Thread(target=(lambda: self.delete_current_thread(file))).start()
            self.trigger_save_layout()        
    
    def delete_current_thread(self, file):        
        os.remove(file.thumbnailPath)
        send2trash(file.path)

    def open_home_folder_click(self):
        self.data.rootFolder = ''
        self.show_folders()
        self.data.save()

    def open_parent_folder_click(self):
        parentFolder = os.path.dirname(self.data.rootFolder)
        if parentFolder == self.data.rootFolder or not os.path.exists(parentFolder):
            parentFolder = ''
        self.data.rootFolder = parentFolder
        self.show_folders()
        self.data.save()

    def on_select_root_folder(self, selection):
        if selection:
            self.show_root_folder(selection[0])

    def show_root_folder(self, path):
        self.data.rootFolder = path
        self.data.currentFolder = path
        self.show_folders()
        self.show_thumbnails()
        self.data.save()

    def on_key_down(self, window, keycode, text, modifiers, x):
        if self.manager.current == self.name:
            self.add_keyboard_modifier(keycode)

            #logging.info('thumbnail_view Key Down: ' + str(keycode))
            if keycode == Keyboard.keycodes['right']:
                self.change_image(-1)
            elif keycode == Keyboard.keycodes['left']:
                self.change_image(1)
            elif keycode == Keyboard.keycodes['down']:
                self.change_image(-self.columns)
            elif keycode == Keyboard.keycodes['up']:
                self.change_image(self.columns)
            elif keycode in [Keyboard.keycodes['home']]:
                self.change_image(1000000) # Big number will stop at the first image (highest index).
            elif keycode in [Keyboard.keycodes['end']]:
                self.change_image(-1000000) # Big negative number will stop at the last image (0 index).
            elif keycode == Keyboard.keycodes['enter']:
                self.manager.transition.direction = 'left'
                self.manager.current = 'image_view'
            elif keycode == Keyboard.keycodes['delete']:
                self.delete()
            elif keycode == Keyboard.keycodes['f11']:
                self.toggle_full_screen()

    def on_key_up(self, window, keycode, text):
        if self.manager.current == self.name:
            self.remove_keyboard_modifier(keycode)
            #logging.info('thumbnail_view Key Up: ' + str(keycode))

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

    def show_folders(self):
        folderGrid = self.ids.folderGrid
        folderGrid.clear_widgets()
        threading.Thread(target=self.show_folders_thread).start()

    def show_folders_thread(self):
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
            self.add_folder(folderGrid, path, name)

    @mainthread
    def add_folder(self, foldersGrid, path, name):
        button = Button()
        button.text = name
        button.fmbPath = path
        button.size_hint = (1, None)
        button.height = self.data.folderHeight
        button.bind(on_press = self.folder_button_click)

        foldersGrid.add_widget(button)

        self.update_folder_grid_size()

    def update_folder_grid_size(self):
        foldersGrid = self.ids.folderGrid
        rows = len(foldersGrid.children)
        newHeight = self.data.folderHeight * rows
        if foldersGrid.height != newHeight:
            foldersGrid.height = newHeight

    def folder_button_click(self, widget):
        if widget.last_touch.is_double_tap:
            self.show_root_folder(widget.fmbPath)
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
    
    def update_title(self):
        if self.currentFile and self.currentFile.path:
            self.app.title = self.app.app_title + ' - ' + self.currentFile.path
        else:
            self.app.title = self.app.app_title


