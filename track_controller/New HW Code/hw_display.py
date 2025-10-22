from typing import List, Dict, Callable, Optional
import tkinter as tk
from tkinter import ttk, filedialog

def _pill(label, text: str, kind: str = "ok") -> None:
    colors = {
        "ok": ("#2e7d32", "#e8f5e9"),
        "warn": ("#ef6c00", "#fff3e0"),
        "bad": ("#b71c1c", "#ffebee"),
        "info": ("#1565c0", "#e3f2fd"),
        "muted": ("#455a64", "#eceff1"),
    }
    fg, bg = colors.get(kind, colors["muted"])
    label.configure(text=text, fg=fg, bg=bg, padx=10, pady=2)


class hw_display:
    def __init__(self) -> None:
        # handlers wired by UI
        self.on_select_block: Optional[Callable[[int], None]] = None
        self.on_upload_plc: Optional[Callable[[str], None]] = None
        self.on_set_switch: Optional[Callable[[int, int], None]] = None
        self.on_toggle_maintenance: Optional[Callable[[bool], None]] = None

        self.is_ready: bool = False
        self._root: Optional[tk.Tk] = None

        # widgets set later
        self._lbl_emergency: Optional[ttk.Label] = None
        self._lbl_speed: Optional[ttk.Label] = None
        self._lbl_authority: Optional[ttk.Label] = None
        self._list_blocks: Optional[tk.Listbox] = None
        self._txt_block_info: Optional[tk.Text] = None
        self._btn_upload: Optional[ttk.Button] = None
        self._maintenance_var: Optional[tk.BooleanVar] = None  # <-- create after root exists
        self._cmb_switch_block: Optional[ttk.Combobox] = None
        self._cmb_switch_state: Optional[ttk.Combobox] = None
        self._btn_set_switch: Optional[ttk.Button] = None
        self._status: Optional[ttk.Label] = None

    def init(self) -> None:
        if self.is_ready:
            return
        self._root = tk.Tk()
        self._root.title("Track Controller HW")
        self._root.geometry("1080x680")
        self._root.configure(bg="#fafafa")
        self._build()
        self.is_ready = True

    def shutdown(self) -> None:
        if self._root:
            self._root.destroy()
        self.is_ready = False

    def _build(self) -> None:
        assert self._root is not None
        # create BooleanVar now that root exists
        self._maintenance_var = tk.BooleanVar(self._root, value=False)

        root = self._root
        style = ttk.Style()
        style.configure("Card.TLabelframe", background="#ffffff")
        style.configure("Card.TLabelframe.Label", font=("Segoe UI", 11, "bold"))
        style.configure("Value.TLabel", font=("Consolas", 22, "bold"))
        style.configure("Small.TLabel", font=("Segoe UI", 10))

        grid = ttk.Frame(root, padding=12)
        grid.pack(fill="both", expand=True)

        grid.columnconfigure(0, weight=2)
        grid.columnconfigure(1, weight=3)
        grid.rowconfigure(0, weight=2)
        grid.rowconfigure(1, weight=3)

        map_card = ttk.LabelFrame(grid, text="Map", style="Card.TLabelframe")
        map_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        map_canvas = tk.Canvas(map_card, height=260, background="#f5f5f5", highlightthickness=0)
        map_canvas.pack(fill="both", expand=True, padx=8, pady=8)
        map_canvas.create_text(200, 120, text="(Map goes here)", fill="#9e9e9e", font=("Segoe UI", 12))

        vital = ttk.LabelFrame(grid, text="Vital / Emergency Comms", style="Card.TLabelframe")
        vital.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))

        vital_row = ttk.Frame(vital)
        vital_row.pack(fill="x", padx=12, pady=(12, 6))
        self._lbl_emergency = tk.Label(vital_row, text="OFF")
        self._lbl_emergency.pack(side="left")
        _pill(self._lbl_emergency, "EMERGENCY: OFF", "ok")

        numbers = ttk.Frame(vital)
        numbers.pack(fill="x", padx=12, pady=(6, 12))
        speed_box = ttk.Frame(numbers)
        speed_box.pack(side="left", padx=(0, 20))
        ttk.Label(speed_box, text="Speed (mph)", style="Small.TLabel").pack(anchor="w")
        self._lbl_speed = ttk.Label(speed_box, text="0", style="Value.TLabel")
        self._lbl_speed.pack(anchor="w")

        auth_box = ttk.Frame(numbers)
        auth_box.pack(side="left")
        ttk.Label(auth_box, text="Authority (yards)", style="Small.TLabel").pack(anchor="w")
        self._lbl_authority = ttk.Label(auth_box, text="0", style="Value.TLabel")
        self._lbl_authority.pack(anchor="w")

        select_card = ttk.LabelFrame(grid, text="Select Block", style="Card.TLabelframe")
        select_card.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(8, 0))
        select_card.columnconfigure(0, weight=1)
        self._list_blocks = tk.Listbox(select_card, height=12, activestyle="dotbox")
        self._list_blocks.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self._list_blocks.bind("<<ListboxSelect>>", self._on_block_select)

        info_card = ttk.LabelFrame(grid, text="Block Info", style="Card.TLabelframe")
        info_card.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=(8, 0))
        info_card.rowconfigure(0, weight=1)
        info_card.columnconfigure(0, weight=1)
        self._txt_block_info = tk.Text(info_card, height=10, wrap="word", state="disabled", background="#fcfcfc")
        self._txt_block_info.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        bottom = ttk.Frame(root, padding=(12, 0, 12, 12))
        bottom.pack(fill="x", side="bottom")

        plc_card = ttk.LabelFrame(bottom, text="Upload PLC", style="Card.TLabelframe")
        plc_card.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=(8, 0))
        self._btn_upload = ttk.Button(plc_card, text="Choose PLC…", command=self._choose_plc)
        self._btn_upload.pack(padx=10, pady=10, anchor="w")

        maint_card = ttk.LabelFrame(bottom, text="Maintenance", style="Card.TLabelframe")
        maint_card.pack(side="left", fill="x", expand=True, padx=(8, 0), pady=(8, 0))

        chk = ttk.Checkbutton(maint_card, text="Maintenance Mode",
                              variable=self._maintenance_var, command=self._toggle_maintenance)
        chk.pack(padx=10, pady=(10, 4), anchor="w")

        row = ttk.Frame(maint_card)
        row.pack(fill="x", padx=10, pady=(6, 10))
        ttk.Label(row, text="Select switch block:", style="Small.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self._cmb_switch_block = ttk.Combobox(row, values=[], state="disabled", width=12)
        self._cmb_switch_block.grid(row=0, column=1, sticky="w", padx=(8, 0), pady=(0, 4))

        ttk.Label(row, text="Set state:", style="Small.TLabel").grid(row=1, column=0, sticky="w")
        self._cmb_switch_state = ttk.Combobox(row, values=["0", "1"], state="disabled", width=12)
        self._cmb_switch_state.grid(row=1, column=1, sticky="w", padx=(8, 0))

        self._btn_set_switch = ttk.Button(row, text="Apply", state="disabled", command=self._apply_switch)
        self._btn_set_switch.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self._status = ttk.Label(root, text="", style="Small.TLabel", foreground="#455a64")
        self._status.pack(fill="x", padx=12, pady=(0, 10), anchor="w")

        self.set_maintenance_enabled(False)

    # ---------- public API (called by UI/controller)
    def run_forever(self) -> None:
        import tkinter as tk
        tk.mainloop()

    def set_status(self, text: str) -> None:
        if self._status:
            self._status.configure(text=text)

    def update_blocks(self, block_ids: List[int]) -> None:
        if not self._list_blocks:
            return
        self._list_blocks.delete(0, tk.END)
        for b in block_ids:
            self._list_blocks.insert(tk.END, f"Block {b}")
        # also feed combobox for maintenance
        if self._cmb_switch_block:
            self._cmb_switch_block["values"] = [str(b) for b in block_ids]

    def show_vital(
        self,
        emergency: bool,
        speed_mph: int,
        authority_yards: int,
        light_states: List[int],
        gate_states: List[int],
        switch_states: List[int],
        occupied_blocks: List[int],
    ) -> None:
        # emergency pill
        if self._lbl_emergency:
            _pill(self._lbl_emergency,
                  "EMERGENCY: ACTIVE" if emergency else "EMERGENCY: OFF",
                  "bad" if emergency else "ok")
        if self._lbl_speed:
            self._lbl_speed.configure(text=str(speed_mph))
        if self._lbl_authority:
            self._lbl_authority.configure(text=str(authority_yards))
        # also show a compact status line
        occ = ", ".join(map(str, occupied_blocks)) or "-"
        self.set_status(f"Occupied: {occ}  |  Signals: {light_states}  |  Gates: {gate_states}  |  Switches: {switch_states}")
        if self._root:
            self._root.update_idletasks()

    def show_block_info(self, data: Dict) -> None:
        if not self._txt_block_info:
            return
        self._txt_block_info.configure(state="normal")
        self._txt_block_info.delete("1.0", tk.END)
        for k, v in data.items():
            self._txt_block_info.insert(tk.END, f"{k}: {v}\n")
        self._txt_block_info.configure(state="disabled")

    def set_maintenance_enabled(self, enabled: bool) -> None:
        self._maintenance_var.set(enabled)
        state = "normal" if enabled else "disabled"
        if self._cmb_switch_block:
            self._cmb_switch_block.configure(state=state)
        if self._cmb_switch_state:
            self._cmb_switch_state.configure(state=state)
        if self._btn_set_switch:
            self._btn_set_switch.configure(state=state)
        if self._btn_upload:
            self._btn_upload.configure(state=state)

    # ---------- handlers (wired to UI)
    def _on_block_select(self, _evt=None):
        if not self._list_blocks or not self.on_select_block:
            return
        sel = self._list_blocks.curselection()
        if not sel:
            return
        # "Block X" → X
        raw = self._list_blocks.get(sel[0]).split()[-1]
        try:
            self.on_select_block(int(raw))
        except Exception:
            pass

    def _choose_plc(self):
        if not self.on_upload_plc:
            return
        path = filedialog.askopenfilename(title="Choose PLC file", filetypes=[("PLC/JSON/TXT", "*.plc *.json *.txt"), ("All files", "*.*")])
        if path:
            self.on_upload_plc(path)

    def _toggle_maintenance(self):
        if self.on_toggle_maintenance:
            self.on_toggle_maintenance(bool(self._maintenance_var.get()))
        # reflect immediately
        self.set_maintenance_enabled(bool(self._maintenance_var.get()))

    def _apply_switch(self):
        if not (self.on_set_switch and self._cmb_switch_block and self._cmb_switch_state):
            return
        try:
            b = int(self._cmb_switch_block.get())
            s = int(self._cmb_switch_state.get())
            self.on_set_switch(b, s)
        except Exception:
            self.set_status("Invalid switch selection/state")
