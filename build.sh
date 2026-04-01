#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

python3 -m py_compile main.py
rm -rf build dist
mkdir -p build
cp main.py at-gui-launcher.sh at-gui.desktop README.md requirements.txt build/
echo "Prepared source package assets under build/"
