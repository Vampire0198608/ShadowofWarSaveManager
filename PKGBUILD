# Maintainer: You <you@example.com>
# PKGBUILD for Shadow of War Save Manager
#
# This packages the app as a native Arch/CachyOS package so it installs
# cleanly via pacman (with proper uninstall, file tracking, etc).
#
# Usage:
#   Put this PKGBUILD, sow_save_manager_gui.py, icon.png, icon.ico, and
#   shadowofwarsavemanager.desktop all in the same folder, then run:
#       makepkg -si
#   (-s installs missing build deps, -i installs the package after building)

pkgname=shadowofwarsavemanager
pkgver=1.0.0
pkgrel=1
pkgdesc="Backup, organize, and restore Shadow of War save files"
arch=('x86_64')
url="https://example.com"
license=('unknown')
depends=('tk' 'python')
makedepends=('python-pip' 'python-virtualenv')
source=("sow_save_manager_gui.py" "icon.png" "icon.ico" "shadowofwarsavemanager.desktop")
sha256sums=('SKIP' 'SKIP' 'SKIP' 'SKIP')

build() {
    cd "$srcdir"
    python -m venv build-venv
    build-venv/bin/pip install --upgrade pip pyinstaller
    build-venv/bin/pyinstaller --onefile --name "shadowofwarsavemanager" \
        --add-data "icon.png:." \
        --add-data "icon.ico:." \
        sow_save_manager_gui.py
}

package() {
    cd "$srcdir"
    install -Dm755 "dist/shadowofwarsavemanager" "$pkgdir/usr/bin/shadowofwarsavemanager"
    install -Dm644 "icon.png" "$pkgdir/usr/share/icons/hicolor/256x256/apps/shadowofwarsavemanager.png"
    install -Dm644 "shadowofwarsavemanager.desktop" "$pkgdir/usr/share/applications/shadowofwarsavemanager.desktop"
}
