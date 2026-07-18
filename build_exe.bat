@echo off
REM Build script for Shadow of War Save Manager
REM Run this on Windows, with sow_save_manager_gui.py and icon.ico in the same folder

echo Installing PyInstaller (if not already installed)...
python -m pip install --upgrade pyinstaller

echo.
echo Building ShadowOfWarSaveManager.exe ...
python -m PyInstaller --onefile --windowed --name "ShadowOfWarSaveManager" --icon "icon.ico" --add-data "icon.ico;." sow_save_manager_gui.py

echo.
echo Done! Your exe is in the "dist" folder: dist\ShadowOfWarSaveManager.exe
pause
