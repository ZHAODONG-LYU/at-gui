#!/usr/bin/env python3
import argparse
import os
import queue
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, scrolledtext, ttk

import serial
import serial.tools.list_ports


BAUD_RATES = ("115200", "9600", "57600", "230400", "460800", "921600")


@dataclass
class SerialSession:
    ser: serial.Serial
    stop_event: threading.Event
    reader_thread: threading.Thread


class SerialManager:
    def __init__(self, on_rx, on_err) -> None:
        self.on_rx = on_rx
        self.on_err = on_err
        self.session: SerialSession | None = None

    def is_connected(self) -> bool:
        return bool(self.session and self.session.ser.is_open)

    def connect(self, port: str, baud: int) -> None:
        self.disconnect(silent=True)
        ser = serial.Serial(port, baudrate=baud, timeout=0.2)
        stop_event = threading.Event()
        reader_thread = threading.Thread(
            target=self._reader_loop,
            args=(ser, stop_event),
            daemon=True,
        )
        self.session = SerialSession(ser=ser, stop_event=stop_event, reader_thread=reader_thread)
        reader_thread.start()

    def disconnect(self, silent: bool = False) -> None:
        session = self.session
        if not session:
            return

        session.stop_event.set()
        try:
            if session.ser.is_open:
                session.ser.close()
        finally:
            session.reader_thread.join(timeout=0.5)
            self.session = None

        if not silent:
            self.on_err(None)

    def send(self, text: str) -> None:
        if not self.session or not self.session.ser.is_open:
            raise RuntimeError("Serial port is not connected")
        self.session.ser.write((text + "\r\n").encode())

    def _reader_loop(self, ser: serial.Serial, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            try:
                line = ser.readline()
                if line:
                    self.on_rx(line.decode(errors="replace").rstrip())
            except Exception as exc:
                if not stop_event.is_set():
                    self.on_err(str(exc))
                break


class GuiQueueBridge:
    def __init__(self) -> None:
        self.queue = queue.Queue()

    def on_rx(self, text: str) -> None:
        self.queue.put(("rx", text))

    def on_err(self, text: str | None) -> None:
        self.queue.put(("err", text))


class ATGuiApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("AT Serial GUI")
        self.root.geometry("980x640")
        self.root.minsize(820, 520)

        self.bridge = GuiQueueBridge()
        self.serial_manager = SerialManager(self.bridge.on_rx, self.bridge.on_err)

        self.port_var = tk.StringVar()
        self.baud_var = tk.StringVar(value="115200")
        self.input_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Status: Disconnected")

        self._init_style()
        self._build_ui()
        self.refresh_ports()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.poll_messages)

    def _init_style(self) -> None:
        self.colors = {
            "window_top": "#EEF2F7",
            "window_bottom": "#DDE6F2",
            "card": "#FFFFFF",
            "card_edge": "#D7DEE8",
            "text": "#162033",
            "muted": "#667085",
            "accent": "#0A84FF",
            "accent_dark": "#0066CC",
            "rx": "#22863A",
            "tx": "#0A84FF",
            "err": "#D93025",
            "info": "#667085",
            "surface": "#F8FAFC",
        }

        self.root.configure(bg=self.colors["window_top"])
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background=self.colors["window_top"])
        style.configure(
            "Card.TFrame",
            background=self.colors["card"],
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "Hero.TLabel",
            background=self.colors["window_top"],
            foreground=self.colors["text"],
            font=("SF Pro Display", 20, "bold"),
        )
        style.configure(
            "Muted.TLabel",
            background=self.colors["window_top"],
            foreground=self.colors["muted"],
            font=("SF Pro Text", 10),
        )
        style.configure(
            "CardTitle.TLabel",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("SF Pro Text", 10, "bold"),
        )
        style.configure(
            "CardBody.TLabel",
            background=self.colors["card"],
            foreground=self.colors["text"],
            font=("SF Pro Text", 10),
        )
        style.configure(
            "Status.TLabel",
            background=self.colors["window_top"],
            foreground=self.colors["muted"],
            font=("SF Pro Text", 10, "bold"),
        )
        style.configure(
            "Primary.TButton",
            background=self.colors["accent"],
            foreground="#FFFFFF",
            borderwidth=0,
            padding=(16, 8),
            font=("SF Pro Text", 10, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[
                ("active", self.colors["accent_dark"]),
                ("pressed", self.colors["accent_dark"]),
            ],
            foreground=[("disabled", "#F2F4F7")],
        )
        style.configure(
            "Soft.TButton",
            background=self.colors["surface"],
            foreground=self.colors["text"],
            borderwidth=0,
            padding=(12, 8),
            font=("SF Pro Text", 10),
        )
        style.map(
            "Soft.TButton",
            background=[("active", "#E9EEF5"), ("pressed", "#E9EEF5")],
        )
        style.configure("TEntry", padding=8)
        style.configure("TCombobox", padding=6)

    def _build_ui(self) -> None:
        outer = tk.Frame(self.root, bg=self.colors["window_top"])
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            outer,
            highlightthickness=0,
            bg=self.colors["window_top"],
        )
        canvas.pack(fill="both", expand=True)
        canvas.bind("<Configure>", self._draw_background)
        self.bg_canvas = canvas

        container = ttk.Frame(canvas, style="App.TFrame", padding=18)
        self.bg_window = canvas.create_window(0, 0, anchor="nw", window=container)
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(self.bg_window, width=event.width),
            add="+",
        )

        header = ttk.Frame(container, style="App.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="AT Serial GUI", style="Hero.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Minimal, clean and fast AT debugging with a desktop-first layout.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 14))

        toolbar = ttk.Frame(container, style="Card.TFrame", padding=14)
        toolbar.pack(fill="x")
        toolbar.columnconfigure(1, weight=1)

        ttk.Label(toolbar, text="Serial Port", style="CardBody.TLabel").grid(row=0, column=0, sticky="w")
        self.port_box = ttk.Combobox(
            toolbar,
            textvariable=self.port_var,
            state="readonly",
            width=26,
        )
        self.port_box.grid(row=0, column=1, sticky="w", padx=(10, 18))

        ttk.Label(toolbar, text="Baud", style="CardBody.TLabel").grid(row=0, column=2, sticky="w")
        self.baud_box = ttk.Combobox(
            toolbar,
            textvariable=self.baud_var,
            state="readonly",
            values=BAUD_RATES,
            width=12,
        )
        self.baud_box.grid(row=0, column=3, sticky="w", padx=(10, 18))

        self.refresh_btn = ttk.Button(toolbar, text="Refresh", command=self.refresh_ports, style="Soft.TButton")
        self.refresh_btn.grid(row=0, column=4, sticky="w", padx=(0, 8))

        self.conn_btn = ttk.Button(toolbar, text="Connect", command=self.toggle_connect, style="Primary.TButton")
        self.conn_btn.grid(row=0, column=5, sticky="w")

        center = ttk.Frame(container, style="App.TFrame")
        center.pack(fill="both", expand=True, pady=(14, 0))
        center.columnconfigure(0, weight=3)
        center.columnconfigure(1, weight=2)
        center.rowconfigure(0, weight=1)

        log_card = ttk.Frame(center, style="Card.TFrame", padding=14)
        log_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ttk.Label(log_card, text="Session Log", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 8))
        self.log = scrolledtext.ScrolledText(
            log_card,
            wrap="word",
            font=("SF Mono", 11),
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=12,
        )
        self.log.pack(fill="both", expand=True)
        self.log.configure(
            state="disabled",
            background="#FBFCFE",
            foreground=self.colors["text"],
            insertbackground=self.colors["text"],
        )
        self.log.tag_configure("rx", foreground=self.colors["rx"])
        self.log.tag_configure("tx", foreground=self.colors["tx"])
        self.log.tag_configure("err", foreground=self.colors["err"])
        self.log.tag_configure("info", foreground=self.colors["info"])

        side_card = ttk.Frame(center, style="Card.TFrame", padding=14)
        side_card.grid(row=0, column=1, sticky="nsew")

        ttk.Label(side_card, text="Quick Commands", style="CardTitle.TLabel").pack(anchor="w")
        quick_wrap = ttk.Frame(side_card, style="Card.TFrame")
        quick_wrap.pack(fill="x", pady=(10, 16))
        quick_commands = ("ATE1", "ATI", "AT+CPIN?")
        for index, command in enumerate(quick_commands):
            btn = ttk.Button(
                quick_wrap,
                text=command,
                command=lambda value=command: self.fill_command(value),
                style="Soft.TButton",
            )
            btn.grid(row=index // 2, column=index % 2, sticky="ew", padx=4, pady=4)
        quick_wrap.columnconfigure(0, weight=1)
        quick_wrap.columnconfigure(1, weight=1)

        ttk.Label(side_card, text="Tips", style="CardTitle.TLabel").pack(anchor="w", pady=(4, 6))
        tips = (
            "Use Refresh after replugging a USB modem.",
            "Press Enter to send the current AT command.",
            "Clear the log before a focused capture session.",
        )
        for tip in tips:
            ttk.Label(side_card, text=f"• {tip}", style="CardBody.TLabel").pack(anchor="w", pady=2)

        composer = ttk.Frame(container, style="Card.TFrame", padding=14)
        composer.pack(fill="x", pady=(14, 0))
        composer.columnconfigure(0, weight=1)
        ttk.Label(composer, text="Command", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.input_entry = ttk.Entry(composer, textvariable=self.input_var)
        self.input_entry.grid(row=1, column=0, sticky="ew")
        self.input_entry.bind("<Return>", self.send_cmd)

        actions = ttk.Frame(composer, style="Card.TFrame")
        actions.grid(row=1, column=1, sticky="e", padx=(10, 0))
        self.send_btn = ttk.Button(actions, text="Send", command=self.send_cmd, style="Primary.TButton")
        self.send_btn.pack(side="left")
        self.send_btn.state(["disabled"])
        self.clear_btn = ttk.Button(actions, text="Clear Log", command=self.clear_log, style="Soft.TButton")
        self.clear_btn.pack(side="left", padx=(8, 0))

        footer = ttk.Frame(container, style="App.TFrame")
        footer.pack(fill="x", pady=(12, 0))
        self.status_label = ttk.Label(footer, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.pack(anchor="w")
        self.set_status("Disconnected", self.colors["err"])
        self.input_entry.focus_set()

    def _draw_background(self, event) -> None:
        self.bg_canvas.delete("bg")
        width = max(event.width, 1)
        height = max(event.height, 1)
        steps = 24
        for index in range(steps):
            ratio = index / max(steps - 1, 1)
            color = self._blend(self.colors["window_top"], self.colors["window_bottom"], ratio)
            y0 = int(height * ratio)
            y1 = int(height * (index + 1) / steps)
            self.bg_canvas.create_rectangle(0, y0, width, y1, fill=color, outline="", tags="bg")

        self.bg_canvas.create_oval(
            width - 280,
            -80,
            width + 60,
            240,
            fill="#FFFFFF",
            outline="",
            stipple="gray25",
            tags="bg",
        )
        self.bg_canvas.create_oval(
            -120,
            height - 160,
            220,
            height + 120,
            fill="#C8D8F2",
            outline="",
            stipple="gray25",
            tags="bg",
        )
        self.bg_canvas.tag_lower("bg")

    @staticmethod
    def _blend(start: str, end: str, ratio: float) -> str:
        start_rgb = tuple(int(start[i : i + 2], 16) for i in (1, 3, 5))
        end_rgb = tuple(int(end[i : i + 2], 16) for i in (1, 3, 5))
        mixed = tuple(int(a + (b - a) * ratio) for a, b in zip(start_rgb, end_rgb))
        return "#{:02x}{:02x}{:02x}".format(*mixed)

    def append_log(self, text: str, tag: str = "info") -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", (tag,))
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def set_status(self, text: str, color: str) -> None:
        self.status_var.set(f"Status: {text}")
        self.status_label.configure(foreground=color)

    def refresh_ports(self) -> None:
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_box["values"] = ports
        if ports:
            current = self.port_var.get()
            self.port_var.set(current if current in ports else ports[0])
            self.append_log(f"[INFO] Found {len(ports)} serial port(s)", "info")
        else:
            self.port_var.set("")
            self.append_log("[INFO] No serial ports detected", "info")

    def fill_command(self, command: str) -> None:
        self.input_var.set(command)
        self.input_entry.focus_set()
        self.input_entry.icursor("end")

    def toggle_connect(self) -> None:
        if self.serial_manager.is_connected():
            self.disconnect_serial()
        else:
            self.connect_serial()

    def connect_serial(self) -> None:
        port = self.port_var.get().strip()
        if not port:
            messagebox.showwarning("Tips", "No serial port found")
            return

        baud = int(self.baud_var.get())
        try:
            self.serial_manager.connect(port, baud)
        except Exception as exc:
            messagebox.showerror("Connect failed", str(exc))
            return

        self.conn_btn.configure(text="Disconnect")
        self.send_btn.state(["!disabled"])
        self.append_log(f"[INFO] Connected {port} @ {baud}", "info")
        self.set_status(f"Connected to {port} @ {baud}", self.colors["rx"])

    def disconnect_serial(self) -> None:
        was_connected = self.serial_manager.is_connected()
        self.serial_manager.disconnect(silent=True)
        self.conn_btn.configure(text="Connect")
        self.send_btn.state(["disabled"])
        self.set_status("Disconnected", self.colors["err"])
        if was_connected:
            self.append_log("[INFO] Disconnected", "info")

    def poll_messages(self) -> None:
        while True:
            try:
                kind, payload = self.bridge.queue.get_nowait()
            except queue.Empty:
                break

            if kind == "rx":
                self.append_log(f"RX: {payload}", "rx")
            else:
                if payload:
                    self.append_log(f"[ERR] {payload}", "err")
                self.disconnect_serial()
                break

        self.root.after(100, self.poll_messages)

    def send_cmd(self, _event=None) -> None:
        cmd = self.input_var.get().strip()
        if not cmd or not self.serial_manager.is_connected():
            return

        try:
            self.serial_manager.send(cmd)
            self.append_log(f"TX: {cmd}", "tx")
            self.input_var.set("")
        except Exception as exc:
            self.append_log(f"[ERR] Send failed: {exc}", "err")

    def on_close(self) -> None:
        self.serial_manager.disconnect(silent=True)
        self.root.destroy()


class ATCliApp:
    def __init__(self, port: str | None, baud: int) -> None:
        self.selected_port = port
        self.baud = baud
        self.bridge = GuiQueueBridge()
        self.serial_manager = SerialManager(self.bridge.on_rx, self.bridge.on_err)
        self.print_queue = queue.Queue()

    def run(self) -> int:
        port = self.selected_port or self.pick_port()
        if not port:
            print("No serial port selected.")
            return 1

        print(f"Connecting to {port} @ {self.baud} ...")
        try:
            self.serial_manager = SerialManager(self.on_rx, self.on_err)
            self.serial_manager.connect(port, self.baud)
        except Exception as exc:
            print(f"Connect failed: {exc}", file=sys.stderr)
            return 1

        print("Connected. Type AT commands and press Enter. Type /quit to exit.")
        try:
            while True:
                self._flush_prints()
                try:
                    line = input("AT> ").strip()
                except EOFError:
                    line = "/quit"

                if line in {"/quit", "/exit"}:
                    break
                if line == "/ports":
                    self.show_ports()
                    continue
                if not line:
                    continue

                try:
                    self.serial_manager.send(line)
                    print(f"TX: {line}")
                except Exception as exc:
                    print(f"Send failed: {exc}", file=sys.stderr)
        finally:
            self.serial_manager.disconnect(silent=True)
            self._flush_prints()
            print("Disconnected.")

        return 0

    def on_rx(self, text: str) -> None:
        self.print_queue.put(("RX", text))

    def on_err(self, text: str | None) -> None:
        if text:
            self.print_queue.put(("ERR", text))

    def _flush_prints(self) -> None:
        while True:
            try:
                kind, text = self.print_queue.get_nowait()
            except queue.Empty:
                break
            print(f"{kind}: {text}")

    @staticmethod
    def show_ports() -> None:
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("No serial ports found.")
            return
        for index, port in enumerate(ports, start=1):
            description = port.description or "Unknown device"
            print(f"{index}. {port.device}  {description}")

    def pick_port(self) -> str | None:
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("No serial ports found.", file=sys.stderr)
            return None

        print("Available ports:")
        for index, port in enumerate(ports, start=1):
            description = port.description or "Unknown device"
            print(f"  {index}. {port.device}  {description}")

        while True:
            raw = input("Select port number: ").strip()
            if not raw:
                return ports[0].device
            if raw.isdigit() and 1 <= int(raw) <= len(ports):
                return ports[int(raw) - 1].device
            print("Invalid selection, try again.")


def should_use_cli(force_cli: bool) -> bool:
    if force_cli:
        return True
    if sys.platform.startswith("linux"):
        return not bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AT serial tool")
    parser.add_argument("--cli", action="store_true", help="Force terminal mode")
    parser.add_argument("--port", help="Serial port for terminal mode")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if should_use_cli(args.cli):
        return ATCliApp(args.port, args.baud).run()

    root = tk.Tk()
    ATGuiApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
