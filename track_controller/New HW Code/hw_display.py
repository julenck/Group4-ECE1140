# hw_display.py
# Simple Tkinter-based display for the Wayside Controller HW module.
# Oliver Kettelson-Belinkie, 2025

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Tuple, Optional
from PIL import Image, ImageTk
import os

class HW_Display:

    is_ready: bool = False

    _on_upload_plc: Optional[Callable[[], None]] = None
    _on_select_block: Optional[Callable[[str], None]] = None
    _on_set_switch: Optional[Callable[[str, int], None]] = None
    _on_toggle_maintenance: Optional[Callable[[bool], None]] = None

    def __init__(self, root: tk.Tk, available_blocks=None):
        self.root = root
        self.root.title("Wayside Controller HW")
        self._build_layout()

        # preload block list if provided
        if available_blocks:

            self.set_blocks(list(available_blocks))

        self.is_ready = True

    # ---- public helpers ------------------------------------------------

    def set_handlers(
            
        self,
        on_upload_plc: Optional[Callable[[], None]] = None,
        on_select_block: Optional[Callable[[str], None]] = None,
        on_set_switch: Optional[Callable[[str, int], None]] = None,
        on_toggle_maintenance: Optional[Callable[[bool], None]] = None,
    ):
        self._on_upload_plc = on_upload_plc
        self._on_select_block = on_select_block
        self._on_set_switch = on_set_switch
        self._on_toggle_maintenance = on_toggle_maintenance

    # ---- layout ---------------------------------------------------------------

    def _build_layout(self):

        root = self.root
        for c in range(12):

            root.grid_columnconfigure(c, weight=1, uniform="col")
        for r in range(6):

            root.grid_rowconfigure(r, weight=1)

        # Top row: Map (cols 0-6), Vital (cols 7-11)
        self.map_card = self._card(root, "Map", row=0, col=0, colspan=7, rowspan=3)
        self.map_canvas = tk.Canvas(self.map_card["body"], bg="#E9ECEF", highlightthickness=0)
        self.map_canvas.pack(fill="both", expand=True)

        # redraw map when canvas is resized so the image stays centered/scaled
        self.map_canvas.bind("<Configure>", lambda _evt: self._redraw_map())

        self.vital_card = self._card(root, "Vital / Emergency Comms", row=0, col=7, colspan=5, rowspan=3)
        vb = self.vital_card["body"]

        # Emergency badge
        self.emergency_var = tk.StringVar(value="NORMAL")
        self.emergency_pill = ttk.Label(vb, textvariable=self.emergency_var, anchor="center")
        self.emergency_pill.pack(fill="x", pady=(2, 6))
        self._paint_emergency(False)

        # Speed / Authority
        stats = ttk.Frame(vb)
        stats.pack(fill="x", pady=(4, 10))
        ttk.Label(stats, text="Speed (mph):", width=14).grid(row=0, column=0, sticky="w")
        self.speed_var = tk.StringVar(value="0")
        ttk.Label(stats, textvariable=self.speed_var).grid(row=0, column=1, sticky="w")
        ttk.Label(stats, text="Authority (yd):", width=14).grid(row=1, column=0, sticky="w")
        self.auth_var = tk.StringVar(value="0")
        ttk.Label(stats, textvariable=self.auth_var).grid(row=1, column=1, sticky="w")

        # Active PLC
        plc_frame = ttk.Frame(vb)
        plc_frame.pack(fill="x", pady=(0, 2))
        ttk.Label(plc_frame, text="Active PLC:").grid(row=0, column=0, sticky="w")
        self.plc_name_var = tk.StringVar(value="(none)")
        ttk.Label(plc_frame, textvariable=self.plc_name_var).grid(row=0, column=1, sticky="w")

        # Safety message log (single-line)
        self.status_var = tk.StringVar(value="")
        self.status_label = ttk.Label(vb, textvariable=self.status_var, wraplength=360, foreground="#495057")
        self.status_label.pack(fill="x", pady=(8, 0))

        # Bottom row: four vertical panels
        self.select_card = self._card(root, "Select Block", row=3, col=0, colspan=3, rowspan=3)
        self.block_list = tk.Listbox(self.select_card["body"], exportselection=False, height=12)
        self.block_list.pack(fill="both", expand=True)
        self.block_list.bind("<<ListboxSelect>>", self._handle_select_block)

        self.info_card = self._card(root, "Block Info", row=3, col=3, colspan=3, rowspan=3)
        self.info_text = tk.Text(self.info_card["body"], height=12, wrap="word")
        self.info_text.configure(state="disabled")
        self.info_text.pack(fill="both", expand=True)

        self.upload_card = self._card(root, "Upload PLC", row=3, col=6, colspan=3, rowspan=3)
        ub = self.upload_card["body"]
        self.plc_status_var = tk.StringVar(value="No file loaded")
        ttk.Label(ub, textvariable=self.plc_status_var).pack(fill="x", pady=(4, 8))
        self.upload_btn = ttk.Button(ub, text="Choose & Load PLC", command=self._handle_upload_plc)
        self.upload_btn.pack(fill="x")

        self.maint_card = self._card(root, "Maintenance", row=3, col=9, colspan=3, rowspan=3)
        mb = self.maint_card["body"]
        self.maint_var = tk.BooleanVar(value=False)
        self.maint_toggle = ttk.Checkbutton(mb, text="Maintenance Mode", variable=self.maint_var,
                                            command=self._handle_toggle_maintenance)
        self.maint_toggle.pack(anchor="w", pady=(0, 8))

        ctl = ttk.Frame(mb)
        ctl.pack(fill="x", padx=2, pady=(0, 4))
        ttk.Label(ctl, text="Select switch:").grid(row=0, column=0, sticky="w")
        self.switch_choice = ttk.Combobox(ctl, state="disabled", width=12)
        self.switch_choice.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctl.grid_columnconfigure(1, weight=1)

        ttk.Label(ctl, text="Set state:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.state_choice = ttk.Combobox(ctl, values=["0", "1"], state="disabled", width=6)
        self.state_choice.current(0)
        self.state_choice.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=(8, 0))

        self.apply_switch_btn = ttk.Button(mb, text="Apply", state="disabled", command=self._handle_set_switch)
        self.apply_switch_btn.pack(anchor="e", pady=(8, 0))

    def _card(self, parent, title, row, col, colspan=1, rowspan=1):
        outer = ttk.Frame(parent, padding=(10, 8))
        outer.grid(row=row, column=col, columnspan=colspan, rowspan=rowspan, sticky="nsew")
        frame = ttk.LabelFrame(outer, text=title)
        frame.pack(fill="both", expand=True)
        body = ttk.Frame(frame, padding=6)
        body.pack(fill="both", expand=True)
        return {"frame": frame, "body": body}

    # ---- event handlers (UI side connects to controller UI) -------------------
    def _handle_upload_plc(self):

        if self._on_upload_plc:
            self._on_upload_plc()

    def _handle_select_block(self, _evt=None):

        sel = self.block_list.curselection()
        if not sel:
            return
        block_id = self.block_list.get(sel[0])
        if self._on_select_block:
            self._on_select_block(block_id)

    def _handle_set_switch(self):

        if not self._on_set_switch:
            return
        bid = self.switch_choice.get().strip()
        if not bid:
            return
        try:
            state = int(self.state_choice.get())
        except ValueError:
            state = 0
        self._on_set_switch(bid, state)

    def _handle_toggle_maintenance(self):

        active = bool(self.maint_var.get())
        self._set_maintenance_enabled(active)

        if self._on_toggle_maintenance:

            self._on_toggle_maintenance(active)

    def _set_maintenance_enabled(self, enabled: bool):
        
        new_state = "readonly" if enabled else "disabled"
        self.switch_choice.configure(state=new_state)
        self.state_choice.configure(state=new_state)
        self.apply_switch_btn.configure(state=("normal" if enabled else "disabled"))

    # ---- display API used by controller/ui -----------------------------------
    def show_vital(
        self,
        emergency: bool,
        speed_mph: float,
        authority_yards: int,
        light_states: List[Tuple[str, int]],
        gate_states: List[Tuple[str, int]],
        switch_states: List[Tuple[str, int]],
        occupied_blocks: List[str],
        active_plc: str = "",
    ) -> None:
        # update vitals
        self._paint_emergency(emergency)
        self.speed_var.set(f"{speed_mph:.0f}")
        self.auth_var.set(f"{authority_yards}")

        # plc name
        self.plc_name_var.set(active_plc if active_plc else "(none)")

        # left bottom: block list
        self._refresh_block_list(sorted(set([bid for bid, _ in light_states] + occupied_blocks)))

        # info panel (selected block details)
        self._refresh_block_info(light_states, gate_states, switch_states, occupied_blocks)

        # maintenance choices follow available switches
        self._refresh_switch_chooser([bid for bid, _ in switch_states])

    def show_status(self, msg: str) -> None:
        self.status_var.set(msg or "")

    def show_safety_report(self, report: Dict) -> None:
        # compact one-liner
        if not report:
            self.status_var.set("")
            return
        safe = report.get("safe", True)
        reasons = ", ".join(report.get("reasons", []))
        self.status_var.set(("SAFE" if safe else "NOT SAFE") + (f" — {reasons}" if reasons else ""))

    def clear(self) -> None:
        self.status_var.set("")
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.configure(state="disabled")

    def shutdown(self) -> None:
        try:
            self.root.destroy()
        except Exception:
            pass

    # ---- helpers --------------------------------------------------------------
    def _paint_emergency(self, is_emerg: bool):
        self.emergency_var.set("EMERGENCY" if is_emerg else "NORMAL")
        # simple pill effect using style changes
        style = ttk.Style()
        style.configure("Red.TLabel", foreground="#fff", background="#dc3545", padding=(6, 3))
        style.configure("Green.TLabel", foreground="#fff", background="#198754", padding=(6, 3))
        self.emergency_pill.configure(style="Red.TLabel" if is_emerg else "Green.TLabel")

    def _refresh_block_list(self, blocks: List[str]):
        old = set(self.block_list.get(0, "end"))
        new = list(blocks)
        if old == set(new):
            return
        self.block_list.delete(0, "end")
        for b in new:
            self.block_list.insert("end", b)

    def _refresh_block_info(
        self,
        light_states: List[Tuple[str, int]],
        gate_states: List[Tuple[str, int]],
        switch_states: List[Tuple[str, int]],
        occupied_blocks: List[str],
    ):
        sel = self.block_list.curselection()
        block = self.block_list.get(sel[0]) if sel else None

        def lookup(lst, key, default="—"):
            d = dict(lst)
            return d.get(key, default)

        txt = []
        if block:
            txt.append(f"Block: {block}")
            txt.append(f"Occupied: {'YES' if block in occupied_blocks else 'NO'}")
            txt.append(f"Signal (0=G,1=Y,2=R): {lookup(light_states, block)}")
            txt.append(f"Switch state: {lookup(switch_states, block)}")
            txt.append(f"Gate state: {lookup(gate_states, block)}")
        else:
            txt.append("Select a block to view details...")

        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("end", "\n".join(txt))
        self.info_text.configure(state="disabled")

    def _refresh_switch_chooser(self, switch_ids: List[str]):
        # keep selection if still valid
        current = self.switch_choice.get()
        if current and current in switch_ids:
            # update list if changed
            if set(self.switch_choice["values"]) != set(switch_ids):
                self.switch_choice.configure(values=switch_ids)
            return
        self.switch_choice.configure(values=switch_ids)
        if switch_ids:
            self.switch_choice.set(switch_ids[0])

    def set_map_image(self, image_path: str) -> None:

        try:
            # resolve relative to this file if a bare filename is given

            if not os.path.isabs(image_path):

                image_path = os.path.join(os.path.dirname(__file__), image_path)

            self._map_img_raw = Image.open(image_path).convert("RGBA")
            # ensure geometry is calculated (canvas size may be 1x1 before mainloop)
            try:
                self.root.update_idletasks()
            except Exception:
                pass
            self._redraw_map()

        except Exception as e:
            self.show_status(f"Map load failed: {e}")

    def _redraw_map(self) -> None:
        """Scale and draw the map image into the canvas."""
        raw = getattr(self, "_map_img_raw", None)
        if not raw:
            # gray background already shows; nothing to draw
            return
        w = max(self.map_canvas.winfo_width(), 1)
        h = max(self.map_canvas.winfo_height(), 1)
        iw, ih = raw.size
        # keep aspect ratio; letterbox if needed
        scale = min(w / iw, h / ih)
        nw, nh = max(int(iw * scale), 1), max(int(ih * scale), 1)
        img = raw.resize((nw, nh), Image.LANCZOS)
        self._map_img_tk = ImageTk.PhotoImage(img)  # keep a ref on self
        self.map_canvas.delete("all")
        # center it
        x = (w - nw) // 2
        y = (h - nh) // 2
        self.map_canvas.create_image(x, y, anchor="nw", image=self._map_img_tk)

    def set_blocks(self, block_ids):
        """Populate the Select Block list."""
        self.block_list.delete(0, "end")
        for b in sorted(block_ids):
            self.block_list.insert("end", b)