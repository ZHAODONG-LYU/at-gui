#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v fpm >/dev/null 2>&1; then
  echo "fpm not found; install it first."
  echo "apt-get install -y ruby ruby-dev build-essential && gem install --no-document fpm"
  exit 1
fi

VERSION="${VERSION:-2.0}"
RPM_NAME="at-gui-${VERSION}-1.noarch.rpm"
rm -rf pkgroot
mkdir -p pkgroot/opt/at-gui pkgroot/usr/bin pkgroot/usr/share/applications

install -m 755 main.py pkgroot/opt/at-gui/main.py

install -m 755 at-gui-launcher.sh pkgroot/usr/bin/at-gui
install -m 644 at-gui.desktop pkgroot/usr/share/applications/at-gui.desktop

rm -f "${RPM_NAME}" at-gui-*.rpm 2>/dev/null || true

fpm -s dir -t rpm \
  -n at-gui \
  -v "${VERSION}" \
  --architecture noarch \
  --description "GUI serial AT tool for 4G/5G modules" \
  --license "MIT" \
  -d "python3" \
  -d "python3-pyserial" \
  -d "python3-tkinter" \
  -C pkgroot \
  opt/at-gui \
  usr/bin/at-gui \
  usr/share/applications/at-gui.desktop

echo "OK: ${RPM_NAME}"
echo "Install: sudo rpm -Uvh ${RPM_NAME}"
echo "Run: at-gui"
