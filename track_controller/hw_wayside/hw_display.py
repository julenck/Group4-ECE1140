"""
Very small Tkinter display helper for the HW UI.
This keeps existing public methods stable and adds two safe helpers:
- set_blocks(block_ids)
- bind_on_select(callback: Callable[[str], None])
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Dict, Any
import math


class HW_Display(ttk.Frame):
    def __init__(self, master: tk.Misc):
        super().__init__(master, padding=8)
        
        self._on_select: Callable[[str], None] | None = None
        # optional handlers saved by set_handlers compatibility wrapper
        self._on_upload = None
        self._on_set_switch = None
        self._on_toggle_maintenance = None

        # left: block picker
        left = ttk.Frame(self)
        ttk.Label(left, text="Blocks").pack(anchor="w")

        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True)

        self.block_list = tk.Listbox(list_frame, height=12, exportselection=False)
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.block_list.yview)
        self.block_list.configure(yscrollcommand=vsb.set)

        self.block_list.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        left.pack(side="left", fill="y", padx=(0, 8))

        # Switch control buttons live under the block picker (left column)
        # so they don't overlap the map. Keep them near the block list for
        # convenient manual operation.
        sw_btns = ttk.Frame(left)
        self._btn_switch_left = ttk.Button(sw_btns, text="Switch -> Straight (0)", command=lambda: self._emit_set_switch('0'))
        self._btn_switch_right = ttk.Button(sw_btns, text="Switch -> Diverge (1)", command=lambda: self._emit_set_switch('1'))
        self._btn_switch_left.pack(side="left", padx=(0,6), pady=(6,0))
        self._btn_switch_right.pack(side="left", pady=(6,0))
        sw_btns.pack(fill="x")

        # right: details
        right = ttk.Frame(self)
        # optional top map image area and detail vars
        self._map_label = None
        self._map_image_ref = None

        self.vars = {
            "block": tk.StringVar(value="-"),
            "speed": tk.StringVar(value="0.0"),
            "authority": tk.StringVar(value="0"),
            "occupied": tk.StringVar(value="False"),
            "switch": tk.StringVar(value="-"),
            "switch_map": tk.StringVar(value=""),
            "light": tk.StringVar(value="-"),
            "gate": tk.StringVar(value="-"),
            "status": tk.StringVar(value="OK"),
        }
        # map frame to the right of details (will hold track_map image if provided)
        map_frame = ttk.Frame(right)
        map_frame.pack(side="right", fill="y", padx=(6, 6), pady=(0, 8))
        self._map_label = ttk.Label(map_frame)
        self._map_label.pack()

        grid = ttk.Frame(right)
        def row(lbl, key):
            r = ttk.Frame(grid)
            ttk.Label(r, text=f"{lbl}: ", width=12).pack(side="left")
            ttk.Label(r, textvariable=self.vars[key], width=18).pack(side="left")
            r.pack(anchor="w")
        row("Block", "block")
        row("Speed (mph)", "speed")
        row("Authority (yd)", "authority")
        row("Occupied", "occupied")
        row("Switch", "switch")
        row("Switch Map", "switch_map")
        ttk.Separator(grid, orient="horizontal").pack(fill="x", pady=6)
        ttk.Label(grid, textvariable=self.vars["status"]).pack(anchor="w")
        grid.pack(side="left", anchor="nw", fill="both", expand=True)
        # no duplicate switch buttons here; controls live under the block list
        right.pack(side="left", fill="both", expand=True)

        # bindings
        self.block_list.bind("<<ListboxSelect>>", self._emit_select)

    # ---------------- public, stable APIs ----------------

    def set_blocks(self, block_ids: List[str]):
        self.block_list.delete(0, tk.END)
        for b in block_ids:
            self.block_list.insert(tk.END, str(b))

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
            max_w, max_h = 360, 400
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
        # state keys: block_id, speed_mph, authority_yards, occupied, switch, light, gate, status
        self.vars["block"].set(str(state.get("block_id", "-")))
        self.vars["speed"].set(f"{float(state.get('speed_mph', 0.0)):.1f}")
        self.vars["authority"].set(str(int(state.get("authority_yards", 0))))
        self.vars["occupied"].set(str(bool(state.get("occupied", False))))
        # no extra occupied list field — keep occupied flag only
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
        # switch now contains the effective display value (target block or state)
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
