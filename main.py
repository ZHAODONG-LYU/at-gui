#!/usr/bin/env python3
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

import serial
import serial.tools.list_ports


class ATGuiApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("AT Serial GUI")
        self.root.geometry("900x560")

        self.ser = None
        self.reader_thread = None
        self.reader_stop = threading.Event()
        self.rx_queue = queue.Queue()

        self.port_var = tk.StringVar()
        self.baud_var = tk.StringVar(value="115200")
        self.input_var = tk.StringVar()

        self._build_ui()
        self.refresh_ports()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.poll_messages)

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill="x")

        ttk.Label(top, text="Port").pack(side="left")

        self.port_box = ttk.Combobox(
            top,
            textvariable=self.port_var,
            state="readonly",
            width=28,
        )
        self.port_box.pack(side="left", padx=(8, 12))

        ttk.Label(top, text="Baud").pack(side="left")

        self.baud_box = ttk.Combobox(
            top,
            textvariable=self.baud_var,
            state="readonly",
            values=("115200", "9600", "57600", "230400", "460800", "921600"),
            width=12,
        )
        self.baud_box.pack(side="left", padx=(8, 12))

        self.refresh_btn = ttk.Button(top, text="Refresh", command=self.refresh_ports)
        self.refresh_btn.pack(side="left", padx=(0, 8))

        self.conn_btn = ttk.Button(top, text="Connect", command=self.toggle_connect)
        self.conn_btn.pack(side="left")

        middle = ttk.Frame(self.root, padding=(12, 0, 12, 0))
        middle.pack(fill="both", expand=True)

        self.log = scrolledtext.ScrolledText(
            middle,
            wrap="word",
            font=("DejaVu Sans Mono", 11),
        )
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

        bottom = ttk.Frame(self.root, padding=12)
        bottom.pack(fill="x")

        self.input_entry = ttk.Entry(bottom, textvariable=self.input_var)
        self.input_entry.pack(side="left", fill="x", expand=True)
        self.input_entry.bind("<Return>", self.send_cmd)

        self.send_btn = ttk.Button(bottom, text="Send", command=self.send_cmd)
        self.send_btn.pack(side="left", padx=(8, 0))
        self.send_btn.state(["disabled"])

    def append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def refresh_ports(self) -> None:
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_box["values"] = ports
        if ports:
            current = self.port_var.get()
            self.port_var.set(current if current in ports else ports[0])
        else:
            self.port_var.set("")

    def toggle_connect(self) -> None:
        if self.ser and self.ser.is_open:
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
            self.ser = serial.Serial(port, baudrate=baud, timeout=0.2)
        except Exception as exc:
            messagebox.showerror("Connect failed", str(exc))
            return

        self.reader_stop.clear()
        self.reader_thread = threading.Thread(target=self.reader_loop, daemon=True)
        self.reader_thread.start()

        self.conn_btn.configure(text="Disconnect")
        self.send_btn.state(["!disabled"])
        self.append_log(f"[INFO] Connected {port} @ {baud}")

    def disconnect_serial(self) -> None:
        self.reader_stop.set()

        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=0.5)
        self.reader_thread = None

        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
                self.append_log("[INFO] Disconnected")
        finally:
            self.ser = None
            self.conn_btn.configure(text="Connect")
            self.send_btn.state(["disabled"])

    def reader_loop(self) -> None:
        while not self.reader_stop.is_set():
            try:
                if not self.ser:
                    break
                line = self.ser.readline()
                if line:
                    self.rx_queue.put(("rx", line.decode(errors="replace").rstrip()))
            except Exception as exc:
                self.rx_queue.put(("err", str(exc)))
                break

    def poll_messages(self) -> None:
        while True:
            try:
                kind, payload = self.rx_queue.get_nowait()
            except queue.Empty:
                break

            if kind == "rx":
                self.append_log(f"RX: {payload}")
            else:
                self.append_log(f"[ERR] {payload}")
                self.disconnect_serial()
                break

        self.root.after(100, self.poll_messages)

    def send_cmd(self, _event=None) -> None:
        cmd = self.input_var.get().strip()
        if not cmd or not (self.ser and self.ser.is_open):
            return

        try:
            self.ser.write((cmd + "\r\n").encode())
            self.append_log(f"TX: {cmd}")
            self.input_var.set("")
        except Exception as exc:
            self.append_log(f"[ERR] Send failed: {exc}")

    def on_close(self) -> None:
        self.disconnect_serial()
        self.root.destroy()


def main() -> int:
    root = tk.Tk()
    ATGuiApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
