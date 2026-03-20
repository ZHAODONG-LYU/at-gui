#!/usr/bin/env bash
# RPM 安装后由 /usr/bin/at-gui 调用；固定插件路径，避免去 /usr/bin/platforms 找
set -euo pipefail
PREFIX="${AT_GUI_PREFIX:-/opt/at-gui}"
export QT_PLUGIN_PATH="${PREFIX}/_internal/PySide6/Qt/plugins"
# 可选：部分环境需要
export QML2_IMPORT_PATH="${PREFIX}/_internal/PySide6/Qt/qml"
exec "${PREFIX}/at-gui.bin" "$@"
