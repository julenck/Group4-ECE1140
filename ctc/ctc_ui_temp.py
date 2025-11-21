import tkinter as tk
import json, os, threading, subprocess, sys
from datetime import datetime
from tkinter import filedialog, ttk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class CTCUI:
    def __init__(self):
        # File paths
        self.data_file = "ctc_data.json"

        # Load defaults
        self.default_data = {
            "Dispatcher": {
                "Trains": {
                    f"Train {i}": {
                        "Line": "",
                        "Suggested Speed": "",
                        "Authority": "",
                        "Station Destination": "",
                        "Arrival Time": "",
                        "Position": "",
                        "State": "",
                        "Current Station": ""
                    } for i in range(1, 6)
                }
            }
        }

        self._ensure_json()

        # Root window
        self.root = tk.Tk()
        self.root.title("CTC User Interface")
        self.root.geometry("1500x700")
        self.root.grid_rowconfigure(3, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Build UI
        self._build_datetime()
        self._build_buttons()
        self._build_frames()
        self._build_manual_ui()
        self._build_maintenance_ui()
        self._build_auto_ui()
        self._build_tables()

        # File watcher
        self._start_file_watcher()

        # Default view
        self.show_frame(self.auto_frame, self.auto_button)

        # Window close
        self.root.protocol("WM_DELETE_WINDOW", lambda: (self.observer.stop(), self.root.destroy()))

        # Start
        self.update_active_trains_table()
        self.root.mainloop()
        self.observer.join()

    # ---------------- JSON HANDLING -----------------
    def _ensure_json(self):
        if not os.path.exists(self.data_file) or os.stat(self.data_file).st_size == 0:
            with open(self.data_file, "w") as f:
                json.dump(self.default_data, f, indent=4)
        else:
            try:
                with open(self.data_file, "r") as f:
                    json.load(f)
            except json.JSONDecodeError:
                with open(self.data_file, "w") as f:
                    json.dump(self.default_data, f, indent=4)

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def save_data(self, data):
        with open(self.data_file, "w") as f:
            json.dump(data, f, indent=4)

    # ------------------- UI SECTIONS -------------------
    def _build_datetime(self):
        frame = tk.Frame(self.root)
        frame.grid(row=0, column=0, sticky="w", padx=10, pady=5)

        self.date_label = tk.Label(frame, font=('Times New Roman', 15, 'bold'))
        self.date_label.pack(side='left')
        self.time_label = tk.Label(frame, font=('Times New Roman', 15, 'bold'))
        self.time_label.pack(side='left')

        self.update_datetime()

    def update_datetime(self):
        now = datetime.now()
        self.date_label.config(text=now.date())
        self.time_label.config(text=f"      {now.strftime('%H:%M:%S')}")
        self.root.after(1000, self.update_datetime)

    # ---------------- BUTTONS ----------------
    def _build_buttons(self):
        self.button_frame = tk.Frame(self.root)
        self.button_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=5)
        self.button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.button_style = {
            "width": 60,
            "height": 1,
            "bg": "white",
            "relief": "flat",
            "bd": 0,
            "font": ("Times New Roman", 15, 'bold'),
            "activebackground": "#ddd"
        }

        self.auto_button = tk.Button(self.button_frame, text='Automatic', command=lambda: self.show_frame(self.auto_frame, self.auto_button), **self.button_style)
        self.manual_button = tk.Button(self.button_frame, text='Manual', command=lambda: self.show_frame(self.manual_frame, self.manual_button), **self.button_style)
        self.maint_button = tk.Button(self.button_frame, text='Maintenance', command=lambda: self.show_frame(self.maint_frame, self.maint_button), **self.button_style)

        self.auto_button.grid(row=0, column=0, sticky='ew', padx=5)
        self.manual_button.grid(row=0, column=1, sticky='ew', padx=5)
        self.maint_button.grid(row=0, column=2, sticky='ew', padx=5)

        self.active_button = None

    def show_frame(self, frame, clicked_button=None):
        frame.tkraise()

        for btn in [self.auto_button, self.manual_button, self.maint_button]:
            btn.config(bg="white", fg="black")

        if clicked_button:
            clicked_button.config(bg="lightgray", fg="black")
            self.active_button = clicked_button

    # ---------------- MAIN FRAMES ----------------
    def _build_frames(self):
        self.main_area = tk.Frame(self.root)
        self.main_area.grid(row=2, column=0, sticky='nsew', padx=10)
        self.main_area.grid_rowconfigure(0, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        self.manual_frame = tk.Frame(self.main_area, bg="lightgreen")
        self.auto_frame = tk.Frame(self.main_area, bg="lightblue")
        self.maint_frame = tk.Frame(self.main_area, bg="lightyellow")

        for f in (self.manual_frame, self.auto_frame, self.maint_frame):
            f.grid(row=0, column=0, sticky="nsew")

    # ---------------- MANUAL UI ----------------
    def _build_manual_ui(self):
        pass  # (You can paste your manual UI code here, replacing references with self.)

    # -------------- MAINTENANCE UI --------------
    def _build_maintenance_ui(self):
        pass

    # ---------------- AUTO UI ------------------
    def _build_auto_ui(self):
        pass

    # ---------------- TABLES -------------------
    def _build_tables(self):
        pass

    def update_active_trains_table(self):
        pass

    # ---------------- FILE WATCHER ----------------
    def _start_file_watcher(self):
        class Handler(FileSystemEventHandler):
            def __init__(self, outer):
                self.outer = outer

            def on_modified(self, event):
                if event.src_path.endswith("ctc_data.json"):
                    self.outer.root.after(100, self.outer.update_active_trains_table)

        self.event_handler = Handler(self)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path=os.path.dirname(self.data_file) or ".", recursive=False)
        threading.Thread(target=self.observer.start, daemon=True).start()


if __name__ == "__main__":
    CTCUI()
