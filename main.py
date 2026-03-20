import os
import sys
from pathlib import Path


def _bootstrap_qt_plugins_for_pyinstaller() -> None:
    """PyInstaller 单文件：在 import Qt 前设置插件路径，否则只会在 /usr/bin/platforms 瞎找。"""
    # 不要依赖 sys.frozen，部分环境下不可靠；有 _MEIPASS 就是 PyInstaller 运行时
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        return
    root = Path(base)

    def try_set(plugins_dir: Path, platforms_dir: Path) -> bool:
        if not platforms_dir.is_dir():
            return False
        # 父目录是 Qt 的 plugins（含 platforms、imageformats 等）
        os.environ["QT_PLUGIN_PATH"] = str(plugins_dir)
        # 部分发行版/版本会认这个
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms_dir)
        return True

    # 1) 常见固定路径
    for rel in (
        Path("PySide6") / "Qt" / "plugins",
        Path("PySide6") / "Qt" / "lib" / "qt6" / "plugins",
    ):
        pdir = root / rel
        if try_set(pdir, pdir / "platforms"):
            return

    # 2) 在解压目录里搜 platforms/libqxcb.so（布局因 PyInstaller 版本可能变化）
    try:
        for lib in root.rglob("libqxcb.so"):
            if lib.parent.name == "platforms":
                if try_set(lib.parent.parent, lib.parent):
                    return
    except OSError:
        pass

    print(
        "AT-GUI: Qt plugins not found under _MEIPASS; GUI may fail.",
        file=sys.stderr,
    )


_bootstrap_qt_plugins_for_pyinstaller()

import serial
import serial.tools.list_ports
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QComboBox,
    QLabel,
    QMessageBox,
)


class ReaderThread(QThread):
    got = Signal(str)
    err = Signal(str)

    def __init__(self, ser):
        super().__init__()
        self.ser = ser
        self.running = True

    def run(self):
        while self.running:
            try:
                line = self.ser.readline()
                if line:
                    self.got.emit(line.decode(errors="replace"))
            except Exception as exc:
                self.err.emit(str(exc))
                break

    def stop(self):
        self.running = False


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AT Serial GUI")
        self.ser = None
        self.reader = None

        self.port_box = QComboBox()
        self.baud_box = QComboBox()
        self.baud_box.addItems(["115200", "9600", "57600", "230400", "460800", "921600"])
        self.refresh_btn = QPushButton("Refresh")
        self.conn_btn = QPushButton("Connect")
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Enter AT command, e.g. AT+CGSN")
        self.send_btn = QPushButton("Send")
        self.send_btn.setEnabled(False)

        top = QHBoxLayout()
        top.addWidget(QLabel("Port"))
        top.addWidget(self.port_box)
        top.addWidget(QLabel("Baud"))
        top.addWidget(self.baud_box)
        top.addWidget(self.refresh_btn)
        top.addWidget(self.conn_btn)

        bottom = QHBoxLayout()
        bottom.addWidget(self.input)
        bottom.addWidget(self.send_btn)

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(self.log)
        root.addLayout(bottom)

        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.conn_btn.clicked.connect(self.toggle_connect)
        self.send_btn.clicked.connect(self.send_cmd)
        self.refresh_ports()

    def refresh_ports(self):
        self.port_box.clear()
        for port in serial.tools.list_ports.comports():
            self.port_box.addItem(port.device)

    def toggle_connect(self):
        if self.ser and self.ser.is_open:
            self.disconnect_serial()
        else:
            self.connect_serial()

    def connect_serial(self):
        port = self.port_box.currentText()
        if not port:
            QMessageBox.warning(self, "Tips", "No serial port found")
            return
        baud = int(self.baud_box.currentText())
        try:
            self.ser = serial.Serial(port, baudrate=baud, timeout=0.2)
            self.reader = ReaderThread(self.ser)
            self.reader.got.connect(lambda text: self.log.append(f"RX: {text.rstrip()}"))
            self.reader.err.connect(lambda err: self.log.append(f"[ERR] {err}"))
            self.reader.start()
            self.conn_btn.setText("Disconnect")
            self.send_btn.setEnabled(True)
            self.log.append(f"[INFO] Connected {port} @ {baud}")
        except Exception as exc:
            QMessageBox.critical(self, "Connect failed", str(exc))

    def disconnect_serial(self):
        try:
            if self.reader:
                self.reader.stop()
                self.reader.wait(500)
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.log.append("[INFO] Disconnected")
        finally:
            self.conn_btn.setText("Connect")
            self.send_btn.setEnabled(False)

    def send_cmd(self):
        cmd = self.input.text().strip()
        if not cmd:
            return
        if not (self.ser and self.ser.is_open):
            return
        try:
            self.ser.write((cmd + "\r\n").encode())
            self.log.append(f"TX: {cmd}")
            self.input.clear()
        except Exception as exc:
            self.log.append(f"[ERR] Send failed: {exc}")

    def closeEvent(self, event):
        self.disconnect_serial()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(900, 560)
    win.show()
    sys.exit(app.exec())
