@echo off
rem Onigiri Loader - release build
rem One-folder (onedir) build, no admin manifest (the app self-elevates at launch when needed).
cd /d "%~dp0"
python -m PyInstaller --noconfirm --onedir --noconsole --icon=onigiri.ico --name OnigiriLoader onigiri_loader.py
echo.
echo Done. Release folder: dist\OnigiriLoader\  (zip that folder for distribution)
pause
