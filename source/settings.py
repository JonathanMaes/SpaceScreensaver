import json
import os
import subprocess
import tkinter as tk
import tkinter.ttk as ttk
import tkfilebrowser

from tkinter import messagebox
from tkinter.font import Font

import utils


class Settings():
    defaultDict = {
        'directories': ['E:/Space'],
        'excluded_directories': ['E:/Space/Memes', 'E:/Space/Models'], # Dict where keys are elements of the 'directories' list, and values are lists of excluded subdirectories.
        'only_high_res': True,
        'interval_seconds': 15
    }

    def __init__(self, file='settings.json'):
        directory = utils.configdir
        self.file = os.path.join(directory, file)
        os.makedirs(directory, exist_ok=True)
        if not os.path.exists(self.file): self.reset()
        else: self.load()

    def save(self):
        with open(self.file, 'w') as optionsFile:
            json.dump(self.options, optionsFile)

    def load(self):
        with open(self.file, 'r') as optionsFile:
            data = optionsFile.read()
            self.options: dict = json.loads(data.replace('\\', '\\\\').replace('\\\\\\\\', '\\\\'))
        # Check if there are options missing in the optionsFile which do exist in the defaultDict, and add them to the file
        changed = False
        for option in Settings.defaultDict:
            if option not in self.options:
                self[option] = Settings.defaultDict[option]
                changed = True
        # Check if there are undesired options in the optionsFile which are not in the defaultDict, and remove them from the file
        unexpectedKeysInFile = [key for key, _ in self.options.items() if key not in Settings.defaultDict] # Can not simply iterate over a size-changing dict, so use this key-list instead
        if len(unexpectedKeysInFile) > 0:
            changed = True
            for key in unexpectedKeysInFile:
                self.options.pop(key)
        if changed: self.save()

    def reset(self):
        self.options = Settings.defaultDict
        self.save()

    def __getitem__(self, option):
         return self.options[option]

    def __setitem__(self, option, value):
        self.options[option] = value
        if not Settings.similar_dicts(self.options, self.defaultDict): raise ValueError(f"Invalid value for '{option}'.")

    @staticmethod
    def similar_dicts(d1, d2): # From https://stackoverflow.com/a/24193949
        ''' Checks if two dictionaries have the same structure (same keys, and same keys with sub-dictionaries). '''
        if isinstance(d1, dict):
            if isinstance(d2, dict):
                return (d1.keys() == d2.keys() and all(Settings.similar_dicts(d1[k], d2[k]) for k in d1.keys()))
            return False # d1 is a dict, but d2 isn't
        return not isinstance(d2, dict) # if d2 is a dict, then False, else True


class HoverButton(tk.Button):
    def __init__(self, master, **kw):
        tk.Button.__init__(self,master=master,**kw)
        self.defaultBackground = self.cget("background")
        self.defaultForeground = self.cget("foreground")
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        if not self.cget("state") == "disabled":
            self.config(background=self.cget('activebackground'))
            self.config(foreground=self.cget('activeforeground'))

    def on_leave(self, e):
        self.config(background=self.defaultBackground)
        self.config(foreground=self.defaultForeground)


class SettingsWindow():
    """ Press <Escape> once to go into manual mode. Press <Escape> again to resume the automatic slideshow.
        During manual mode, use the left and right arrow keys to move.
        During the automatic slideshow, press any key except <Escape> or move/click the mouse to exit.
        Press <o> at any time to open the file location in explorer (this closes the slideshow).
    """
    def __init__(self, options: Settings = None):
        self.settings = Settings() if options is None else options

        ## Create the fullscreen window
        self.root = tk.Tk()
        self.root.title(f"{utils.PROGRAMNAME_READABLE} - Settings")
        self.w_screen, self.h_screen = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"800x250+{max(0, (self.w_screen-800)//2)}+{max(0, (self.h_screen-250)//2 - 100)}") # Nice in the center, almost.
        self.root.focus_set()
        self.root.protocol("WM_DELETE_WINDOW", self.exit) # Pressing the red 'X' goes to self.exit
        self.root.report_callback_exception = utils.show_error

        # Make widgets sized to window
        self.root.grid_columnconfigure((0, 4), pad=10, weight=2, uniform="dircols")
        self.root.grid_columnconfigure(2, pad=10, minsize=120)
        self.root.grid_rowconfigure(0, pad=10, weight=1)

        # Directory list
        dir_frame = tk.Frame(self.root)
        dir_frame.grid(column=0, row=0, sticky='nsew')
        dir_frame.grid_columnconfigure((0, 1), weight=1)
        dir_frame.grid_rowconfigure(1, weight=1)

        dir_label = tk.Label(dir_frame, text="Directories", font=Font(size=14, underline=True), background='#222', foreground='white')
        dir_list_frame = tk.Frame(dir_frame)
        self.dir_list = tk.Listbox(dir_list_frame, selectmode=tk.EXTENDED, background='#222', foreground='white', borderwidth=0, highlightthickness=0)
        self.dir_scrollbary = tk.Scrollbar(dir_list_frame, orient=tk.VERTICAL)
        self.dir_scrollbarx = tk.Scrollbar(dir_list_frame, orient=tk.HORIZONTAL)
        add_dir_button = HoverButton(dir_frame, text="Add", command=self.add_directory, background="#AAF", activebackground="#CCF")
        remove_dir_button = HoverButton(dir_frame, text="Remove", command=self.remove_directory, background="#F44", activebackground="#F77")

        dir_label.grid(row=0, column=0, columnspan=2, sticky="ew")
        dir_list_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        add_dir_button.grid(row=2, column=0, sticky="ew")
        remove_dir_button.grid(row=2, column=1, sticky="ew")

        self.dir_scrollbarx.pack(side=tk.BOTTOM, fill=tk.BOTH)
        self.dir_list.pack(expand=True, side=tk.LEFT, fill=tk.BOTH)
        self.dir_scrollbary.pack(side=tk.RIGHT, fill=tk.BOTH)
        self.dir_list.config(yscrollcommand=self.dir_scrollbary.set, xscrollcommand=self.dir_scrollbarx.set)
        self.dir_scrollbary.config(command=self.dir_list.yview)
        self.dir_scrollbarx.config(command=self.dir_list.xview)

        # Excluded directories list
        excluded_frame = tk.Frame(self.root)
        excluded_frame.grid(column=4, row=0, sticky='nsew')
        excluded_frame.grid_columnconfigure((0,1), weight=1)
        excluded_frame.grid_rowconfigure(1, weight=1)

        excluded_label = tk.Label(excluded_frame, text="Excluded directories", font=Font(size=14, underline=True), background='#222', foreground='white')
        excluded_list_frame = tk.Frame(excluded_frame)
        self.excluded_list = tk.Listbox(excluded_list_frame, selectmode=tk.EXTENDED, background='#222', foreground='white', borderwidth=0, highlightthickness=0)
        self.excluded_scrollbary = tk.Scrollbar(excluded_list_frame, orient=tk.VERTICAL)
        self.excluded_scrollbarx = tk.Scrollbar(excluded_list_frame, orient=tk.HORIZONTAL)
        add_ex_button = HoverButton(excluded_frame, text="Add exclusion", command=self.add_excluded_directory, background="#AAF", activebackground="#CCF")
        remove_ex_button = HoverButton(excluded_frame, text="Remove exclusion", command=self.remove_excluded_directory, background="#F44", activebackground="#F77")

        excluded_label.grid(row=0, column=0, columnspan=2, sticky="ew")
        excluded_list_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        add_ex_button.grid(row=2, column=0, sticky="ew")
        remove_ex_button.grid(row=2, column=1, sticky="ew")

        self.excluded_scrollbarx.pack(side=tk.BOTTOM, fill=tk.BOTH)
        self.excluded_list.pack(expand=True, side=tk.LEFT, fill=tk.BOTH)
        self.excluded_scrollbary.pack(side=tk.RIGHT, fill=tk.BOTH)
        self.excluded_list.config(yscrollcommand=self.excluded_scrollbary.set, xscrollcommand=self.excluded_scrollbarx.set)
        self.excluded_scrollbary.config(command=self.excluded_list.yview)
        self.excluded_scrollbarx.config(command=self.excluded_list.xview)

        # Buttons to add and remove directories
        other_frame = tk.Frame(self.root)
        other_frame.grid(column=2, row=0, sticky='nsew')
        other_frame.grid_columnconfigure((0,1), weight=1)
        other_frame.grid_rowconfigure((1,4), weight=1)

        # Open file location button
        self.button_open_settings = HoverButton(other_frame, text="Open settings folder", command=self.open_settings_dir, background="#EEE", activebackground="#F4F4F4")
        self.button_open_settings.grid(row=0, column=0, columnspan=2, padx=10, pady=3, sticky="sew")

        # Checkbox for 'only_high_res'
        self.high_res_var = tk.BooleanVar(self.root)
        high_res_check = tk.Checkbutton(other_frame, text="Use only high\nresolution photos", variable=self.high_res_var)
        high_res_check.grid(row=2, column=0, columnspan=2, pady=10)

        # Entry for interval seconds using Spinbox
        interval_label = tk.Label(other_frame, text="Interval (sec.):", justify='right')
        interval_label.grid(row=3, column=0, sticky="e")
        self.interval_spinbox = tk.Spinbox(other_frame, from_=1, to=9999, width=4)
        self.interval_spinbox.grid(row=3, column=1, sticky="w")

        # Save button
        self.button_save = HoverButton(other_frame, text="Save settings", height=2, command=self.save_json, background="#00AA00", activebackground="#00FF00")
        self.button_save.grid(row=5, column=0, columnspan=2, padx=10, sticky="sew")

        # Separators between columns
        ttk.Separator(self.root, orient=tk.VERTICAL).grid(column=1, row=0, sticky='ns')
        ttk.Separator(self.root, orient=tk.VERTICAL).grid(column=3, row=0, sticky='ns')

        # Load default values
        self.load_values()
        self.save_json(flash_button=False) # For compatibility

    def _modify_scrollbars(self, event=None):
        pass # TODO: implement auto-hiding/showing scrollbars as in https://stackoverflow.com/a/75718185/
    
    def run(self):
        self.root.mainloop()
    
    def exit(self):
        if not self.is_unchanged():
            do_quit = messagebox.askokcancel("Quit", "Exit and discard unsaved changes?")
            if not do_quit: return
        (self.root.withdraw(), self.root.quit())

    def open_settings_dir(self):
        FILEBROWSER_PATH = os.path.join(os.getenv('WINDIR'), 'explorer.exe')
        path = self.settings.file
        subprocess.Popen([FILEBROWSER_PATH, '/select,', path], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)

    # Load the default values into the GUI
    def load_values(self):
        for directory in self.settings["directories"]:
            self.dir_list.insert(tk.END, os.path.abspath(directory).replace('\\', '/'))
        for directory in self.settings["excluded_directories"]:
            self.excluded_list.insert(tk.END, os.path.abspath(directory).replace('\\', '/'))
        self.high_res_var.set(self.settings["only_high_res"])
        self.interval_spinbox.delete(0, tk.END)
        self.interval_spinbox.insert(0, self.settings["interval_seconds"])

    def is_unchanged(self): # TODO: better way of checking this, now we have redundant code between this and save_json
        unchanged = True
        unchanged &= self.settings["directories"] == list(self.dir_list.get(0, tk.END))
        unchanged &= self.settings["excluded_directories"] == list(self.excluded_list.get(0, tk.END))
        unchanged &= self.settings["only_high_res"] == self.high_res_var.get()
        unchanged &= self.settings["interval_seconds"] == int(self.interval_spinbox.get())
        return unchanged

    # Function to update the JSON data
    def save_json(self, flash_button: bool = True):
        self.settings["directories"] = list(self.dir_list.get(0, tk.END))
        self.settings["excluded_directories"] = list(self.excluded_list.get(0, tk.END))
        self.settings["only_high_res"] = self.high_res_var.get()
        self.settings["interval_seconds"] = int(self.interval_spinbox.get())
        self.settings.save()

        if flash_button:
            self.button_save.config(text="Saved successfully.")
            self.root.after(1000, lambda: self.button_save.config(text="Save settings"))

    def add_directory(self):
        selected = self.dir_list.get(tk.ACTIVE)
        initialdir = os.path.dirname(selected) if selected else None
        directories = tkfilebrowser.askopendirnames(foldercreation=False, initialdir=initialdir)
        for directory in directories:
            self.dir_list.insert(tk.END, directory.replace('\\', '/'))

    def remove_directory(self):
        selection = sorted(self.dir_list.curselection(), reverse=True) # Sort descending to ensure popping elements does not affect subsequent indices
        for index in selection:
            self.dir_list.delete(index)

    def add_excluded_directory(self):
        selected = self.excluded_list.get(tk.ACTIVE)
        initialdir = os.path.dirname(selected) if selected else None
        directories = tkfilebrowser.askopendirnames(foldercreation=False, initialdir=initialdir)
        for directory in directories:
            self.excluded_list.insert(tk.END, directory.replace('\\', '/'))

    def remove_excluded_directory(self):
        selection = sorted(self.excluded_list.curselection(), reverse=True)
        for index in selection:
            self.excluded_list.delete(index)
