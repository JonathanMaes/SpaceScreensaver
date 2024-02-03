@echo off
call conda activate base
python -m nuitka --disable-console --standalone --enable-plugin=tk-inter --output-dir="build" --include-data-files="source/DejaVuSans.ttf"="DejaVuSans.ttf" --include-data-dir="C:\ProgramData\Anaconda3\Lib\site-packages\tkfilebrowser\images"="tkfilebrowser\images" "source/main.pyw"
rename ".\build\main.dist\main.exe" "SpaceScreensaver.scr"
pause