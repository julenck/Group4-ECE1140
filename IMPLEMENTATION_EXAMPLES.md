# Synchronized Timing - Implementation Examples

## Example 1: Track Model UI (track_model_UI.py)

### Changes needed:

**1. Add imports at the top:**
```python
import sys
# Add parent directory for time_controller
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from time_controller import get_time_controller
```

**2. In `__init__` method, add:**
```python
def __init__(self):
    super().__init__()
    # ... existing code ...
    
    # Get time controller for synchronized updates
    self.time_controller = get_time_controller()
```

**3. Update the `load_data` method (around line 668):**
```python
# BEFORE:
self.after(500, self.load_data)

# AFTER:
interval_ms = self.time_controller.get_update_interval_ms()
self.after(interval_ms, self.load_data)
```

## Example 2: Train Controller SW UI (train_controller/ui/train_controller_sw_ui.py)

### Changes needed:

**1. Add imports at top:**
```python
import sys
import os
# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)
if grandparent_dir not in sys.path:
    sys.path.append(grandparent_dir)

from time_controller import get_time_controller
```

**2. In `__init__` method:**
```python
def __init__(self, ...):
    super().__init__()
    # Get time controller
    self.time_controller = get_time_controller()
    
    # REMOVE THIS LINE:
    # self.update_interval = 500  # Fixed interval
    
    # ... rest of init ...
```

**3. Update `periodic_update` method:**
```python
def periodic_update(self):
    """Update display every update_interval milliseconds."""
    try:
        # ... your update logic ...
        
        # Get dynamic interval from time controller
        interval_ms = self.time_controller.get_update_interval_ms()
        self.after(interval_ms, self.periodic_update)
    except Exception as e:
        # ...error handling...
```

## Example 3: SW Wayside Controller (track_controller/New_SW_Code/sw_wayside_controller.py)

### Changes needed:

**1. Add import at top:**
```python
import sys
import os
# Add parent directories
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)
if grandparent_dir not in sys.path:
    sys.path.append(grandparent_dir)

from time_controller import get_time_controller
```

**2. In `__init__` method:**
```python
def __init__(self, vital, plc=""):
    # ... existing code ...
    
    # Get time controller
    self.time_controller = get_time_controller()
```

**3. Update threading timers:**
```python
# In run_plc method - BEFORE:
threading.Timer(0.2, self.run_plc).start()

# AFTER:
interval_s = self.time_controller.get_update_interval_ms() / 1000.0
# Cap minimum interval for PLC updates
interval_s = max(0.1, min(interval_s, 1.0))
threading.Timer(interval_s, self.run_plc).start()
```

```python
# In run_trains method - BEFORE:
threading.Timer(1.0, self.run_trains).start()

# AFTER:
interval_s = self.time_controller.get_update_interval_ms() / 1000.0
threading.Timer(interval_s, self.run_trains).start()
```

## Example 4: CTC UI (ctc/ctc_ui.py)

### Changes needed:

**1. Add import at top:**
```python
import sys
# Add parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from time_controller import get_time_controller
```

**2. In `__init__` method:**
```python
def __init__(self):
    # ... existing code ...
    
    # Get time controller
    self.time_controller = get_time_controller()
```

**3. Update `update_active_trains_table` method:**
```python
def update_active_trains_table(self):
    # ... update logic ...
    
    # BEFORE:
    # self.root.after(1000, self.update_active_trains_table)
    
    # AFTER:
    interval_ms = self.time_controller.get_update_interval_ms()
    self.root.after(interval_ms, self.update_active_trains_table)
```

## Example 5: Train Manager (train_controller/train_manager.py)

### Changes needed:

**1. Add import:**
```python
from time_controller import get_time_controller
```

**2. In `__init__`:**
```python
def __init__(self):
    # ... existing code ...
    self.time_controller = get_time_controller()
```

**3. Update `simulation_loop`:**
```python
def simulation_loop(self):
    # ... simulation logic ...
    
    # BEFORE:
    # self.after(500, self.simulation_loop)
    
    # AFTER:
    interval_ms = self.time_controller.get_update_interval_ms()
    self.after(interval_ms, self.simulation_loop)
```

## Example 6: CTC Main (ctc/ctc_main.py) - Dwell Time

### For blocking sleep calls:

```python
# At top, add:
from time_controller import get_time_controller
time_controller = get_time_controller()

# In the station loop - BEFORE:
time.sleep(dwell_time_s)

# AFTER:
# Scale dwell time by speed multiplier
actual_dwell = dwell_time_s / time_controller.speed_multiplier
time.sleep(actual_dwell)
```

## Quick Reference: Common Patterns

### Pattern 1: Tkinter .after()
```python
# Always use dynamic interval
interval_ms = self.time_controller.get_update_interval_ms()
self.after(interval_ms, self.your_method)
```

### Pattern 2: Threading.Timer
```python
# Convert ms to seconds
interval_s = self.time_controller.get_update_interval_ms() / 1000.0
threading.Timer(interval_s, self.your_method).start()
```

### Pattern 3: time.sleep()
```python
# Scale by speed multiplier
base_delay = 1.0  # Your desired delay
actual_delay = base_delay / self.time_controller.speed_multiplier
time.sleep(actual_delay)
```

### Pattern 4: Check if paused
```python
if not self.time_controller.paused:
    # Do work
    pass
```

## Testing Checklist

- [ ] Launch time_manager_ui.py
- [ ] Set speed to 2x
- [ ] Launch each module
- [ ] Verify updates are 2x faster
- [ ] Set speed to 0.5x
- [ ] Verify updates are 2x slower
- [ ] Test pause button
- [ ] Verify all modules stop updating
- [ ] Check console for sync messages
