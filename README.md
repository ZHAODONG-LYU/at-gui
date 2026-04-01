# at-gui

A small Linux GUI for serial ports: connect, send AT commands, view responses. Intended for embedded cellular modules (AT over UART).

**Stack:** Python 3, Tkinter, pyserial. RPM packaging uses `fpm` (`package-rpm.sh`) and installs a lightweight Python app instead of bundling a full runtime.

## Install (Fedora, RPM)

After building the package locally:

```bash
sudo rpm -Uvh at-gui-0.1.1-1.noarch.rpm
```

If dependencies are missing on the target machine, install them first:

```bash
sudo dnf install -y python3 python3-pyserial python3-tkinter
```

Launch via the `at-gui` command or the desktop entry.

## Build from source

Ruby and `fpm` are required for the RPM step.

```bash
./build.sh
./package-rpm.sh
```

To run during development:

```bash
python3 main.py
```

## Serial permissions

Add your user to the `dialout` group, then log in again:

```bash
sudo usermod -aG dialout $USER
```

## Roadmap

Optional per-module default AT snippets may be added in a later release; the current release is a generic serial terminal only.
