"""
One UI window per wayside. Mirrors the SW UI shape but stays minimal.
- Block selection updates the LCD (if present)
- Periodic refresh pulls state from controller
"""

from __future__ import annotations
from datetime import time
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

# Shared LCD instance used by both Wayside UIs so we can write line 0 for A
# and line 1 for B (minimal coordination).
_SHARED_LCD = None


class HW_Wayside_Controller_UI(ttk.Frame):
    def __init__(self, root: tk.Misc, controller: HW_Wayside_Controller, title: str = "Wayside"):
        super().__init__(root, padding=8)
        self.controller = controller
        self.root = root if isinstance(root, (tk.Tk, tk.Toplevel)) else self.winfo_toplevel()
        self.root.title(title)

        # --- minimal dark ttk theme (no deps) ---
        style = ttk.Style(self.root)

        try:
            style.theme_use("clam")
        except Exception:
            pass

        BG = "#2a2d31"
        PANEL = "#33363b"
        FG = "#f2f3f4"
        ACCENT = "#4e9af1"
        GOOD = "#2e7d32"   # green
        BAD = "#b71c1c"    # red

        style.configure(".", background=BG, foreground=FG, fieldbackground=PANEL, relief="flat")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("TButton", background=PANEL, foreground=FG, padding=6)
        style.configure("Header.TLabel", background=BG, foreground=FG, font=("TkDefaultFont", 12, "bold"))
        style.configure("TSeparator", background="#444")

        # indicator button styles
        style.configure("Good.TButton", background=GOOD, foreground="#ffffff", padding=6)
        style.map("Good.TButton", background=[("active", "#388e3c")])
        style.configure("Bad.TButton", background=BAD, foreground="#ffffff", padding=6)
        style.map("Bad.TButton", background=[("active", "#c62828")])

        # slightly larger default font for readability
        try:
            from tkinter import font as tkfont
            tkfont.nametofont("TkDefaultFont").configure(size=11)
        except Exception:
            pass

        self.root.configure(background=BG)

        # --- toolbar ---
        bar = ttk.Frame(self)

        # Emergency indicator (read-only; reflects system state)
        self._emergency_active = False
        self._emergency_block: Optional[str] = None
        self.btn_emergency = ttk.Button(
            bar, text="Normal", style="Good.TButton", state="disabled"
        )
        self.btn_emergency.pack(side="left", padx=(0, 8))

        # Upload PLC (gated by Maintenance)
        self.btn_load = ttk.Button(bar, text="Upload PLC", command=self._on_upload_plc, state="disabled")
        self.btn_load.pack(side="left", padx=(0, 8))

        self.var_maint = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Maintenance", variable=self.var_maint,
                        command=self._on_toggle_maint).pack(side="left", padx=8)

        bar.pack(fill="x", pady=(0, 6))

        self._selected_block: Optional[str] = None
        self._last_lcd_tuple: Optional[tuple] = None  # <-- make sure this exists early

        # --- display area (create once) ---
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
        # reflect emergency state in the indicator
        self._set_emergency(emergency)
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

        on = bool(self.var_maint.get())
        self.controller.maintenance_active = on
        # Enable/disable PLC upload button based on Maintenance
        try:
            self.btn_load.configure(state=("normal" if on else "disabled"))
        except Exception:
            pass

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

    # -------- emergency indicator helper --------
    def _set_emergency(self, is_emergency: bool, block_id: Optional[str] = None):
        self._emergency_active = bool(is_emergency)
        self._emergency_block = block_id if is_emergency else None

        if self._emergency_active:
            label = "EMERGENCY"
            if self._emergency_block:
                label += f" ({self._emergency_block})"
            try:
                self.btn_emergency.configure(text=label, style="Bad.TButton")
            except Exception:
                self.btn_emergency.configure(text=label)
        else:
            try:
                self.btn_emergency.configure(text="Normal", style="Good.TButton")
            except Exception:
                self.btn_emergency.configure(text="Normal")

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

        global _SHARED_LCD

        try:
            if _SHARED_LCD is None:

                from lcd_i2c_wayside_hw import I2CLcd
                _SHARED_LCD = I2CLcd(bus=1, addr=0x27)
            
                time.sleep(0.15)

                try:
                    if _SHARED_LCD.present():

                        _SHARED_LCD.clear()  
                        time.sleep(0.02)    
                    else:
                        return  
                except Exception:
                    return
        except Exception:
            _SHARED_LCD = None

        if not block_id or not _SHARED_LCD or not _SHARED_LCD.present():
            return

        st = self.controller.get_block_state(block_id)
        spd = int(float(st.get("speed_mph", 0)))
        auth = int(st.get("authority_yards", 0))

        try:
            wid = getattr(self.controller, "wayside_id", "").upper()
        except Exception:
            wid = ""

        if wid != "B":
            return

        def _sanitize(s: str) -> str:
            return "".join(ch if 32 <= ord(ch) <= 126 else " " for ch in s)

        blk = _sanitize(str(block_id))[:6] if block_id else "-"
        line0 = f"Blk:{blk:<6} Spd:{spd:3d}"[:16]
        line1 = f"Auth:{auth:5d} yd"[:16]

        try:
            _SHARED_LCD.write_line(0, line0)
            _SHARED_LCD.write_line(1, line1)
        except Exception:
        # --- ADDED: one-shot reinit on bus hiccup, then give up silently
            try:
                _SHARED_LCD.clear()
                time.sleep(0.02)
                _SHARED_LCD.write_line(0, line0)
                _SHARED_LCD.write_line(1, line1)
            except Exception:
                pass