@echo off
call conda activate base
python -m nuitka --disable-console --standalone --enable-plugin=tk-inter --output-dir="build" --include-data-files="source/DejaVuSans.ttf"="DejaVuSans.ttf" "source/main.pyw"
pause