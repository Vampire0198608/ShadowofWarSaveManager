#!/usr/bin/env bash
# Installs Shadow of War Save Manager for the current user (no root/sudo needed).
# Run this from the same folder as: dist/ShadowOfWarSaveManager, icon.png, shadowofwarsavemanager.desktop
#
# Usage:
#   chmod +x install.sh
#   ./install.sh

set -e

BIN_SRC="dist/ShadowOfWarSaveManager"
ICON_SRC="icon.png"
DESKTOP_SRC="shadowofwarsavemanager.desktop"

BIN_DEST_DIR="$HOME/.local/bin"
ICON_DEST_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
DESKTOP_DEST_DIR="$HOME/.local/share/applications"

if [ ! -f "$BIN_SRC" ]; then
    echo "Couldn't find $BIN_SRC — build it first with ./build_linux.sh"
    exit 1
fi

mkdir -p "$BIN_DEST_DIR" "$ICON_DEST_DIR" "$DESKTOP_DEST_DIR"

echo "Installing binary to $BIN_DEST_DIR ..."
cp "$BIN_SRC" "$BIN_DEST_DIR/shadowofwarsavemanager"
chmod +x "$BIN_DEST_DIR/shadowofwarsavemanager"

echo "Installing icon to $ICON_DEST_DIR ..."
cp "$ICON_SRC" "$ICON_DEST_DIR/shadowofwarsavemanager.png"

echo "Installing desktop menu entry to $DESKTOP_DEST_DIR ..."
cp "$DESKTOP_SRC" "$DESKTOP_DEST_DIR/shadowofwarsavemanager.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DEST_DIR" 2>/dev/null || true
fi

echo
echo "Installed! Make sure $BIN_DEST_DIR is on your PATH (it usually is by default)."
echo "You can now launch it by running 'shadowofwarsavemanager' from a terminal,"
echo "or find it in your application menu as 'Shadow of War Save Manager'"
echo "(you may need to log out/in, or restart your desktop panel, for the menu entry to appear)."
