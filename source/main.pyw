"""
This program starts a screensaver with high-resolution images and frames from videos in the specified directory.
NOTE: If there are not enough high-resolution images as compared to low-res images in the directory, the program can slow down considerably.
"""

import cv2
import json
import numpy as np
import os
import psutil
import random
import scipy.ndimage as ndi
import time
import tkinter as tk
import warnings

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageTk, UnidentifiedImageError
warnings.simplefilter('ignore', Image.DecompressionBombWarning) # Ignore warning (i.e. dont warn for images between 90 and 179 MP)
from ctypes import windll
windll.shcore.SetProcessDpiAwareness(1)


class Options():
    defaultDict = {
        'directories': [r'E:\Space'],
        'excluded_directories': [],
        'only_high_res': True,
        'interval_seconds': 1
    }

    def __init__(self, file='options.json'):
        directory = os.path.expandvars(u"%APPDATA%\\Jonathan's Programma's\\SpaceScreensaver")
        self.file = os.path.join(directory, file)
        os.makedirs(directory, exist_ok=True)
        if not os.path.exists(self.file): self.reset()
        else: self.load()

    def save(self):
        with open(self.file, 'w') as optionsFile:
            json.dump(self.options, optionsFile)

    def load(self):
        with open(self.file, 'r') as optionsFile:
            self.options: dict = json.load(optionsFile)
        # Check if there are options missing in the optionsFile which do exist in the defaultDict, and add them to the file
        changed = False
        for option in Options.defaultDict:
            if option not in self.options:
                self[option] = Options.defaultDict[option]
                changed = True
        # Check if there are undesired options in the optionsFile which are not in the defaultDict, and remove them from the file
        unexpectedKeysInFile = [key for key, _ in self.options.items() if key not in Options.defaultDict] # Can not simply iterate over a size-changing dict, so use this key-list instead
        if len(unexpectedKeysInFile) > 0:
            changed = True
            for key in unexpectedKeysInFile:
                self.options.pop(key)
        if changed: self.save()

    def reset(self):
        self.options = Options.defaultDict
        self.save()

    def __getitem__(self, option):
         return self.options[option]

    def __setitem__(self, option, value):
        self.options[option] = value
        if not Options.similar_dicts(self.options, self.defaultDict): raise ValueError(f"Invalid value for '{option}'.")

    @staticmethod
    def similar_dicts(d1, d2): # From https://stackoverflow.com/a/24193949
        ''' Checks if two dictionaries have the same structure (same keys, and same keys with sub-dictionaries). '''
        if isinstance(d1, dict):
            if isinstance(d2, dict):
                return (d1.keys() == d2.keys() and all(Options.similar_dicts(d1[k], d2[k]) for k in d1.keys()))
            return False # d1 is a dict, but d2 isn't
        return not isinstance(d2, dict) # if d2 is a dict, then False, else True


class App():
    image_extensions = {'.png', '.jpg', '.jpeg', '.jfif', '.tiff', '.tif', '.bmp', '.webp'}
    video_extensions = {'.mp4', '.mkv', '.mov', '.wmv', '.avi', '.webm'}

    def __init__(self):
        self.options = Options()
        self.fonts = {i: ImageFont.truetype("DejaVuSans.ttf", size=i) for i in range(5, 25)}

        ## 1) Get all the possibly relevant image and video files
        self.available_paths = [] # Fill this array with all the paths to individual images. Fast with os.walk.
        for directory in self.options['directories']:
            if not os.path.exists(directory): continue
            for dirpath, dirnames, filenames in os.walk(directory, topdown=True):
                dirnames[:] = [d for d in dirnames if os.path.join(dirpath, d) not in self.options['excluded_directories']] # Don't visit excluded directories at all
                self.available_paths += [os.path.abspath(os.path.join(dirpath, file)) for file in filenames
                                    if os.path.splitext(file)[1].lower() in App.image_extensions | App.video_extensions]

        ## 2) Create the fullscreen window
        self.root = tk.Tk()
        self.w_screen, self.h_screen = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.overrideredirect(1)
        self.root.geometry("%dx%d+0+0" % (self.w_screen, self.h_screen))
        self.root.focus_set()
        self.root.config(cursor="none")
        exit_cmd = lambda e: (self.root.withdraw(), self.root.quit())
        for action in ["<Escape>", "<Button>", "<Motion>", "<Key>"]: self.root.bind(action, exit_cmd)
        self.canvas = tk.Canvas(self.root, width=self.w_screen, height=self.h_screen, bg='black', highlightthickness=0)
        self.canvas.pack()

    def run(self):
        self.root.after(0, self.mainIteration)
        self.root.mainloop()
    
    def mainIteration(self, repeat=True):
        t = time.time()
        im, filepath = self.get_random_image()
        im = self.annotate_image(im, filepath)
        self.root.image = ImageTk.PhotoImage(im) # Assign to self.root to prevent garbage collection
        self.root.imagesprite = self.canvas.create_image(self.w_screen//2, self.h_screen//2, image=self.root.image)
        wait_ms = int(1000*max(.5, self.options['interval_seconds'] - (time.time() - t)))
        if repeat: self.root.after(wait_ms, self.mainIteration)


    def get_random_image(self):
        random_index = random.randint(0,len(self.available_paths)-1)
        filepath = self.available_paths[random_index]
        is_image = os.path.splitext(filepath)[1] in App.image_extensions
        if is_image:
            try:
                im = Image.open(filepath)
            except (UnidentifiedImageError, Image.DecompressionBombError): # DecompressionBombError if image more than 179 MegaPixels
                self.available_paths.pop(random_index)
                return self.get_random_image()
        else:
            cap = cv2.VideoCapture(filepath)
            randomFrameNumber = random.randint(0, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
            cap.set(cv2.CAP_PROP_POS_FRAMES, randomFrameNumber) # set frame position
            success, image = cap.read()
            if not success:
                self.available_paths.pop(random_index)
                return self.get_random_image()
            im = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)) # Videos are in BGR, so convert to RGB
        w, h = im.size
        if self.options['only_high_res'] and (w < self.w_screen/2 and h < self.h_screen/2): # Then too small for the screen
            self.available_paths.pop(random_index)
            return self.get_random_image() # Just try another
        ratio = min(self.w_screen/w, self.h_screen/h)
        im = im.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
        return im, filepath

    def annotate_image(self, im: Image.Image, filepath: str, pad=10, interline=7):
        w, h = im.size
        full_im = Image.new('RGBA', (self.w_screen, self.h_screen), (0, 0, 0, 255))
        full_im.paste(im, (int((self.w_screen - w)/2), int((self.h_screen - h)/2)))

        ## Determine text size
        for directory in self.options['directories']:
            if directory in filepath:
                filepath = filepath.replace(directory, '')[1:]
                break
        path_parts = os.path.splitext(filepath)[0].split('\\')
        path_parts[:-1] = [u"▶ " + part for part in path_parts[:-1]]

        max_length_px, max_font_size = self.w_screen/3, 24
        lengths_20 = [self.fonts[20].getbbox(part)[2] for part in path_parts]
        fontsizes = [min(max_font_size, int(max_length_px/length*20)) for length in lengths_20]
        fontsizes[:-1] = [min(fontsizes[:-1]) for _ in fontsizes[:-1]] # Set all but the last directory to same font size

        ## Calculate size of text and surrounding box
        text_im = Image.new('RGBA', (self.w_screen, self.h_screen), color=(255, 255, 255, 0))
        h_line_max, w_max = 0, 0
        for i, part in enumerate(path_parts):
            bbox = self.fonts[fontsizes[i]].getbbox(part)
            h_line_max = max(h_line_max, bbox[3]-bbox[1])
            w_max = max(w_max, bbox[2])
        w_rect, h_rect = w_max + interline + 3*pad, (h_line_max + interline)*len(path_parts) + 2*pad

        ## Calculate which corner to put the textbox in
        if w/h < self.w_screen/self.h_screen:
            dh, dw = h_rect, (w - self.w_screen)/2 + w_rect
        else:
            dw, dh = w_rect, (h - self.h_screen)/2 + h_rect
        corner = self.least_cluttered_corner(im, dw, dh)
        anchor = ['lt', 'rt', 'rb', 'lb'][corner]
        east, south = anchor[0] == 'r', anchor[1] == 'b'
        if east: path_parts[:-1] = [part[2:] + u" ◀" for part in path_parts[:-1]]
        
        ## Draw the text and box
        drw = ImageDraw.Draw(text_im, 'RGBA')
        box_vertices = [(-10, -10), (w_rect, -10), (w_rect, h_rect-20), (w_rect-20, h_rect), (-10, h_rect)]
        transformed_pixels = lambda list_of_tuples: [(self.w_screen - x if east else x, self.h_screen - y if south else y) for x, y in list_of_tuples]
        drw.polygon(xy=transformed_pixels(box_vertices), fill=(180, 150, 75, 192), outline=(64, 50, 25, 255), width=3)
        drw.line(xy=transformed_pixels([(w_rect-1, h_rect-27), (w_rect-27, h_rect-1)]), fill=(64, 50, 25, 255), width=2) # Small extra line for fanciness
        for i, part in enumerate(path_parts):
            color = "#AAAAAA" if (i + 1) < len(path_parts) else "#FFFFFF"
            text_x = pad
            text_y = h_line_max*i + pad + i*interline
            if i + 1 == len(path_parts): text_y += interline # Move the filename further away because this looks better
            drw.text((self.w_screen - text_x if east else text_x, self.h_screen - text_y if south else text_y), text=part, font=self.fonts[fontsizes[i]], fill=color, anchor=anchor)
        full_im.paste(text_im, (0, 0), text_im) # Repeat text_im in the 3rd argument to have correct transparency
        return full_im
    
    def least_cluttered_corner(self, im: Image.Image, dw: int, dh: int):
        if dw <= 0 or dh <= 0: return 3 # Default bottom left corner
        w, h = im.size
        im = im.convert('L')
        corners_cluttering = [0]*4
        for i, corner_coords in enumerate([(0,0,dw,dh), (w-dw,0,w,dh), (w-dw,h-dh,w,h), (0,h-dh,dw,h)]): # nw, ne, se, sw
            corner = np.array(im.crop(corner_coords)).astype(float)
            corners_cluttering[i] = np.average(np.absolute(ndi.filters.laplace(corner / 255.0)))
        return np.argmin(corners_cluttering)


if __name__ == "__main__":
    app = App()
    app.run()
