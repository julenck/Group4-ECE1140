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

# ---- I2C LCD support (hardcoded to 0x27) ----
class LCD:
    def __init__(self):
        self._lcd = None
        try:
            from RPLCD.i2c import CharLCD
            import smbus2  # noqa: F401
            self._lcd = CharLCD(
                i2c_expander='PCF8574',
                address=0x27,  # hardcoded LCD address
                port=1,
                cols=16,
                rows=2,
                charmap='A02',
                auto_linebreaks=False
            )
        except Exception:
            self._lcd = None

    def display(self, speed_mph: int, authority_yd: int, emergency: bool):
        if not self._lcd:
            return
        try:
            self._lcd.clear()
            line1 = f"SPD:{speed_mph:>3} mph"
            line2 = f"AUTH:{authority_yd:>3} yd"
            if emergency:
                line2 = "E! " + line2
            line1 = (line1 + " " * 16)[:16]
            line2 = (line2 + " " * 16)[:16]
            self._lcd.write_string(line1)
            self._lcd.crlf()
            self._lcd.write_string(line2)
        except Exception:
            pass

    def cleanup(self):
        if not self._lcd:
            return
        try:
            self._lcd.close(clear=True)
        except Exception:
            pass


# --- Pin mapping ---
EMERGENCY_LED_PIN = 17
EMERGENCY_BUTTON_PIN = 18


class HWTrackControllerUI(tk.Tk):
    
    def __init__(self):
        super().__init__()
        self.title("Track Controller - HW UI")
        self.geometry("700x500")
        self.resizable(False, False)

        # State
        self.emergency_active = tk.BooleanVar(value=False)
        self.speed_kmh = tk.IntVar(value=0)
        self.authority_m = tk.IntVar(value=0)

        # Hardware (UNCHANGED)
        self._led = LED(EMERGENCY_LED_PIN)
        self._button = Button(EMERGENCY_BUTTON_PIN, pull_up=True, bounce_time=0.05) if GPIO_OK else Button()
        self._button.when_pressed = lambda: self.after(0, self.toggle_emergency)

        # I2C LCD (UNCHANGED)
        self._lcd = LCD()

        # --- Track block selection state (CREATE BEFORE _build_ui!) ---
        self.selected_block_number = tk.IntVar(value=-1)
        self.available_blocks = list(range(1, 51))  # adjustable: 1..50
        self.selected_block_number.trace_add('write', lambda *_: self.show_selected_block())

        # UI
        self._build_ui()

        # Bind state → UI
        self.emergency_active.trace_add("write", lambda *_: self._on_emergency_change())
        self.speed_kmh.trace_add("write", lambda *_: self._apply_speed_auth_to_labels())
        self.authority_m.trace_add("write", lambda *_: self._apply_speed_auth_to_labels())

        # Initial display
        self._apply_emergency()
        self._apply_speed_auth_to_labels()
        self._apply_assets_status()

    # -------- UI --------
    def _build_ui(self):
        pad = {"padx": 10, "pady": 8}
        self.em_label = ttk.Label(self, text="Emergency: OFF", foreground="green", font=("Segoe UI", 14, "bold"))
        self.em_label.grid(row=0, column=0, columnspan=2, sticky="w", **pad)

        disp = ttk.LabelFrame(self, text="Screen Display")
        disp.grid(row=1, column=0, columnspan=2, sticky="nsew", **pad)

        ttk.Label(disp, text="Commanded Speed (mph):", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.lbl_speed = ttk.Label(disp, text="0", font=("Consolas", 16, "bold"))
        self.lbl_speed.grid(row=0, column=1, sticky="e", padx=8, pady=6)

        ttk.Label(disp, text="Commanded Authority (yards):", font=("Segoe UI", 12)).grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.lbl_auth = ttk.Label(disp, text="0", font=("Consolas", 16, "bold"))
        self.lbl_auth.grid(row=1, column=1, sticky="e", padx=8, pady=6)

        # Assets status
        assets = ttk.LabelFrame(self, text="Field Assets")
        assets.grid(row=2, column=0, columnspan=2, sticky="ew", **pad)

        ttk.Label(assets, text="Signal Lights:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.lbl_signal_lights = ttk.Label(assets, text="NORMAL", foreground="green", font=("Segoe UI", 12, "bold"))
        self.lbl_signal_lights.grid(row=0, column=1, sticky="w", padx=8, pady=4)

        ttk.Label(assets, text="Gates:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.lbl_gates = ttk.Label(assets, text="NORMAL", foreground="green", font=("Segoe UI", 12, "bold"))
        self.lbl_gates.grid(row=1, column=1, sticky="w", padx=8, pady=4)

        # --- Track Blocks Section (modeled after SW UI) ---
        blocks = ttk.LabelFrame(self, text='Track Blocks')
        blocks.grid(row=3, column=0, columnspan=2, sticky='ew', **pad)

        ttk.Label(blocks, text='Select Block:').grid(row=0, column=0, sticky='w', padx=8, pady=6)
        self.block_combo = ttk.Combobox(blocks, values=self.available_blocks, state='readonly', width=10)
        self.block_combo.grid(row=0, column=1, sticky='w', padx=8, pady=6)
        self.block_combo.bind('<<ComboboxSelected>>', lambda e: self._on_block_chosen())

        self.block_info_label = ttk.Label(blocks, text='Selected Block Info: None', font=('Segoe UI', 11))
        self.block_info_label.grid(row=1, column=0, columnspan=2, sticky='w', padx=8, pady=6)

        # Optional quick-select list
        self.block_list = tk.Listbox(blocks, height=5, exportselection=False)
        for b in self.available_blocks:
            self.block_list.insert('end', f'Block {b}')
        self.block_list.grid(row=0, column=2, rowspan=2, sticky='nsew', padx=8, pady=6)
        self.block_list.bind('<<ListboxSelect>>', lambda e: self._on_block_list_select())

        blocks.grid_columnconfigure(3, weight=1)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

    # -------- Public API --------
    def toggle_emergency(self):
        self.emergency_active.set(not self.emergency_active.get())

    def set_speed(self, mph: int):
        try:
            self.speed_kmh.set(int(mph))
        except:
            pass

    def set_authority(self, yards: int):
        try:
            self.authority_m.set(int(yards))
        except:
            pass

    # -------- Apply state to hardware/UI --------
    def _on_emergency_change(self):
        val = self.emergency_active.get()
        self._apply_emergency()
        self._apply_assets_status()
        try:
            self._lcd.display(self.speed_kmh.get(), self.authority_m.get(), val)
        except Exception:
            pass

    def _apply_emergency(self):
        active = self.emergency_active.get()
        self._led.on() if active else self._led.off()
        self.em_label.config(
            text="Emergency: ACTIVE" if active else "Emergency: OFF",
            foreground="red" if active else "green"
        )

        # Update field assets to mirror SW UI behavior
        try:
            if active:
                self.lbl_signal_lights.config(text="RED", foreground="red")
                self.lbl_gates.config(text="CLOSED", foreground="red")
            else:
                self.lbl_signal_lights.config(text="GREEN", foreground="green")
                self.lbl_gates.config(text="OPEN", foreground="green")
        except Exception:
            pass

    def _apply_assets_status(self):
        active = self.emergency_active.get()
        if active:
            self.lbl_signal_lights.config(text="RED", foreground="red")
            self.lbl_gates.config(text="CLOSED", foreground="red")
        else:
            self.lbl_signal_lights.config(text="GREEN", foreground="green")
            self.lbl_gates.config(text="OPEN", foreground="green")

    def _apply_speed_auth_to_labels(self):
        self.lbl_speed.config(text=str(self.speed_kmh.get()))
        self.lbl_auth.config(text=str(self.authority_m.get()))
        try:
            self._lcd.display(self.speed_kmh.get(), self.authority_m.get(), self.emergency_active.get())
        except Exception:
            pass

    # --- Track block handlers ---
    def _on_block_chosen(self):
        try:
            b = int(self.block_combo.get())
            self.selected_block_number.set(b)
            # keep listbox in sync
            self.block_list.selection_clear(0, 'end')
            self.block_list.selection_set(b-1)
            self.block_list.see(b-1)
        except Exception:
            pass

    def _on_block_list_select(self):
        try:
            sel = self.block_list.curselection()
            if sel:
                idx = sel[0]
                b = self.available_blocks[idx]
                self.selected_block_number.set(b)
                # keep combobox in sync
                self.block_combo.set(str(b))
        except Exception:
            pass

    def show_selected_block(self):
        b = self.selected_block_number.get()
        if b != -1:
            self.block_info_label.config(text=f'Selected Block Info: Block {b}')
        else:
            self.block_info_label.config(text='Selected Block Info: None')

    def destroy(self):
        try:
            self._led.off()
            self._led.close()
        except Exception:
            pass
        try:
            self._lcd.cleanup()
        except Exception:
            pass
        super().destroy()


if __name__ == "__main__":
    app = HWTrackControllerUI()
    app.mainloop()
