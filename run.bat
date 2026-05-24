@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PATH=C:\Program Files\Python312;C:\Program Files\Python312\Scripts;%SystemRoot%\System32;%SystemRoot%"
set PYTHONHOME=
set PYTHONPATH=
start "" pythonw lingxi_droplet.py
exit
