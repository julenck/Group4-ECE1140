"""
One UI window per wayside. Mirrors the SW UI shape but stays minimal.
- Block selection updates the LCD (if present)
- Periodic refresh pulls state from controller
"""

from __future__ import annotations
from datetime import time
import time
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional

# CRITICAL: Add hw_wayside directory to path BEFORE importing local modules
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from hw_display import HW_Display
from hw_wayside_controller import HW_Wayside_Controller

# optional time controller integration
try:
    from time_controller import get_time_controller
except Exception:
    get_time_controller = None

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
        # Accent style for toggle
        try:
            style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff", padding=6)
            style.map("Accent.TButton", background=[("active", ACCENT)])
        except Exception:
            pass

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
        # Clear maintenance mode toggle button
        self.btn_maint = ttk.Button(bar, text="Maintenance Mode: OFF", command=self._on_toggle_maint_button, style="TButton", width=24)
        self.btn_maint.pack(side="left", padx=8)

        bar.pack(fill="x", pady=(0, 6))

        # Real-time clock on the far right of the toolbar
        try:
            self._now_var = tk.StringVar(value="--:--:--")
            lbl_now = ttk.Label(bar, textvariable=self._now_var)
            lbl_now.pack(side="right", padx=(8, 0))
        except Exception:
            self._now_var = None

        self._selected_block: Optional[str] = None
        self._last_lcd_tuple: Optional[tuple] = None  # <-- make sure this exists early

        # --- display area (create once) ---
        self.display = HW_Display(self)
        self.display.pack(fill="both", expand=True)

        # Try to load a track map image if present in this wayside folder
        try:
            base = os.path.dirname(__file__)
            img_path = os.path.join(base, 'track_map.png')
            if os.path.exists(img_path):
                self.display.set_map_image_from_file(img_path)
        except Exception:
            pass

        # wire handlers for manual operations
        try:
            self.display.set_handlers(on_set_switch=self._on_set_switch)
        except Exception:
            pass

        # block list: show only the controller's managed blocks. Including
        # external switch_map entries caused cross-wayside confusion (blocks
        # from Wayside A appearing in Wayside B). Keep UI limited to the
        # canonical `block_ids` supplied to this controller.
        try:
            ids = self.controller.get_block_ids()
        except Exception:
            try:
                ids = self.controller.get_ui_block_list()
            except Exception:
                ids = []
        # Ensure the display is populated with the controller's block ids
        try:
            self.display.set_blocks(ids)
        except Exception:
            pass
        self.display.bind_on_select(self._on_select_block)

        # (Removed) occupancy debug button: keep UI minimal and stable

        # pick a first block immediately so the panel renders
        if ids:
            self._selected_block = ids[0]
            self.display.select_block(ids[0])

        # now it's safe to render once
        self._push_to_display()

        # Start periodic refresh for real-time updates
        self._refresh_period_ms = 500  # 500ms = 2Hz refresh
        self._schedule_refresh()

    # -------- periodic refresh timer --------
    def _schedule_refresh(self):
        """Schedule the next periodic refresh."""
        try:
            self._push_to_display()
        except Exception:
            pass
        # Schedule next refresh
        try:
            self.after(self._refresh_period_ms, self._schedule_refresh)
        except Exception:
            pass

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
            messagebox.showinfo("PLC Upload", "PLC successfully loaded!")
        else:
            messagebox.showerror("PLC Upload", "Error: Could not load PLC file.")

    def _on_toggle_maint(self):

        on = bool(self.var_maint.get())
        self.controller.maintenance_active = on
        # Enable/disable PLC upload button based on Maintenance
        try:
            self.btn_load.configure(state=("normal" if on else "disabled"))
        except Exception:
            pass

    def _on_toggle_maint_button(self):
        # flip the boolean and delegate to existing handler
        try:
            self.var_maint.set(not bool(self.var_maint.get()))
        except Exception:
            self.var_maint.set(True)
        # update appearance first
        self._update_maint_button_appearance()
        # call the original handler to set controller state and upload-button state
        try:
            self._on_toggle_maint()
        except Exception:
            pass

    def _update_maint_button_appearance(self):
        try:
            on = bool(self.var_maint.get())
            if on:
                self.btn_maint.configure(text="Maintenance Mode: ON", style="Accent.TButton")
            else:
                self.btn_maint.configure(text="Maintenance Mode: OFF", style="TButton")
        except Exception:
            pass

    def _on_select_block(self, block_id: str):

        self._selected_block = block_id
        self.controller.on_selected_block(block_id)
        self._push_to_display()

    def _on_set_switch(self, block_id: str, new_state: str):
        """Called when the display requests a manual switch change.

        We call controller.request_switch_change and show a dialog if rejected.
        """
        try:
            ok, reason = self.controller.request_switch_change(block_id, new_state)
            if not ok:
                messagebox.showwarning("Switch Change Denied", f"{reason}")
            else:
                # Get the target block from switch_map for a friendly message
                target_block = None
                try:
                    sm = getattr(self.controller, 'switch_map', {}) or {}
                    entry = sm.get(str(block_id)) or {}
                    target_block = entry.get(str(new_state)) or entry.get(new_state)
                except Exception:
                    pass
                
                if new_state == '0' or str(new_state).upper().startswith('L'):
                    direction = "straight"
                else:
                    direction = "diverging"
                
                if target_block:
                    messagebox.showinfo("Switch Changed", f"Switch now {direction} to block {target_block}")
                else:
                    messagebox.showinfo("Switch Changed", f"Switch now set to {direction}")
                # refresh display
                self._push_to_display()
        except Exception as e:
            messagebox.showerror("Switch Error", f"Error changing switch: {e}")

    # -------- periodic refresh --------
    def _push_to_display(self):

        # Do NOT overwrite the display's block list every tick — leave block
        # population to initialization or explicit changes to avoid stomping
        # the user's selection while they interact with the UI.
        try:
            ids = self.controller.get_block_ids()
        except Exception:
            ids = []

        # If the controller's block list changed and the current selection
        # is missing, refresh the UI block list. This avoids stomping a
        # user's selection when it's still valid, but ensures the UI will
        # show new blocks (e.g., when switching PLC variants or partitions).
        try:
            current = list(self.display.block_list.get(0, tk.END))
            if set(str(x) for x in ids) != set(current):
                # Only refresh if the currently selected block is not in the
                # new set (to avoid stomping a user's selection), or if the
                # display is empty.
                sel = None
                try:
                    sel_idx = self.display.block_list.curselection()
                    if sel_idx:
                        sel = self.display.block_list.get(sel_idx[0])
                except Exception:
                    sel = None
                if not sel or str(sel) not in set(str(x) for x in ids):
                    self.display.set_blocks(ids)
                    # preserve selection if possible
                    if ids:
                        self._selected_block = ids[0]
                        self.display.select_block(ids[0])
        except Exception:
            # Fallback: set blocks unconditionally if anything goes wrong
            try:
                self.display.set_blocks(ids)
            except Exception:
                pass

        if self._selected_block is None and ids:
            self._selected_block = ids[0]
            self.display.select_block(ids[0])

        if self._selected_block:

            # Base state (includes speed/authority/status/emergency)
            state = self.controller.get_block_state(self._selected_block)
            # Merge in switch_map (and any small extras) from get_block_data for display
            try:
                bdata = self.controller.get_block_data(self._selected_block) or {}
                # Merge switch_map and resolved switch display value from get_block_data
                if 'switch_map' in bdata and bdata.get('switch_map') is not None:
                    state['switch_map'] = bdata.get('switch_map')
                if 'switch' in bdata and bdata.get('switch') is not None:
                    # Override the basic switch textual/state value with the
                    # controller-resolved display value (could be target block).
                    state['switch'] = bdata.get('switch')
            except Exception:
                pass
            self.display.update_details(state)
            # Enable switch buttons only if this block actually has a switch
            try:
                has_sw = False
                try:
                    has_sw = self.controller.has_switch(self._selected_block)
                except Exception:
                    has_sw = bool(state.get('switch_map'))
                self.display.set_switch_buttons_enabled(bool(has_sw))
            except Exception:
                pass

            # final update to the details already performed above
            try:
                train_block = self.controller.get_current_train_block()
            except Exception:
                train_block = None
            status_txt = state.get("status", "OK")
            if status_txt == "OK" and train_block:
                self.display.show_status(f"OK — Train @ {train_block}")

            # Keep existing emergency indicator behavior
            is_emerg = bool(state.get("emergency", getattr(self, "_emergency_active", False)))
            fault_block = state.get("fault_block") or (self._selected_block if is_emerg else None)
            self._set_emergency(is_emerg, fault_block)

            self._update_lcd_tuple(state)

            # Update Active Trains panel
            try:
                trains = []
                try:
                    trains = self.controller.get_active_trains()
                except Exception:
                    trains = []
                self.display.set_active_trains(trains)
                # lightweight redraw of the left block Treeview if present
                try:
                    bt = getattr(self.display, 'block_tree', None)
                    if bt is not None:
                        bt.update_idletasks()
                except Exception:
                    pass
            except Exception:
                pass

        # Update the top-right clock every push
        try:
            if getattr(self, '_now_var', None) is not None:
                try:
                    now = time.strftime("%H:%M:%S", time.localtime(time.time()))
                    self._now_var.set(now)
                except Exception:
                    pass
        except Exception:
            pass

        # Update simulation time if time controller available
        try:
            if get_time_controller:
                tc = get_time_controller()
                try:
                    sim = tc.get_sim_time()
                    self.display.show_time(sim)
                except Exception:
                    pass
        except Exception:
            pass

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
