"""Standalone Time Controller Application.

This is the master clock application that controls the simulation speed
for all modules in the train system. Run this first, then launch other modules.

Author: GitHub Copilot
"""
import tkinter as tk
from tkinter import ttk
import sys
import os

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from time_controller import get_time_controller

class TimeControllerApp(tk.Tk):
    """Standalone Time Controller Application.
    
    Master clock control for the entire train system simulation.
    All modules will read from this to synchronize their update rates.
    """
    
    def __init__(self):
        super().__init__()
        self.title("Train System - Time Controller")
        self.geometry("600x400")
        self.resizable(False, False)
        
        # Get time controller singleton
        self.time_controller = get_time_controller()
        
        # Track start time for real elapsed time
        import time
        self.start_real_time = time.time()
        
        self._create_widgets()
        self._start_updates()
    
    def _create_widgets(self):
        """Create UI widgets."""
        # Title
        title_frame = ttk.Frame(self)
        title_frame.pack(fill="x", padx=20, pady=20)
        
        title_label = ttk.Label(
            title_frame,
            text="Train System Time Controller",
            font=("TkDefaultFont", 16, "bold")
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Master Clock for All Modules",
            font=("TkDefaultFont", 10)
        )
        subtitle_label.pack()
        
        # Speed control section
        speed_frame = ttk.LabelFrame(self, text="Simulation Speed Control", padding=15)
        speed_frame.pack(fill="x", padx=20, pady=10)
        
        # Speed buttons
        button_frame = ttk.Frame(speed_frame)
        button_frame.pack(fill="x", pady=5)
        
        ttk.Label(button_frame, text="Set Speed:").pack(side="left", padx=(0, 10))
        
        speeds = [0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
        for speed in speeds:
            btn = ttk.Button(
                button_frame,
                text=f"{speed}x",
                command=lambda s=speed: self._set_speed(s),
                width=7
            )
            btn.pack(side="left", padx=3)
        
        # Custom speed entry
        custom_frame = ttk.Frame(speed_frame)
        custom_frame.pack(fill="x", pady=10)
        
        ttk.Label(custom_frame, text="Custom Speed:").pack(side="left", padx=(0, 5))
        self.custom_speed_var = tk.StringVar(value="1.0")
        custom_entry = ttk.Entry(custom_frame, textvariable=self.custom_speed_var, width=10)
        custom_entry.pack(side="left", padx=5)
        
        ttk.Button(
            custom_frame,
            text="Apply",
            command=self._apply_custom_speed
        ).pack(side="left", padx=5)
        
        # Control buttons
        control_frame = ttk.LabelFrame(self, text="Simulation Control", padding=15)
        control_frame.pack(fill="x", padx=20, pady=10)
        
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack()
        
        self.pause_button = ttk.Button(
            btn_frame,
            text="⏸ Pause",
            command=self._toggle_pause,
            width=15
        )
        self.pause_button.pack(side="left", padx=5)
        
        ttk.Button(
            btn_frame,
            text="🔄 Reset Time",
            command=self._reset_time,
            width=15
        ).pack(side="left", padx=5)
        
        # Status display
        status_frame = ttk.LabelFrame(self, text="System Status", padding=15)
        status_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Create grid for status info
        status_grid = ttk.Frame(status_frame)
        status_grid.pack(expand=True)
        
        # Current speed
        ttk.Label(status_grid, text="Current Speed:", font=("TkDefaultFont", 11)).grid(
            row=0, column=0, sticky="e", padx=5, pady=8
        )
        self.speed_label = ttk.Label(
            status_grid, text="1.0x", font=("TkDefaultFont", 14, "bold"), foreground="blue"
        )
        self.speed_label.grid(row=0, column=1, sticky="w", padx=5, pady=8)
        
        # Update interval
        ttk.Label(status_grid, text="Update Interval:", font=("TkDefaultFont", 11)).grid(
            row=1, column=0, sticky="e", padx=5, pady=8
        )
        self.interval_label = ttk.Label(
            status_grid, text="1000 ms", font=("TkDefaultFont", 14, "bold"), foreground="green"
        )
        self.interval_label.grid(row=1, column=1, sticky="w", padx=5, pady=8)
        
        # Simulation time
        ttk.Label(status_grid, text="Simulation Time:", font=("TkDefaultFont", 11)).grid(
            row=2, column=0, sticky="e", padx=5, pady=8
        )
        self.sim_time_label = ttk.Label(
            status_grid, text="0.0 s", font=("TkDefaultFont", 14, "bold"), foreground="purple"
        )
        self.sim_time_label.grid(row=2, column=1, sticky="w", padx=5, pady=8)
        
        # Real time elapsed
        ttk.Label(status_grid, text="Real Time Elapsed:", font=("TkDefaultFont", 11)).grid(
            row=3, column=0, sticky="e", padx=5, pady=8
        )
        self.real_time_label = ttk.Label(
            status_grid, text="0.0 s", font=("TkDefaultFont", 14, "bold"), foreground="orange"
        )
        self.real_time_label.grid(row=3, column=1, sticky="w", padx=5, pady=8)
        
        # Status indicator
        ttk.Label(status_grid, text="Status:", font=("TkDefaultFont", 11)).grid(
            row=4, column=0, sticky="e", padx=5, pady=8
        )
        self.status_label = ttk.Label(
            status_grid, text="● Running", font=("TkDefaultFont", 14, "bold"), foreground="green"
        )
        self.status_label.grid(row=4, column=1, sticky="w", padx=5, pady=8)
    
    def _set_speed(self, speed: float):
        """Set simulation speed."""
        self.time_controller.set_speed_multiplier(speed)
        self.custom_speed_var.set(str(speed))
        self._update_display()
        print(f"[TimeController] Speed set to {speed}x")
    
    def _apply_custom_speed(self):
        """Apply custom speed from entry."""
        try:
            speed = float(self.custom_speed_var.get())
            if speed <= 0:
                raise ValueError("Speed must be positive")
            self.time_controller.set_speed_multiplier(speed)
            self._update_display()
            print(f"[TimeController] Custom speed set to {speed}x")
        except ValueError as e:
            print(f"[TimeController] Invalid speed value: {e}")
            self.custom_speed_var.set(str(self.time_controller.speed_multiplier))
    
    def _toggle_pause(self):
        """Toggle pause state."""
        paused = self.time_controller.toggle_pause()
        self.pause_button.config(text="▶ Resume" if paused else "⏸ Pause")
        self.status_label.config(
            text="● Paused" if paused else "● Running",
            foreground="red" if paused else "green"
        )
        self._update_display()
    
    def _reset_time(self):
        """Reset simulation time."""
        self.time_controller.reset_sim_time()
        import time
        self.start_real_time = time.time()
        self._update_display()
        print("[TimeController] Time reset")
    
    def _update_display(self):
        """Update display labels."""
        tc = self.time_controller
        
        # Update labels
        self.speed_label.config(text=f"{tc.speed_multiplier}x")
        self.interval_label.config(text=f"{tc.get_update_interval_ms()} ms")
        self.sim_time_label.config(text=f"{tc.get_sim_time():.1f} s")
        
        # Update real time
        import time
        real_elapsed = time.time() - self.start_real_time
        self.real_time_label.config(text=f"{real_elapsed:.1f} s")
    
    def _start_updates(self):
        """Start periodic updates."""
        self._periodic_update()
    
    def _periodic_update(self):
        """Periodic update function."""
        # Advance simulation time if not paused
        if not self.time_controller.paused:
            self.time_controller.advance_sim_time()
        
        # Update display
        self._update_display()
        
        # Schedule next update
        interval_ms = self.time_controller.get_update_interval_ms()
        self.after(min(interval_ms, 100), self._periodic_update)  # Cap at 100ms for UI responsiveness


if __name__ == "__main__":
    app = TimeControllerApp()
    app.mainloop()