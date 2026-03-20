#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -f dist/at-gui/at-gui ]] || [[ ! -d dist/at-gui/_internal ]]; then
  echo "dist/at-gui/ 不完整，先执行: ./build.sh（会生成 onedir）"
  exit 1
fi

if ! command -v fpm >/dev/null 2>&1; then
  echo "fpm not found; install it first."
  echo "apt-get install -y ruby ruby-dev build-essential && gem install --no-document fpm"
  exit 1
fi

VERSION="${VERSION:-0.1.1}"
rm -rf pkgroot
mkdir -p pkgroot/opt/at-gui pkgroot/usr/bin pkgroot/usr/share/applications

# 整套 PyInstaller 输出放到 /opt/at-gui（不用 cp -a：挂载卷上可能无法保留属主）
cp -r dist/at-gui/. pkgroot/opt/at-gui/
# 真实二进制改名，避免与 /usr/bin/at-gui 启动脚本冲突
mv pkgroot/opt/at-gui/at-gui pkgroot/opt/at-gui/at-gui.bin
chmod 755 pkgroot/opt/at-gui/at-gui.bin

# 启动脚本：写死 QT_PLUGIN_PATH，解决 xcb/wayland 插件找不到
install -m 755 at-gui-launcher.sh pkgroot/usr/bin/at-gui
install -m 644 at-gui.desktop pkgroot/usr/share/applications/at-gui.desktop

rm -f "at-gui-${VERSION}-1.x86_64.rpm" at-gui-*.rpm 2>/dev/null || true

fpm -s dir -t rpm \
  -n at-gui \
  -v "${VERSION}" \
  --architecture x86_64 \
  --description "GUI serial AT tool for 4G/5G modules" \
  --license "MIT" \
  -C pkgroot \
  opt/at-gui \
  usr/bin/at-gui \
  usr/share/applications/at-gui.desktop

echo "OK: at-gui-${VERSION}-1.x86_64.rpm"
echo "Install: sudo rpm -Uvh at-gui-${VERSION}-1.x86_64.rpm"
echo "Run: at-gui   (不要直接运行 /opt/at-gui/at-gui.bin，除非已 export QT_PLUGIN_PATH)"
