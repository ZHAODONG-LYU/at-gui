#!/usr/bin/env bash
# RPM 安装后由 /usr/bin/at-gui 调用；直接使用系统 Python 运行精简版 GUI
set -euo pipefail
PREFIX="${AT_GUI_PREFIX:-/opt/at-gui}"
exec /usr/bin/python3 "${PREFIX}/main.py" "$@"
