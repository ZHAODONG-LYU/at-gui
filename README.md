# at-gui

A small Qt-based GUI for serial ports: connect, send AT commands, view responses. Intended for embedded cellular modules (AT over UART).

**Stack:** Python 3, PySide6, pyserial. Linux builds use PyInstaller (`build.sh`); RPM packaging uses `fpm` (`package-rpm.sh`).

## Install (Fedora, RPM)

After building the package locally:

```bash
sudo rpm -Uvh at-gui-0.1.1-1.x86_64.rpm
```

Launch via the `at-gui` command or the desktop entry. The wrapper under `/usr/bin/at-gui` sets `QT_PLUGIN_PATH` for the bundled Qt plugins; run that entry point rather than calling `/opt/at-gui/at-gui.bin` directly.

## Build from source

Ruby and `fpm` are required for the RPM step.

```bash
./build.sh
./package-rpm.sh
```

To run the unpacked binary during development:

```bash
export QT_PLUGIN_PATH="$PWD/dist/at-gui/_internal/PySide6/Qt/plugins"
./dist/at-gui/at-gui
```

## Serial permissions

Add your user to the `dialout` group, then log in again:

```bash
sudo usermod -aG dialout $USER
```

## Roadmap

Optional per-module default AT snippets may be added in a later release; the current release is a generic serial terminal only.
