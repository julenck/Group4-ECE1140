# track_controller_HW_UI.py
import tkinter as tk
from tkinter import ttk

# ---- GPIO (safe fallback if not on Raspberry Pi) ----
GPIO_OK = True
try:
    from gpiozero import LED, Button
except Exception:
    GPIO_OK = False
    class LED:
        def __init__(self, *a, **k): pass
        def on(self): pass
        def off(self): pass
        def close(self): pass
    class Button:
        def __init__(self, *a, **k): self.when_pressed = None

# --- Pin mapping (adjust to your wiring) ---
EMERGENCY_LED_PIN = 17
EMERGENCY_BUTTON_PIN = 18

class HWTrackControllerUI(tk.Tk):
    """
    Single source of truth for state:
      - emergency_active: toggled by hardware button OR UI
      - speed_kmh / authority_m: displayed on screen, settable by Test UI
    """
    def __init__(self):
        super().__init__()
        self.title("Track Controller - HW UI")
        self.geometry("520x300")
        self.resizable(False, False)

        # State
        self.emergency_active = tk.BooleanVar(value=False)
        self.speed_kmh = tk.IntVar(value=0)
        self.authority_m = tk.IntVar(value=0)

        # GPIO
        self._led = LED(EMERGENCY_LED_PIN)
        self._button = Button(EMERGENCY_BUTTON_PIN, pull_up=True, bounce_time=0.05) if GPIO_OK else Button()
        self._button.when_pressed = lambda: self.after(0, self.toggle_emergency)  # toggle on each press

        # UI
        self._build_ui()

        # Bind state -> UI
        self.emergency_active.trace_add("write", lambda *_: self._apply_emergency())
        self.speed_kmh.trace_add("write", lambda *_: self._apply_speed_auth())
        self.authority_m.trace_add("write", lambda *_: self._apply_speed_auth())

        # Initial paint
        self._apply_emergency()
        self._apply_speed_auth()

    # -------- UI --------
    def _build_ui(self):
        pad = {"padx": 10, "pady": 8}

        self.em_label = ttk.Label(self, text="Emergency: OFF", foreground="green", font=("Segoe UI", 14, "bold"))
        self.em_label.grid(row=0, column=0, columnspan=2, sticky="w", **pad)

        disp = ttk.LabelFrame(self, text="On-Train Display")
        disp.grid(row=1, column=0, columnspan=2, sticky="nsew", **pad)

        ttk.Label(disp, text="Speed (mph):", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.lbl_speed = ttk.Label(disp, text="0", font=("Consolas", 16, "bold"))
        self.lbl_speed.grid(row=0, column=1, sticky="e", padx=8, pady=6)

        ttk.Label(disp, text="Authority (yards):", font=("Segoe UI", 12)).grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.lbl_auth = ttk.Label(disp, text="0", font=("Consolas", 16, "bold"))
        self.lbl_auth.grid(row=1, column=1, sticky="e", padx=8, pady=6)

        # Simple local test controls
        ctrls = ttk.LabelFrame(self, text="Quick Test")
        ctrls.grid(row=2, column=0, columnspan=2, sticky="ew", **pad)
        ttk.Button(ctrls, text="Toggle Emergency", command=self.toggle_emergency).grid(row=0, column=0, padx=6, pady=6)

    # -------- Public API used by Test UI --------
    def toggle_emergency(self):
        self.emergency_active.set(not self.emergency_active.get())

    def set_speed(self, kmh: int):
        try: self.speed_kmh.set(int(kmh))
        except: pass

    def set_authority(self, meters: int):
        try: self.authority_m.set(int(meters))
        except: pass

    # -------- Apply state to hardware/UI --------
    def _apply_emergency(self):
        active = self.emergency_active.get()
        self._led.on() if active else self._led.off()
        self.em_label.config(text="Emergency: ACTIVE" if active else "Emergency: OFF",
                             foreground="red" if active else "green")

    def _apply_speed_auth(self):
        self.lbl_speed.config(text=str(self.speed_kmh.get()))
        self.lbl_auth.config(text=str(self.authority_m.get()))

    # Cleanup
    def destroy(self):
        try: self._led.off(); self._led.close()
        except: pass
        super().destroy()

if __name__ == "__main__":
    app = HWTrackControllerUI()
    app.mainloop()