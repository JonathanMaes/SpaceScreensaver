import platformdirs
import traceback

from pathlib import Path
from tkinter import messagebox


PROGRAMNAME_READABLE = "Jonathan's Screensaver"

def appdir(dir_func, **kwargs):
    """ <dir_func> should be one of the top-level functions of the <platformdirs> package (e.g. <platformdirs.user_cache_dir>). """
    dirpath = Path(dir_func("SpaceScreensaver", "Jonathan's Programma's", **kwargs))
    if not dirpath.exists(): dirpath.mkdir(parents=True)
    return dirpath

configdir = appdir(platformdirs.user_config_dir) # For larger files (like the TLE cache)


def show_error(*args):
    exc = '    '.join(traceback.format_exception(*args)) if args else traceback.format_exc()
    messagebox.showerror(f"Error in {PROGRAMNAME_READABLE}", exc)