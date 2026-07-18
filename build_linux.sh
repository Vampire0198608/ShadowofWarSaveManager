#!/usr/bin/env bash
# Build script for Shadow of War Save Manager on Linux (e.g. CachyOS).
# Run this from the same folder as sow_save_manager_gui.py, icon.ico, and icon.png.
#
# Usage:
#   chmod +x build_linux.sh
#   ./build_linux.sh
#
# This creates a local virtual environment (.build-venv) to install
# PyInstaller into, so it works even on Arch/CachyOS where pip blocks
# global installs by default (PEP 668).

set -e

echo "Checking for python-tkinter (needed for the GUI)..."
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo
    echo "tkinter isn't installed for your Python. On CachyOS/Arch, install it with:"
    echo "    sudo pacman -S tk"
    echo
    exit 1
fi

VENV_DIR=".build-venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating a local virtual environment in $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
fi

echo "Installing/upgrading PyInstaller into the virtual environment..."
"$VENV_DIR/bin/pip" install --upgrade pip pyinstaller

echo
echo "Building the ShadowOfWarSaveManager binary..."
"$VENV_DIR/bin/pyinstaller" --onefile --name "ShadowOfWarSaveManager" \
    --add-data "icon.png:." \
    --add-data "icon.ico:." \
    sow_save_manager_gui.py

echo
echo "Done! Your binary is at: dist/ShadowOfWarSaveManager"
echo "Run it with: ./dist/ShadowOfWarSaveManager"
