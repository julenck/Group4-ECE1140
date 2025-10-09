import tkinter as tk
from tkinter import ttk

class TestUI(tk.Frame):
    """Mirror + controls with emergency toggle and S/A inputs (clamped & adjusted)."""
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller
        self.pack(fill="both", expand=True)
        self._build_ui()
        self._sync_all()

        # Keep in sync
        controller.emergency_active.trace_add("write", lambda *_: (self._sync_emergency(), self._sync_assets()))
        controller.speed_kmh.trace_add("write", lambda *_: self._sync_speed())
        controller.authority_m.trace_add("write", lambda *_: self._sync_authority())

    def _build_ui(self):
        pad = {"padx": 10, "pady": 8}

        self.status = ttk.Label(self, text="Emergency: OFF", foreground="green", font=("Segoe UI", 13, "bold"))
        self.status.grid(row=0, column=0, columnspan=6, sticky="w", **pad)

        out = ttk.LabelFrame(self, text="Outputs (Mirror of HW Screen)")
        out.grid(row=1, column=0, columnspan=6, sticky="nsew", **pad)

        ttk.Label(out, text="Speed (mph):").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.m_speed = ttk.Label(out, text="0", font=("Consolas", 14, "bold"))
        self.m_speed.grid(row=0, column=1, sticky="e", padx=8, pady=6)

        ttk.Label(out, text="Authority (yards):").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.m_auth = ttk.Label(out, text="0", font=("Consolas", 14, "bold"))
        self.m_auth.grid(row=1, column=1, sticky="e", padx=8, pady=6)

        # Assets mirror
        assets = ttk.LabelFrame(self, text="Field Assets")
        assets.grid(row=2, column=0, columnspan=6, sticky="ew", **pad)

        ttk.Label(assets, text="Signal Lights:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.m_signal_lights = ttk.Label(assets, text="NORMAL", foreground="green", font=("Segoe UI", 12, "bold"))
        self.m_signal_lights.grid(row=0, column=1, sticky="w", padx=8, pady=4)

        ttk.Label(assets, text="Gates:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.m_gates = ttk.Label(assets, text="NORMAL", foreground="green", font=("Segoe UI", 12, "bold"))
        self.m_gates.grid(row=1, column=1, sticky="w", padx=8, pady=4)

        ctl = ttk.LabelFrame(self, text="Controls")
        ctl.grid(row=3, column=0, columnspan=6, sticky="ew", **pad)

        ttk.Button(ctl, text="Toggle Emergency", command=self.controller.toggle_emergency).grid(row=0, column=0, padx=6, pady=6)

        ttk.Label(ctl, text="Speed (input mph):").grid(row=0, column=1, padx=6)
        self.e_speed = ttk.Entry(ctl, width=6)
        self.e_speed.insert(0, "0")
        self.e_speed.grid(row=0, column=2, padx=4)

        ttk.Label(ctl, text="Authority (input yards):").grid(row=0, column=3, padx=6)
        self.e_auth = ttk.Entry(ctl, width=8)
        self.e_auth.insert(0, "0")
        self.e_auth.grid(row=0, column=4, padx=4)

        ttk.Button(ctl, text="Apply S/A", command=self._apply_inputs).grid(row=0, column=5, padx=6)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=1)

    def _apply_inputs(self):
        try:
            val_s = max(0, int(self.e_speed.get()) - 5)   # clamp and subtract 5 mph
            self.controller.set_speed(val_s)
        except:
            pass
        try:
            val_a = max(0, int(self.e_auth.get()) - 50)   # clamp and subtract 50 yards
            self.controller.set_authority(val_a)
        except:
            pass

    # --- mirror helpers
    def _sync_all(self):
        self._sync_emergency()
        self._sync_speed()
        self._sync_authority()
        self._sync_assets()

    def _sync_emergency(self):
        a = self.controller.emergency_active.get()
        self.status.config(text="Emergency: ACTIVE" if a else "Emergency: OFF",
                           foreground="red" if a else "green")

    def _sync_speed(self):
        self.m_speed.config(text=str(self.controller.speed_kmh.get()))

    def _sync_authority(self):
        self.m_auth.config(text=str(self.controller.authority_m.get()))

    def _sync_assets(self):
        a = self.controller.emergency_active.get()
        if a:
            self.m_signal_lights.config(text="RED", foreground="red")
            self.m_gates.config(text="RED", foreground="red")
        else:
            self.m_signal_lights.config(text="NORMAL", foreground="green")
            self.m_gates.config(text="NORMAL", foreground="green")
