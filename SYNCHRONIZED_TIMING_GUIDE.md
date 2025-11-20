# Synchronized Timing Implementation Guide

## Overview
This guide explains how to integrate the centralized TimeController into all modules to ensure synchronized updates across the entire train system.

## How It Works

1. **time_controller.py**: Singleton that manages timing globally
2. **time_manager_ui.py**: UI to control speed multiplier (launches first)
3. **time_config.json**: Saved configuration file (auto-generated)
4. **All modules**: Read from TimeController to sync their updates

## Implementation Steps for Each Module

### Step 1: Import the TimeController

Add to the top of your file:
```python
import sys
import os

# Add parent directory to path (if not already added)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from time_controller import get_time_controller
```

### Step 2: Initialize in __init__ or setup

```python
class YourModule:
    def __init__(self):
        # Get the shared time controller
        self.time_controller = get_time_controller()
        
        # Your other initialization...
```

### Step 3: Replace Fixed Intervals with Dynamic Ones

**BEFORE (Fixed interval):**
```python
self.after(500, self.update_loop)  # Always 500ms
```

**AFTER (Dynamic interval from TimeController):**
```python
# Get interval from time controller (changes with speed multiplier)
interval_ms = self.time_controller.get_update_interval_ms()
self.after(interval_ms, self.update_loop)
```

### Step 4: For Threading Timers

**BEFORE:**
```python
threading.Timer(1.0, self.run_plc).start()
```

**AFTER:**
```python
interval_s = self.time_controller.get_update_interval_ms() / 1000.0
threading.Timer(interval_s, self.run_plc).start()
```

### Step 5: For time.sleep() calls

**BEFORE:**
```python
time.sleep(0.5)  # Fixed delay
```

**AFTER:**
```python
# Scale sleep by speed multiplier
base_delay = 0.5
actual_delay = base_delay / self.time_controller.speed_multiplier
time.sleep(actual_delay)
```

## Files That Need Updates

### High Priority (Core Update Loops)
1. ✅ **Track_Model/track_model_UI.py** - `self.after(500, self.load_data)`
2. ✅ **train_controller/ui/train_controller_sw_ui.py** - `self.update_interval = 500`
3. ✅ **train_controller/train_manager.py** - `self.after(500, self.simulation_loop)`
4. ✅ **track_controller/New_SW_Code/sw_wayside_controller.py** - Threading timers
5. ✅ **ctc/ctc_ui.py** - `self.root.after(1000, self.update_active_trains_table)`
6. ✅ **Track_Model/Track_Visualizer.py** - Train animation updates

### Medium Priority (Periodic Checks)
7. **track_controller/New_SW_Code/sw_wayside_controller_ui.py** - Block updates
8. **train_controller/ui/train_controller_test_ui.py** - Test UI updates
9. **train_controller/ui/train_controller_hw_ui.py** - Hardware UI updates

### Low Priority (One-time delays or UI-specific)
10. **Track_Model/track_model_UI.py** - Auto-load delay, polling
11. **ctc/ctc_main.py** - Dwell time and station waits

## Example: Complete Implementation for Track Model UI

```python
import tkinter as tk
from tkinter import ttk
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from time_controller import get_time_controller

class TrackModelUI(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Get time controller
        self.time_controller = get_time_controller()
        
        # ... rest of initialization ...
        
        # Start synchronized update loop
        self.load_data()
    
    def load_data(self):
        """Load data and update UI - called periodically."""
        # Your update logic here
        # ...
        
        # Schedule next update using synchronized interval
        interval_ms = self.time_controller.get_update_interval_ms()
        self.after(interval_ms, self.load_data)
```

## Testing

1. Launch `time_manager_ui.py` first
2. Set speed to 2x
3. Launch other modules
4. Verify all modules update twice as fast
5. Change speed to 0.5x
6. Verify all modules update at half speed

## Common Pitfalls

1. **Don't cache the interval** - Always call `get_update_interval_ms()` each time
2. **Import order** - Make sure time_controller.py is in the path
3. **Singleton pattern** - Don't create new instances, use `get_time_controller()`
4. **UI responsiveness** - For UI updates, cap at reasonable values (100-500ms)

## Benefits

- ✅ All modules stay synchronized
- ✅ Speed up/slow down entire simulation
- ✅ Pause all modules at once
- ✅ No more conflicting update rates
- ✅ Easier debugging at slower speeds
- ✅ Prevent file write conflicts by coordinating timing
