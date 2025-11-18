"""Centralized Time Controller for Train System.

This module provides a singleton time controller that manages simulation time
and update rates for all modules. Allows speeding up/slowing down the entire
system synchronously.

Author: GitHub Copilot
"""
import json
import os
import time
import threading
from typing import Optional, Callable

# Default time configuration file
TIME_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "time_config.json")

class TimeController:
    """Singleton time controller for system-wide timing.
    
    Controls the simulation speed multiplier and base update rate.
    All modules should use this for their periodic updates.
    
    Attributes:
        base_dt: Base time step in seconds (default 1.0).
        speed_multiplier: Speed multiplier (1.0 = real-time, 2.0 = 2x speed, etc.).
        paused: Whether simulation is paused.
    """
    
    _instance: Optional['TimeController'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize time controller (only once)."""
        if self._initialized:
            return
            
        self.base_dt = 1.0  # Base time step in seconds
        self.speed_multiplier = 1.0  # 1.0 = real-time
        self.paused = False
        self._sim_time = 0.0  # Simulated time elapsed
        self._real_start_time = time.time()
        self._callbacks = []  # List of (callback, interval) tuples
        self._initialized = True
        
        # Load from config if exists
        self.load_config()
    
    def get_update_interval_ms(self) -> int:
        """Get the current update interval in milliseconds.
        
        This is what tkinter's .after() method should use.
        
        Returns:
            Update interval in milliseconds.
        """
        if self.paused:
            return 1000  # 1 second when paused (for UI responsiveness)
        
        # Effective dt = base_dt / speed_multiplier
        effective_dt = self.base_dt / self.speed_multiplier
        return int(effective_dt * 1000)
    
    def get_effective_dt(self) -> float:
        """Get the effective time step in seconds.
        
        Returns:
            Effective time step accounting for speed multiplier.
        """
        if self.paused:
            return 0.0
        return self.base_dt / self.speed_multiplier
    
    def set_speed_multiplier(self, multiplier: float) -> None:
        """Set the simulation speed multiplier.
        
        Args:
            multiplier: Speed multiplier (0.5 = half speed, 2.0 = double speed, etc.).
                       Must be > 0.
        """
        if multiplier <= 0:
            raise ValueError("Speed multiplier must be positive")
        
        self.speed_multiplier = multiplier
        self.save_config()
        print(f"[TimeController] Speed multiplier set to {multiplier}x")
    
    def set_base_dt(self, dt: float) -> None:
        """Set the base time step.
        
        Args:
            dt: Base time step in seconds. Must be > 0.
        """
        if dt <= 0:
            raise ValueError("Base dt must be positive")
        
        self.base_dt = dt
        self.save_config()
        print(f"[TimeController] Base dt set to {dt} seconds")
    
    def toggle_pause(self) -> bool:
        """Toggle pause state.
        
        Returns:
            New pause state (True if now paused).
        """
        self.paused = not self.paused
        print(f"[TimeController] Simulation {'paused' if self.paused else 'resumed'}")
        return self.paused
    
    def advance_sim_time(self) -> float:
        """Advance simulation time by one step.
        
        Returns:
            New simulation time in seconds.
        """
        if not self.paused:
            self._sim_time += self.base_dt
        return self._sim_time
    
    def get_sim_time(self) -> float:
        """Get current simulation time.
        
        Returns:
            Simulation time in seconds.
        """
        return self._sim_time
    
    def reset_sim_time(self) -> None:
        """Reset simulation time to zero."""
        self._sim_time = 0.0
        self._real_start_time = time.time()
        print("[TimeController] Simulation time reset")
    
    def save_config(self) -> None:
        """Save current configuration to JSON file."""
        config = {
            "base_dt": self.base_dt,
            "speed_multiplier": self.speed_multiplier,
            "paused": self.paused
        }
        try:
            os.makedirs(os.path.dirname(TIME_CONFIG_FILE), exist_ok=True)
            with open(TIME_CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"[TimeController] Error saving config: {e}")
    
    def load_config(self) -> None:
        """Load configuration from JSON file."""
        try:
            if os.path.exists(TIME_CONFIG_FILE):
                with open(TIME_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                self.base_dt = config.get("base_dt", 1.0)
                self.speed_multiplier = config.get("speed_multiplier", 1.0)
                self.paused = config.get("paused", False)
                print(f"[TimeController] Loaded config: dt={self.base_dt}s, speed={self.speed_multiplier}x")
        except Exception as e:
            print(f"[TimeController] Error loading config: {e}")


# Global singleton instance
_time_controller = TimeController()

def get_time_controller() -> TimeController:
    """Get the global time controller instance.
    
    Returns:
        TimeController singleton instance.
    """
    return _time_controller