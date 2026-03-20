#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
rm -rf build dist at-gui.spec
# 使用 onedir：单文件(onefile)装在 /usr/bin 时 Qt 常错找 /usr/bin/platforms
# 配合 package-rpm 里的启动脚本设置 QT_PLUGIN_PATH
pyinstaller --noconfirm --onedir --name at-gui main.py \
  --collect-all PySide6
echo "Built: dist/at-gui/at-gui + dist/at-gui/_internal/"
