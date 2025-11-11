"""
One UI window per wayside. Mirrors the SW UI shape but stays minimal.
- Block selection updates the LCD (if present)
- Periodic refresh pulls state from controller
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional

from hw_display import HW_Display
from hw_wayside_controller import HW_Wayside_Controller

# optional LCD
try:
    from lcd_i2c import I2CLcd
    _LCD = I2CLcd(bus=1, addr=0x27)
except Exception:
    _LCD = None


class HW_Wayside_Controller_UI(ttk.Frame):
    def __init__(self, root: tk.Misc, controller: HW_Wayside_Controller, title: str = "Wayside"):
        super().__init__(root, padding=8)
        self.controller = controller
        self.root = root if isinstance(root, (tk.Tk, tk.Toplevel)) else self.winfo_toplevel()
        self.root.title(title)

        # toolbar
        bar = ttk.Frame(self)
        self.btn_load = ttk.Button(bar, text="Upload PLC", command=self._on_upload_plc)
        self.btn_load.pack(side="left")
        self.var_maint = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Maintenance", variable=self.var_maint,
                    command=self._on_toggle_maint).pack(side="left", padx=8)
        bar.pack(fill="x", pady=(0, 6))

        self._selected_block: Optional[str] = None
        self._last_lcd_tuple: Optional[tuple] = None  # <-- make sure this exists early

        # display area (create once)
        self.display = HW_Display(self)
        self.display.pack(fill="both", expand=True)

        # block list
        ids = self.controller.get_block_ids()
        self.display.set_blocks(ids)
        self.display.bind_on_select(self._on_select_block)

        # pick a first block immediately so the panel renders
        if ids:
            self._selected_block = ids[0]
            self.display.select_block(ids[0])

        # now it's safe to render once
        self._push_to_display() 

    # -------- public compatibility method (SW parity) --------
    def update_display(self, *, emergency: bool, speed_mph: float, authority_yards: int):
        
        self.controller.update_from_feed(
            speed_mph=speed_mph,
            authority_yards=authority_yards,
            emergency=emergency,
        )
        self._push_to_display()

    # -------- UI callbacks --------
    def _on_upload_plc(self):
        path = filedialog.askopenfilename(
            title="Select PLC file",
            filetypes=[("Python", "*.py"), ("All files", "*.*")]
        )
        if not path:
            return
        ok = self.controller.load_plc(path)
        if ok:
            self.controller.change_plc(True)
            messagebox.showinfo("PLC", f"Loaded: {path}")
        else:
            messagebox.showerror("PLC", "Failed to load PLC")

    def _on_toggle_maint(self):
        self.controller.maintenance_active = bool(self.var_maint.get())

    def _on_select_block(self, block_id: str):

        self._selected_block = block_id
        self.controller.on_selected_block(block_id)
        self._push_to_display()

    # -------- periodic refresh --------
    def _push_to_display(self):

        ids = self.controller.get_block_ids()

        if self._selected_block is None and ids:

            self._selected_block = ids[0]
            self.display.select_block(ids[0])

        if self._selected_block:

            state = self.controller.get_block_state(self._selected_block)
            self.display.update_details(state)
            self._update_lcd_tuple(state)

    # LCD updater with change detection
    def _update_lcd_tuple(self, state):
        block = state.get("block_id")
        spd = float(state.get("speed_mph", 0.0))
        auth = float(state.get("authority_yards", 0))
        tup = (block, int(spd), int(auth))
        if tup != self._last_lcd_tuple:
            self._last_lcd_tuple = tup
            self._update_lcd_for(block)

    def _update_lcd_for(self, block_id: str | None):

        try:
            from lcd_i2c_wayside_hw import I2CLcd  
            _lcd = I2CLcd(bus=1, addr=0x27)
        except Exception:
            _lcd = None

        if not block_id or not _lcd or not _lcd.present():
            return
        
        st = self.controller.get_block_state(block_id)
        _lcd.show_speed_auth(block_id, st.get("speed_mph", 0.0), st.get("authority_yards", 0))