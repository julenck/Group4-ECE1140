"""
Very small Tkinter display helper for the HW UI.
This keeps existing public methods stable and adds two safe helpers:
- set_blocks(block_ids)
- bind_on_select(callback: Callable[[str], None])
- set_active_trains(trains) for the train status table
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Dict, Any, Optional
import math
import time as time_module


class HW_Display(ttk.Frame):
    def __init__(self, master: tk.Misc):
        super().__init__(master, padding=8)
        
        self._on_select: Callable[[str], None] | None = None
        # optional handlers saved by set_handlers compatibility wrapper
        self._on_upload = None
        self._on_set_switch = None
        self._on_toggle_maintenance = None

        # Main content frame (map + details on right, block list on left)
        content_frame = ttk.Frame(self)
        content_frame.pack(fill="both", expand=True)

        # ========== LEFT SIDE: Block picker ==========
        left = ttk.Frame(content_frame)
        ttk.Label(left, text="Blocks", style="Header.TLabel").pack(anchor="w", pady=(0, 4))

        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True)

        # Dark themed listbox
        self.block_list = tk.Listbox(
            list_frame, 
            height=18, 
            width=10,
            exportselection=False,
            bg="#33363b",
            fg="#f2f3f4",
            selectbackground="#4e9af1",
            selectforeground="#ffffff",
            highlightthickness=0,
            relief="flat",
            font=("TkDefaultFont", 11)
        )
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.block_list.yview)
        self.block_list.configure(yscrollcommand=vsb.set)

        self.block_list.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        left.pack(side="left", fill="y", padx=(0, 8))

        # Switch control buttons live under the block picker (left column)
        sw_btns = ttk.Frame(left)
        self._btn_switch_left = ttk.Button(sw_btns, text="Switch -> Straight (0)", command=lambda: self._emit_set_switch('0'))
        self._btn_switch_right = ttk.Button(sw_btns, text="Switch -> Diverge (1)", command=lambda: self._emit_set_switch('1'))
        self._btn_switch_left.pack(side="left", padx=(0,6), pady=(6,0))
        self._btn_switch_right.pack(side="left", pady=(6,0))
        sw_btns.pack(fill="x")

        # ========== RIGHT SIDE: Map image + details ==========
        right = ttk.Frame(content_frame)
        
        # Frame to hold map image (center) and details panel (right of map)
        top_right = ttk.Frame(right)
        top_right.pack(fill="both", expand=True)

        # Map frame in center-right area
        map_frame = ttk.Frame(top_right)
        map_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self._map_label = ttk.Label(map_frame)
        self._map_label.pack()
        self._map_image_ref = None

        # Details panel on right side
        details_frame = ttk.Frame(top_right)
        details_frame.pack(side="right", fill="y", anchor="ne")

        # Section header for block data
        ttk.Label(details_frame, text="Selected Block Data", style="Header.TLabel").pack(anchor="w", pady=(0, 8))

        self.vars = {
            "block": tk.StringVar(value="-"),
            "time": tk.StringVar(value="00:00"),
            "speed": tk.StringVar(value="0.0"),
            "authority": tk.StringVar(value="0"),
            "occupied": tk.StringVar(value="False"),
            "switch": tk.StringVar(value="-"),
            "switch_map": tk.StringVar(value=""),
            "light": tk.StringVar(value="-"),
            "gate": tk.StringVar(value="-"),
            "status": tk.StringVar(value="OK"),
        }

        # Create detail rows
        grid = ttk.Frame(details_frame)
        def row(lbl, key, val_width=16):
            r = ttk.Frame(grid)
            ttk.Label(r, text=f"{lbl}:", width=14, anchor="w").pack(side="left")
            ttk.Label(r, textvariable=self.vars[key], width=val_width, anchor="w").pack(side="left")
            r.pack(anchor="w", pady=1)

        row("Block", "block")
        row("Time", "time")
        row("Speed (mph)", "speed", 10)
        row("Authority (yd)", "authority", 10)
        row("Occupied", "occupied")
        row("Switch", "switch")
        row("Switch Map", "switch_map", 24)  # Wider for switch map (e.g., "0->100, 1->85")

        grid.pack(anchor="nw", fill="both", expand=True)

        right.pack(side="left", fill="both", expand=True)

        # ========== BOTTOM: Active Trains Section ==========
        trains_section = ttk.Frame(self)
        trains_section.pack(fill="x", pady=(12, 0))

        # Header label
        ttk.Label(trains_section, text="Active Trains", style="Header.TLabel").pack(anchor="w")
        
        # Simulation time display (hidden by default, only shown when time is available)
        self._sim_time_var = tk.StringVar(value="")

        # Treeview for trains table
        columns = ("train", "block", "next_station", "cmd_spd", "auth", "eta")
        self.train_tree = ttk.Treeview(
            trains_section,
            columns=columns,
            show="headings",
            height=5,
            selectmode="browse"
        )

        # Define column headings and widths
        self.train_tree.heading("train", text="Train")
        self.train_tree.heading("block", text="Block")
        self.train_tree.heading("next_station", text="Next Station")
        self.train_tree.heading("cmd_spd", text="Cmd Spd")
        self.train_tree.heading("auth", text="Auth")
        self.train_tree.heading("eta", text="ETA")

        self.train_tree.column("train", width=120, anchor="w")
        self.train_tree.column("block", width=80, anchor="center")
        self.train_tree.column("next_station", width=160, anchor="w")
        self.train_tree.column("cmd_spd", width=80, anchor="center")
        self.train_tree.column("auth", width=100, anchor="center")
        self.train_tree.column("eta", width=100, anchor="center")

        # Add scrollbar for train tree
        train_scroll = ttk.Scrollbar(trains_section, orient="vertical", command=self.train_tree.yview)
        self.train_tree.configure(yscrollcommand=train_scroll.set)

        self.train_tree.pack(side="left", fill="x", expand=True)
        train_scroll.pack(side="right", fill="y")

        # Style the treeview for dark theme
        try:
            style = ttk.Style()
            style.configure("Treeview",
                background="#33363b",
                foreground="#f2f3f4",
                fieldbackground="#33363b",
                rowheight=25
            )
            style.configure("Treeview.Heading",
                background="#2a2d31",
                foreground="#f2f3f4",
                relief="flat"
            )
            style.map("Treeview",
                background=[("selected", "#4e9af1")],
                foreground=[("selected", "#ffffff")]
            )
        except Exception:
            pass

        # bindings
        self.block_list.bind("<<ListboxSelect>>", self._emit_select)

    # ---------------- public, stable APIs ----------------

    def set_blocks(self, block_ids: List[str]):
        """Populate the block list with the given block IDs."""
        self.block_list.delete(0, tk.END)
        for b in block_ids:
            self.block_list.insert(tk.END, str(b))

    def set_active_trains(self, trains: List[Dict[str, Any]]):
        """Update the Active Trains table with current train data.
        
        Each train dict should have: name, active, position, cmd_speed, cmd_auth, next_station
        """
        # Clear existing rows
        for item in self.train_tree.get_children():
            self.train_tree.delete(item)

        if not trains:
            return

        # Get current time for ETA calculation
        now = time_module.time()

        for train in trains:
            try:
                name = train.get('name', '-')
                active = train.get('active', False)
                
                # Only show active trains
                if not active:
                    continue

                position = train.get('position', '-')
                if position is None:
                    position = '-'
                
                cmd_speed = train.get('cmd_speed', 0)
                cmd_auth = train.get('cmd_auth', 0)
                next_station = train.get('next_station', '-')

                # Format speed and authority with 2 decimal places
                try:
                    speed_str = f"{float(cmd_speed):.2f}"
                except:
                    speed_str = str(cmd_speed)

                try:
                    auth_str = f"{float(cmd_auth):.2f}"
                except:
                    auth_str = str(cmd_auth)

                # Calculate ETA if we have speed and authority
                eta_str = "--:--:--"
                try:
                    if float(cmd_speed) > 0 and float(cmd_auth) > 0:
                        # yards / (mph * 1760 yards/mile / 3600 sec/hour) = seconds
                        yards_per_sec = float(cmd_speed) * 1760.0 / 3600.0
                        if yards_per_sec > 0:
                            seconds_remaining = float(cmd_auth) / yards_per_sec
                            eta_time = now + seconds_remaining
                            eta_str = time_module.strftime("%H:%M:%S", time_module.localtime(eta_time))
                except:
                    pass

                # Insert row
                self.train_tree.insert("", "end", values=(
                    name,
                    str(position),
                    str(next_station) if next_station else '-',
                    speed_str,
                    auth_str,
                    eta_str
                ))

            except Exception:
                continue

    def show_time(self, sim_time: str):
        """Update the simulation time display."""
        try:
            self._sim_time_var.set(str(sim_time) if sim_time else "--:--:--")
        except Exception:
            pass

    # ---- compatibility wrappers used by older UI code -----------------
    def set_handlers(self, on_upload_plc=None, on_select_block=None, on_set_switch=None, on_toggle_maintenance=None):
        """Compatibility wrapper: store callbacks and wire select handler."""
        self._on_upload = on_upload_plc
        self._on_set_switch = on_set_switch
        self._on_toggle_maintenance = on_toggle_maintenance
        if on_select_block:
            self.bind_on_select(on_select_block)

    def set_map_image_from_file(self, path: str) -> bool:
        """Load a PNG/GIF into the map area. Returns True on success."""
        try:
            if not path:
                return False
            # Prefer Pillow for robust resizing; fall back to Tk PhotoImage.
            max_w, max_h = 420, 480
            try:
                from PIL import Image, ImageTk
                pil = Image.open(path)
                pil.thumbnail((max_w, max_h))
                img = ImageTk.PhotoImage(pil)
                self._map_image_ref = img
                if self._map_label:
                    self._map_label.configure(image=img)
                return True
            except Exception:
                # Fallback: use Tk PhotoImage and subsample if needed
                try:
                    img = tk.PhotoImage(file=path)
                    w = img.width()
                    h = img.height()
                    sw = max(1, math.ceil(w / max_w))
                    sh = max(1, math.ceil(h / max_h))
                    factor = max(sw, sh)
                    if factor > 1:
                        img = img.subsample(factor, factor)
                    self._map_image_ref = img
                    if self._map_label:
                        self._map_label.configure(image=img)
                    return True
                except Exception:
                    return False
        except Exception:
            return False

    def set_switch_buttons_enabled(self, enabled: bool):
        st = "normal" if enabled else "disabled"
        try:
            self._btn_switch_left.configure(state=st)
            self._btn_switch_right.configure(state=st)
        except Exception:
            pass

    def _emit_set_switch(self, new_state: str):
        """Internal helper called when Left/Right button is pressed."""
        if not self._on_set_switch:
            return
        # Determine currently selected block
        sel = self.block_list.curselection()
        if not sel:
            return
        bid = self.block_list.get(sel[0])
        try:
            self._on_set_switch(bid, new_state)
        except Exception:
            pass

    def show_status(self, msg: str) -> None:
        # map to the internal status label used in update_details
        try:
            self.vars["status"].set(str(msg or ""))
        except Exception:
            pass

    def show_vital(self, emergency: bool, speed_mph: float, authority_yards: int, light_states=None, gate_states=None, switch_states=None, occupied_blocks=None, active_plc: str = "") -> None:
        """Compatibility method expected by HW UI: update blocks and status.

        light_states may be list of (bid, state) tuples; occupied_blocks a list.
        """
        try:
            # Do not change the block list here — block population is driven
            # by the controller/UI initialization. Keep this method limited to
            # updating the status area.
            # update status area
            status_msg = f"PLC: {active_plc}" if active_plc else ""
            if emergency:
                status_msg = "EMERGENCY" if not status_msg else status_msg + " — EMERGENCY"
            self.show_status(status_msg)
        except Exception:
            pass

    def show_safety(self, report: dict) -> None:
        if not report:
            self.show_status("")
            return
        safe = report.get("safe", True)
        reasons = ", ".join(report.get("reasons", []))
        self.show_status(("SAFE" if safe else "NOT SAFE") + (f" — {reasons}" if reasons else ""))

    def bind_on_select(self, cb: Callable[[str], None]):
        self._on_select = cb

    def select_block(self, block_id: str):
        # best-effort selection without raising
        try:
            idx = list(self.block_list.get(0, tk.END)).index(str(block_id))
            self.block_list.selection_clear(0, tk.END)
            self.block_list.selection_set(idx)
        except Exception:
            pass

    def update_details(self, state: Dict[str, Any]):
        """Update the details panel with block state info."""
        self.vars["block"].set(str(state.get("block_id", "-")))
        
        # Update time if provided
        if "time" in state:
            self.vars["time"].set(str(state.get("time", "00:00")))
        
        self.vars["speed"].set(f"{float(state.get('speed_mph', 0.0)):.1f}")
        self.vars["authority"].set(str(int(state.get("authority_yards", 0))))
        self.vars["occupied"].set(str(bool(state.get("occupied", False))))
        self.vars["switch"].set(str(state.get("switch", "-")))
        
        try:
            sm = state.get("switch_map")
            if sm:
                # format as 0->X,1->Y
                s = ", ".join(f"{k}-> {v}" for k, v in sorted(sm.items()))
            else:
                s = ""
        except Exception:
            s = ""
        self.vars["switch_map"].set(s)
        
        self.vars["light"].set(str(state.get("light", "-")))
        self.vars["gate"].set(str(state.get("gate", "-")))
        self.vars["status"].set(str(state.get("status", "OK")))

    # ---------------- internals ----------------

    def _emit_select(self, _evt=None):
        if not self._on_select:
            return
        sel = self.block_list.curselection()
        if not sel:
            return
        self._on_select(self.block_list.get(sel[0]))
