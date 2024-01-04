"""
This program starts a screensaver with high-resolution images and frames from videos in the specified directory.
NOTE: If there are not enough high-resolution images as compared to low-res images in the directory, the program can slow down considerably.
"""

import cv2
import numpy as np
import os
import random
import scipy.ndimage as ndi
import subprocess
import sys
import time
import tkinter as tk
import warnings

from ctypes import windll
from collections import deque
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk, UnidentifiedImageError
from typing import List

from settings import Settings, SettingsWindow
import utils

warnings.simplefilter('ignore', Image.DecompressionBombWarning) # Ignore warning (i.e. dont warn for images between 90 and 179 MP)
windll.shcore.SetProcessDpiAwareness(1)


class App():
    """ Press <Escape> once to go into manual mode. Press <Escape> again to resume the automatic slideshow.
        During manual mode, use the left and right arrow keys to move.
        During the automatic slideshow, press any key except <Escape> or move/click the mouse to exit.
        Press <o> at any time to open the file location in explorer (this closes the slideshow).
    """
    def __init__(self, settings: Settings = None, directories: List[str] = None, fullscreen: bool = False):
        self.settings = Settings() if settings is None else settings
        self.fullscreen = fullscreen

        ## Create the fullscreen window
        self.root = tk.Tk()
        self.root.report_callback_exception = utils.show_error
        if self.fullscreen:
            self.w_screen, self.h_screen = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            self.root.overrideredirect(1)
            self.root.geometry("%dx%d+0+0" % (self.w_screen, self.h_screen))
            self.root.config(cursor="none")
        else:
            self.w_screen, self.h_screen = self.root.winfo_screenwidth()//3, self.root.winfo_screenheight()//2
            self.root.geometry("%dx%d" % (self.w_screen, self.h_screen))
            self.root.config(cursor="crosshair")
        for action in ["<Escape>", "<Button>", "<Motion>", "<Key>"]: self.root.bind(action, self.userinput_received)

        self.root.bind("<Configure>", self.resize)
        self.last_resize_time = 0
        self.root.focus_set()
        self.canvas = tk.Canvas(self.root, width=self.w_screen, height=self.h_screen, bg='black', highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        ## Create ImageReel object
        if directories is None:
            directories = self.settings['directories']
            excluded_directories = self.settings['excluded_directories']
        else:
            excluded_directories = [] # If directories was specified explicitly, then don't exclude the subdirectories from the Settings
        if directories is None: directories = self.settings['directories']
        self.imagereel = ImageReel(self.w_screen, self.h_screen, directories, 
                                   excluded_directories=excluded_directories, only_high_res=self.settings['only_high_res'])
        self.imagesprite = self.canvas.create_image(self.w_screen//2, self.h_screen//2, image=None)
        
        self.paused = False
        self.text_escape = self.canvas.create_text(self.w_screen//2, 0, text="Slideshow paused. Press <Esc> to resume.", fill="white", anchor="n")
        self.text_loading = self.canvas.create_text(self.w_screen//2, self.h_screen//2, text="Loading...", fill="white", anchor="center")
        self.text_resizing = self.canvas.create_text(0, 0, text="Resizing image...", fill="white", anchor="nw")
        self.canvas_text_display(self.text_escape, False)
        self.canvas_text_display(self.text_loading, False)
        self.canvas_text_display(self.text_resizing, False)

    def canvas_text_display(self, text_id: int, show: bool):
        if show:
            self.canvas.lift(text_id)
            self.canvas.itemconfigure(text_id, state='normal')
        else:
            self.canvas.lower(text_id)
            self.canvas.itemconfigure(text_id, state='hidden')
    
    def run(self):
        self.root.after(0, self.mainIteration)
        self.root.mainloop()

    def resize(self, e, manual=True):
        """ If <manual> is True (default), it means that the resizing is done by the user.
            If it is False, it was scheduled and should actually redraw
            (if the user is not dragging the window edges anymore).
        """
        if e.width == self.w_screen and e.height == self.h_screen:
            return # No resize, just a generic "<Configure>" change
        
        # Waiting logic to prevent excessive recalculation of image
        wait_time = 200 # [ms]
        if manual:
            self.canvas_text_display(self.text_resizing, True)
            self.last_resize_time = time.time()
            self.root.after(wait_time, lambda: self.resize(e, manual=False))
            return # Let's wait a bit to see if the user is still actively dragging the window edges
        if time.time() - self.last_resize_time < wait_time/1000/1.5: # Divide by 1.5 to be sure
            return
        self.last_resize_time = time.time()

        # We waited long enough apparently, so recalculate the image
        self.canvas_text_display(self.text_resizing, False)
        self.w_screen, self.h_screen = self.root.winfo_width(), self.root.winfo_height()
        self.canvas.coords(self.text_escape, self.w_screen//2, 0)
        self.canvas.coords(self.text_loading, self.w_screen//2, self.h_screen//2)
        self.canvas.coords(self.imagesprite, self.w_screen//2, self.h_screen//2)
        self.imagereel.resize(self.w_screen, self.h_screen)
        self.show_image()

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            if self.fullscreen: self.root.config(cursor="crosshair")
            self.canvas_text_display(self.text_escape, True)
            self.root.after_cancel(self._nextImageLoop)
        else:
            if self.fullscreen: self.root.config(cursor="none")
            self.canvas_text_display(self.text_escape, False)
            self._nextImageLoop = self.root.after(int(self.settings['interval_seconds']*1000), self.mainIteration)
        self.root.update()
    
    def userinput_received(self, e: tk.Event):
        if e.type == tk.EventType.Key: # Do these things regardless whether the slideshow was 'paused'
            if e.keysym == 'Escape':
                return self.toggle_pause()
            if e.keysym == 'o': # TODO: does not work when this is run as a real screensaver, because screensaver hides all created windows upon screensaver exit
                try:
                    FILEBROWSER_PATH = os.path.join(os.getenv('WINDIR'), 'explorer.exe')
                    path = os.path.normpath(self.imagereel.current_filepath)
                    subprocess.Popen([FILEBROWSER_PATH, '/select,', path], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
                except:
                    pass
                self.exit()

        if not self.paused and self.fullscreen:
            self.exit()
        
        if e.type == tk.EventType.Key: # Only do this if 'paused'
            if e.keysym in ['Left', 'Right']:
                self.canvas_text_display(self.text_loading, True)
                self.root.update()
                if e.keysym == 'Left':
                    self.imagereel.previous()
                elif e.keysym == 'Right':
                    self.imagereel.next()
                self.show_image()
                self.canvas_text_display(self.text_loading, False)
                self.canvas_text_display(self.text_escape, True)
                self.root.update()
    
    def exit(self):
        return (self.root.withdraw(), self.root.quit())

    
    def mainIteration(self, repeat=True):
        t = time.time()
        self.imagereel.next()
        self.show_image()
        wait_ms = int(1000*max(.5, self.settings['interval_seconds'] - (time.time() - t)))
        if repeat: self._nextImageLoop = self.root.after(wait_ms, self.mainIteration)
    
    def show_image(self):
        self.root.image = ImageTk.PhotoImage(self.imagereel.im) # Assign to self.root to prevent garbage collection
        self.canvas.itemconfig(self.imagesprite, image=self.root.image)


class ImageReel:
    image_extensions = {'.png', '.jpg', '.jpeg', '.jfif', '.tiff', '.tif', '.bmp', '.webp'}
    video_extensions = {'.mp4', '.mkv', '.mov', '.wmv', '.avi', '.webm'}

    def __init__(self, w: int, h: int, directories: List[str], excluded_directories: List[str] = None, only_high_res: bool = True):
        self.w, self.h = w, h
        self._deque = deque(maxlen=128)
        self._index = 0
        self.im = Image.new(mode="RGB", size=(1, 1))

        self.ONLY_HIGH_RES = only_high_res
        self._fonts = {i: ImageFont.truetype("DejaVuSans.ttf", size=i) for i in range(1, 25)}

        ## Construct self.available_paths (list of all allowed files, given <directories> and <excluded_directories>)
        self.directories = [os.path.abspath(directory) for directory in directories]
        self.excluded_directories = [os.path.abspath(directory) for directory in excluded_directories]
        self.available_paths = [] # Fill this array with all the paths to individual images. Fast with os.walk.
        for directory in self.directories:
            if not os.path.exists(directory): continue
            for dirpath, dirnames, filenames in os.walk(directory, topdown=True):
                dirnames[:] = [d for d in dirnames if os.path.join(dirpath, d) not in self.excluded_directories] # Don't visit excluded directories at all
                self.available_paths += [os.path.abspath(os.path.join(dirpath, file)) for file in filenames
                                    if os.path.splitext(file)[1].lower() in ImageReel.image_extensions | ImageReel.video_extensions]
    
    def resize(self, w, h):
        self.w, self.h = w, h
        filepath, frameNumber = self._deque[self._index]
        self.im = self._open_image(filepath, frameNumber)

    def next(self):
        self._to_index(self._index - 1)

    def previous(self):
        self._to_index(self._index + 1)

    def _to_index(self, n: int):
        if n < 0:
            self.im, filepath, frameNumber = self._select_random()
            self._deque.appendleft((filepath, frameNumber))
        elif n >= len(self._deque):
            self.im, filepath, frameNumber = self._select_random()
            self._deque.append((filepath, frameNumber))
        else:
            filepath, frameNumber = self._deque[n]
            self.im = self._open_image(filepath, frameNumber)
        self._index = int(np.clip(n, 0, len(self._deque) - 1))
    
    @property
    def current_filepath(self):
        return self._deque[self._index][0]
    @property
    def current_frameNumber(self):
        return self._deque[self._index][1]

    def _select_random(self):
        random_index = random.randint(0, len(self.available_paths) - 1)
        filepath, frameNumber = self.available_paths[random_index], 0
        ext: str = os.path.splitext(filepath)[1]
        if ext.lower() in ImageReel.image_extensions:
            pass
        elif ext.lower() in ImageReel.video_extensions:
            cap = cv2.VideoCapture(filepath)
            num_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frameNumber = random.randint(0, num_frames)
        else:
            self._select_random()

        # Check if this fulfills the requirements, otherwise select another random image
        im = self._open_image(filepath, frameNumber=frameNumber)
        if im is None:
            self.available_paths.pop(random_index)
            return self._select_random()

        w, h = im.size
        if self.ONLY_HIGH_RES and (w < self.w/2 and h < self.h/2): # Then too small for the screen
            self.available_paths.pop(random_index)
            return self._select_random() # Just try another
        return im, filepath, frameNumber

    def _open_image(self, filepath: str, frameNumber: int = None, raise_err: bool = False):
        """ Returns None if the image could not be opened for some reason. """
        is_image = os.path.splitext(filepath)[1].lower() in ImageReel.image_extensions
        if is_image:
            try:
                im = Image.open(filepath)
                im = ImageOps.exif_transpose(im) # To get correct rotation (sometimes rotation info is hidden in EXIF)
            except (UnidentifiedImageError, Image.DecompressionBombError) as e: # DecompressionBombError if image more than 179 MegaPixels
                if raise_err: raise e
                return None
        else:
            cap = cv2.VideoCapture(filepath)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frameNumber) # set frame position
            success, image = cap.read()
            if not success:
                if raise_err: raise UnidentifiedImageError(f"Could not read frame {frameNumber} of video '{filepath}'.")
                return None
            im = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)) # Videos are in BGR, so convert to RGB
        
        ## Resize and annotate
        w, h = im.size
        ratio = min(self.w/w, self.h/h)
        im = im.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
        im = self._annotate_image(im, filepath)
        return im

    def _annotate_image(self, im: Image.Image, filepath: str, pad=10, interline=7):
        """ This is an extremely filthy function internally, but it does the job. :) """
        w, h = im.size
        full_im = Image.new('RGBA', (self.w, self.h), (0, 0, 0, 255))
        full_im.paste(im, (int((self.w - w)/2), int((self.h - h)/2)))

        ## Determine text size
        for directory in self.directories:
            if directory in filepath:
                filepath = filepath.replace(directory, '')[1:]
                break
        path_parts = os.path.splitext(filepath)[0].split('\\')
        path_parts[:-1] = [u"▶ " + part for part in path_parts[:-1]]
        path_parts.insert(0, directory)

        max_length_px, max_font_size = self.w/3, 24
        lengths_20 = [self._fonts[20].getbbox(part)[2] for part in path_parts]
        fontsizes = [min(max_font_size, int(max_length_px/length*20)) for length in lengths_20]
        if len(fontsizes) >= 3:
            fontsizes[1:-1] = [min(fontsizes[1:-1]) for _ in fontsizes[1:-1]] # Set all but the last directory to same font size
        fontsizes[0] = 8 # The base directory in very small text

        ## Calculate size of text and surrounding box
        text_im = Image.new('RGBA', (self.w, self.h), color=(255, 255, 255, 0))
        h_line_max, w_max = 0, 0
        for i, part in enumerate(path_parts):
            bbox = self._fonts[fontsizes[i]].getbbox(part)
            h_line_max = max(h_line_max, bbox[3]-bbox[1])
            w_max = max(w_max, bbox[2])
        w_rect, h_rect = w_max + interline + 3*pad, (h_line_max + interline)*(len(path_parts) - 1) + 2*pad + fontsizes[0] + interline

        ## Calculate which corner to put the textbox in
        if w/h < self.w/self.h:
            dh, dw = h_rect, (w - self.w)/2 + w_rect
        else:
            dw, dh = w_rect, (h - self.h)/2 + h_rect
        corner = ImageReel.least_cluttered_corner(im, dw, dh)
        anchor = ['lt', 'rt', 'rb', 'lb'][corner]
        east, south = anchor[0] == 'r', anchor[1] == 'b'
        if east: path_parts[1:-1] = [part[2:] + u" ◀" for part in path_parts[1:-1]]
        
        ## Draw the text and box
        drw = ImageDraw.Draw(text_im, 'RGBA')
        box_vertices = [(-10, -10), (w_rect, -10), (w_rect, h_rect-20), (w_rect-20, h_rect), (-10, h_rect)]
        transformed_pixels = lambda list_of_tuples: [(self.w - x if east else x, self.h - y if south else y) for x, y in list_of_tuples]
        drw.polygon(xy=transformed_pixels(box_vertices), fill=(120, 100, 50, 220), outline=(64, 50, 25, 255), width=3)
        drw.line(xy=transformed_pixels([(w_rect-1, h_rect-27), (w_rect-27, h_rect-1)]), fill=(64, 50, 25, 255), width=2) # Small extra line for fanciness
        text_y = 3
        for i, part in enumerate(path_parts):
            color = "#997744" if i == 0 else ("#C4C4C4" if (i + 1) < len(path_parts) else "#FFFFFF")
            text_x = pad if i != 0 else 3
            if i != 0: text_y += (h_line_max if i != 1 else fontsizes[0]) + interline
            if i + 1 == len(path_parts): text_y += interline # Move the filename further away because this looks better
            drw.text((self.w - text_x if east else text_x, self.h - text_y if south else text_y), text=part,
                     font=self._fonts[fontsizes[i]], fill=color, anchor=anchor)

        full_im.paste(text_im, (0, 0), text_im) # Repeat text_im in the 3rd argument to have correct transparency
        return full_im

    @staticmethod
    def least_cluttered_corner(im: Image.Image, dw: int, dh: int):
        if dw <= 0 or dh <= 0: return 3 # Default bottom left corner
        w, h = im.size
        im = im.convert('L')
        corners_cluttering = [0]*4
        for i, corner_coords in enumerate([(0, 0, dw, dh), (w - dw, 0, w, dh), (w - dw, h - dh, w, h), (0, h - dh, dw, h)]): # nw, ne, se, sw
            corner = np.array(im.crop(corner_coords)).astype(float)
            corners_cluttering[i] = np.average(np.absolute(ndi.laplace(corner/255.0))) # If error: use ndi.filters.laplace
        return np.argmin(corners_cluttering)


if __name__ == "__main__":
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__))) # Set current working directory

        ## Parse command-line arguments
        # Note: if the extension is changed to ".scr", then it is no longer possible to drag-and-drop a folder onto that file (contrary to a .exe).
        cmd_argument = None
        directory = None
        for item in sys.argv[1:]:
            if item.lower().startswith("/"): # Then it is command-line argument
                cmd_argument = item.lower()[:2] # Only first two characters (/p, /c, /s) because Windows adds extra info after that (e.g. sys.argv[1]=="/s:13658452")
            else:
                directory = [item]
        
        ## Follow API from https://learn.microsoft.com/sl-si/previous-versions/troubleshoot/windows/win32/screen-saver-command-line
        if cmd_argument == "/p": # Preview Screen Saver as child of window <HWND>.
            sys.exit() # Ignore /p, don't know how to show in HWND so just stop the program
        elif cmd_argument == "/c": # Show the Settings dialog box, modal to the foreground window.
            app = SettingsWindow()
            app.run()
        elif cmd_argument == "/s": # Run the Screen Saver in fullscreen mode.
            app = App(directories=directory, fullscreen=True)
            app.run()
        else: # Run the Screen Saver in windowed mode.
            app = App(directories=directory, fullscreen=False)
            app.run()
    except Exception:
        utils.show_error()

