# Jonathan's Screensaver

A screensaver that shows random images (or stills from videos), with an annotation listing the parent directories where the image was found. This can be useful for additional context if a folder contains many photos in a tree-like structure.

Options (see `Appdata/Local/Jonathan's Programma's/SpaceScreensaver/settings.json`):

- List of directories to take the images from
- List of subdirectories not to take images from
- Time between subsequent images (in seconds)
- Whether to show only high-resolution images (i.e. more than half the screen size in pixels)

## Using RunSaver to run this as a screensaver

To use this script as a screensaver on windows, the easiest way is to download the <1MB [RunSaver](https://www.dcmembers.com/skrommel/download/runsave/) tool (which allows an arbitrary command to be run as a 'screensaver'), and set its command to point to the `run.bat` file (which itself runs this script in the appropriate working directory).

To set RunSaver, and then this screensaver, as your screensaver, do the following (no installation required, just extract the zip files and put the resulting directories somewhere):

1) Download [RunSaver](https://www.dcmembers.com/skrommel/download/runsave/) (this is a zip file containing `RunCheck.zip` and `RunSaver.zip`; we only need RunSaver). Download this repository as a zip file.

2) Extract the `RunSaver.zip` file to a folder where it can remain for eternity. Do the same for this repository's zip file.

3) In the RunSaver directory, right-click on `RunSaver.scr` and select 'install'. This adds it to the list of screensavers that you can choose from in the windows settings.

4) Go to the Windows screensaver settings in the control panel (shortcut: Win+R `control desk.cpl,,@screensaver`)

5) Choose RunSaver from the dropdown menu.

6) Press the 'Settings' button to the right of the dropdown menu. Set the command to point to the `run.bat` file by clicking 'Browse' and navigating to the `run.bat` file in the directory where you extracted the zip file of this repository.

That should be all, when your screensaver activates (as determined by the timeout in the control panel window) it should start the slideshow. However, you still need to set which folders to take the images from. For this,

7) open the `options.json` file and edit the settings to your preference.

## TODO

- Turn this into an executable (try `nuitka` instead of pyinstaller for once?)
  - If this does not work, at least add a venv or environment information to run this, and add a statement to `run.bat` to select the correct environment.
  - If it does work, I can just get rid of RunSaver and instead make the command-line arguments control whether the screensaver is shown or if the options are shown.
