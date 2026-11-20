@echo off
call conda activate spacescreensaver
if errorlevel 1 (
    echo Could not activate the "spacescreensaver" Conda environment.
    echo Create it with: conda env create -f environment.yml
    pause
    exit /b 1
)

for /f "usebackq delims=" %%I in (`python -c "import pathlib, tkfilebrowser; print(pathlib.Path(tkfilebrowser.__file__).parent / 'images')"`) do set "TKFILEBROWSER_IMAGES=%%I"
if not exist "%TKFILEBROWSER_IMAGES%" (
    echo Could not find tkfilebrowser's images directory: "%TKFILEBROWSER_IMAGES%"
    pause
    exit /b 1
)

python -m nuitka --disable-console --standalone --enable-plugin=tk-inter --output-dir="build" --include-data-files="source/DejaVuSans.ttf"="DejaVuSans.ttf" --include-data-dir="%TKFILEBROWSER_IMAGES%"="tkfilebrowser\images" "source/main.pyw"
rename ".\build\main.dist\main.exe" "SpaceScreensaver.scr"
pause