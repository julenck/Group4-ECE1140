# track_controller_HW_test_UI.py
import tkinter as tk
from tkinter import ttk

class TestUI(tk.Frame):
    """Simple mirror + controls. No observers, just read/write controller state."""
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller
        self.pack(fill="both", expand=True)
        self._build_ui()
        self._sync_all()

        # Keep in sync
        controller.emergency_active.trace_add("write", lambda *_: self._sync_emergency())
        controller.speed_kmh.trace_add("write", lambda *_: self._sync_speed())
        controller.authority_m.trace_add("write", lambda *_: self._sync_authority())

    def _build_ui(self):
        pad = {"padx": 10, "pady": 8}

        self.status = ttk.Label(self, text="Emergency: OFF", foreground="green", font=("Segoe UI", 13, "bold"))
        self.status.grid(row=0, column=0, columnspan=4, sticky="w", **pad)

        out = ttk.LabelFrame(self, text="Outputs (Mirror of HW Screen)")
        out.grid(row=1, column=0, columnspan=4, sticky="nsew", **pad)

        ttk.Label(out, text="Speed (km/h):").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.m_speed = ttk.Label(out, text="0", font=("Consolas", 14, "bold"))
        self.m_speed.grid(row=0, column=1, sticky="e", padx=8, pady=6)

        ttk.Label(out, text="Authority (m):").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.m_auth = ttk.Label(out, text="0", font=("Consolas", 14, "bold"))
        self.m_auth.grid(row=1, column=1, sticky="e", padx=8, pady=6)

        ctl = ttk.LabelFrame(self, text="Controls")
        ctl.grid(row=2, column=0, columnspan=4, sticky="ew", **pad)

        ttk.Button(ctl, text="Toggle Emergency", command=self.controller.toggle_emergency).grid(row=0, column=0, padx=6, pady=6)

        ttk.Label(ctl, text="Speed:").grid(row=0, column=1, padx=6)
        self.e_speed = ttk.Entry(ctl, width=6)
        self.e_speed.insert(0, "0")
        self.e_speed.grid(row=0, column=2, padx=4)

        ttk.Label(ctl, text="Authority:").grid(row=0, column=3, padx=6)
        self.e_auth = ttk.Entry(ctl, width=6)
        self.e_auth.insert(0, "0")
        self.e_auth.grid(row=0, column=4, padx=4)

        ttk.Button(ctl, text="Apply S/A", command=self._apply_inputs).grid(row=0, column=5, padx=6)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=1)

    def _apply_inputs(self):
        try: self.controller.set_speed(int(self.e_speed.get()))
        except: pass
        try: self.controller.set_authority(int(self.e_auth.get()))
        except: pass

    # --- mirror helpers
    def _sync_all(self):
        self._sync_emergency(); self._sync_speed(); self._sync_authority()

    def _sync_emergency(self):
        a = self.controller.emergency_active.get()
        self.status.config(text="Emergency: ACTIVE" if a else "Emergency: OFF",
                           foreground="red" if a else "green")

    def _sync_speed(self):
        self.m_speed.config(text=str(self.controller.speed_kmh.get()))

    def _sync_authority(self):
        self.m_auth.config(text=str(self.controller.authority_m.get()))
