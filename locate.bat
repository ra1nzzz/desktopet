@echo off
set PATH=C:\Program Files\Python312;C:\Program Files\Python312\Scripts;%SystemRoot%\System32;%SystemRoot%
set PYTHONHOME=
set PYTHONPATH=
"C:\Program Files\Python312\python.exe" "%~dp0_locate.py" "%~1"
