# hw_display.py
# Simple Tkinter-based display for the Wayside Controller HW module.
# Oliver Kettelson-Belinkie, 2025

import tkinter as tk
from tkinter import ttk
from typing import Dict, List

class HW_Display:

    is_ready: bool = True

    def __init__(self, root: tk.Tk, available_blocks: List[str]) -> None:

        self.root = root
        self.root.title("Track Controller HW")
        self.root.geometry("900x540")

        self.speed_var = tk.StringVar(value="Speed: 0 mph")
        self.auth_var = tk.StringVar(value="Authority: 0 yd")
        self.emergency_label = tk.Label(self.root, text="EMERGENCY: OFF", fg="white", bg="#4caf50", padx=10, pady=5)
        self.emergency_label.pack(anchor="w", padx=10, pady=8)

        row = ttk.Frame(self.root, padding=10)
        row.pack(fill=tk.X)
        ttk.Label(row, textvariable=self.speed_var).pack(side=tk.LEFT, padx=10)
        ttk.Label(row, textvariable=self.auth_var).pack(side=tk.LEFT, padx=10)

        self.map_canvas = tk.Canvas(self.root, bg="#ddd", height=260)
        self.map_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.block_listbox = tk.Listbox(self.root, height=6)

        for b in available_blocks:

            self.block_listbox.insert(tk.END, b)

        self.block_listbox.pack(fill=tk.X, padx=10, pady=(0, 10))

    def show_vital(
        self,
        emergency: bool,
        speed_mph: int,
        authority_yards: int,
        light_states: Dict,
        gate_states: Dict,
        switch_states: Dict,
        occupied_blocks: List,
    ) -> None:
        
        self.speed_var.set(f"Speed: {speed_mph} mph")
        self.auth_var.set(f"Authority: {authority_yards} yd")
        self.emergency_label.config(text="EMERGENCY: ON" if emergency else "EMERGENCY: OFF",
                                    bg="#e53935" if emergency else "#4caf50")
        self.map_canvas.delete("all")
        self.map_canvas.create_text(12, 12, anchor="nw", text=f"Occupied: {occupied_blocks}")

    def show_status(self, msg: str) -> None:
        print("[STATUS]", msg)

    def show_safety(self, report: Dict) -> None:
        print("[SAFETY]", report)

    def clear(self) -> None:
        self.map_canvas.delete("all")

    def shutdown(self) -> None:
        self.root.destroy()