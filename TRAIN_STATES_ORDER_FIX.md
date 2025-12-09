# Train States Order Fix

## Problem

Trains appeared in **random order** in `train_states.json`:
- Sometimes: `train_1`, `train_2`, `train_3`, `train_4`, `train_5` ✅
- Other times: `train_2`, `train_5`, `train_1`, `train_3`, `train_4` ❌
- Or: `train_1` at bottom, then moved to top when new train dispatched ❌

**User Report:**
> "train one is currently at the bottom but as soon as we dispatch a new train it gets moved to the top I think this is causing a lot of issues"

**Why it matters:**
- Confusing when inspecting files
- Potential issues with code that assumes specific order
- Makes debugging harder
- Looks unprofessional

---

## Root Cause

### Python Dictionary Behavior

Python 3.7+ dictionaries **maintain insertion order**, but:
- When you load JSON, modify it, and save it back, the order can change
- Different code paths insert keys in different orders
- `dict[key] = value` maintains order for existing keys, but new keys go at the end
- Multiple threads writing can cause unpredictable ordering

### Multiple Write Locations

**8 different places** write to `train_states.json`:
1. `train_controller/train_manager.py` - 3 locations (init, delete, update)
2. `train_controller/api/train_controller_api.py` - 2 locations (state writes)
3. `train_controller/api/train_api_server.py` - 1 location (server writes)
4. `Train_Model/train_model_core.py` - 2 locations (via `safe_write_json()`)

**Each location** was writing keys in whatever order they appeared in memory!

---

## The Fix: Sorted Keys Everywhere

### Strategy
**Always sort train keys before writing to `train_states.json`**

```python
# BEFORE (random order)
json.dump(all_states, f, indent=4)

# AFTER (sorted order)
sorted_states = {k: all_states[k] for k in sorted(all_states.keys())}
json.dump(sorted_states, f, indent=4)
```

**Result:** Trains always appear in order: `train_1`, `train_2`, `train_3`, `train_4`, `train_5`

---

## Changes Applied

### File 1: `train_controller/train_manager.py` (3 locations)

**Location 1 - Initialize Train State (line 376):**
```python
# BEFORE
all_states[train_key] = initial_state
with open(self.state_file, 'w') as f:
    json.dump(all_states, f, indent=4)

# AFTER  
all_states[train_key] = initial_state
sorted_states = {k: all_states[k] for k in sorted(all_states.keys())}
with open(self.state_file, 'w') as f:
    json.dump(sorted_states, f, indent=4)
```

**Location 2 - Remove Train (line 532):**
```python
# BEFORE
if train_key in all_states:
    del all_states[train_key]
with open(self.state_file, 'w') as f:
    json.dump(all_states, f, indent=4)

# AFTER
if train_key in all_states:
    del all_states[train_key]
sorted_states = {k: all_states[k] for k in sorted(all_states.keys())}
with open(self.state_file, 'w') as f:
    json.dump(sorted_states, f, indent=4)
```

**Location 3 - Update Train State (line 596):**
```python
# BEFORE
if train_key in all_states:
    all_states[train_key].update(state_updates)
with open(self.state_file, 'w') as f:
    json.dump(all_states, f, indent=4)

# AFTER
if train_key in all_states:
    all_states[train_key].update(state_updates)
sorted_states = {k: all_states[k] for k in sorted(all_states.keys())}
with open(self.state_file, 'w') as f:
    json.dump(sorted_states, f, indent=4)
```

---

### File 2: `train_controller/api/train_controller_api.py` (2 locations)

**Location 1 - Set State (Multi-train mode) (line 266):**
```python
# BEFORE
all_states[train_key] = {
    'inputs': inputs,
    'outputs': outputs
}
with open(self.state_file, 'w') as f:
    json.dump(all_states, f, indent=4)

# AFTER
all_states[train_key] = {
    'inputs': inputs,
    'outputs': outputs
}
sorted_states = {k: all_states[k] for k in sorted(all_states.keys())}
with open(self.state_file, 'w') as f:
    json.dump(sorted_states, f, indent=4)
```

**Location 2 - Set State (Legacy mode) (line 290):**
```python
# BEFORE
for key, value in state.items():
    # ... update logic ...
with open(self.state_file, 'w') as f:
    json.dump(all_states, f, indent=4)

# AFTER
for key, value in state.items():
    # ... update logic ...
sorted_states = {k: all_states[k] for k in sorted(all_states.keys())}
with open(self.state_file, 'w') as f:
    json.dump(sorted_states, f, indent=4)
```

---

### File 3: `train_controller/api/train_api_server.py` (1 location)

**Function: `write_json_file()` (line 55):**
```python
# BEFORE
def write_json_file(filepath, data):
    """Thread-safe JSON file write."""
    with file_lock:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)

# AFTER
def write_json_file(filepath, data):
    """Thread-safe JSON file write with sorted keys for train_states.json."""
    with file_lock:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Sort keys if writing to train_states.json
            if 'train_states.json' in filepath and isinstance(data, dict):
                data = {k: data[k] for k in sorted(data.keys())}
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
```

**Impact:** This fixes ALL 5 server writes to train_states.json!

---

### File 4: `Train_Model/train_model_core.py` (affects 2 call sites)

**Function: `safe_write_json()` (line 47):**
```python
# BEFORE
def safe_write_json(path, data):
    payload = json.dumps(data, indent=4)
    # ...
    if "train_states.json" in path:
        with open(path, "w") as f:
            f.write(payload)

# AFTER
def safe_write_json(path, data):
    # Sort keys if writing to train_states.json
    if "train_states.json" in path and isinstance(data, dict):
        data = {k: data[k] for k in sorted(data.keys())}
    
    payload = json.dumps(data, indent=4)
    # ...
    if "train_states.json" in path:
        with open(path, "w") as f:
            f.write(payload)
```

**Impact:** This fixes both Train Model writes (failure modes + state writes)!

---

## Testing

### Before Fix:
```json
{
    "train_3": { ... },
    "train_1": { ... },  ← Train 1 at bottom
    "train_5": { ... },
    "train_2": { ... },
    "train_4": { ... }
}
```

**Dispatch new train → Train 1 jumps to top**

```json
{
    "train_1": { ... },  ← Train 1 moved to top!
    "train_3": { ... },
    "train_2": { ... },
    "train_4": { ... },
    "train_5": { ... }
}
```

### After Fix:
```json
{
    "train_1": { ... },
    "train_2": { ... },
    "train_3": { ... },
    "train_4": { ... },
    "train_5": { ... }
}
```

**Dispatch any train → Order stays consistent** ✅

---

## How to Verify

### Check Current File Order:
```bash
python -c "
import json
with open('train_controller/data/train_states.json') as f:
    data = json.load(f)
    print('Current order:', list(data.keys()))
"
```

**Expected:**
```
Current order: ['train_1', 'train_2', 'train_3', 'train_4', 'train_5']
```

### Test Consistency:
```bash
# Dispatch multiple trains
python combine_ctc_wayside_test.py

# After each dispatch, check order:
python -c "
import json
with open('train_controller/data/train_states.json') as f:
    data = json.load(f)
    print(list(data.keys()))
"
```

**Should always show:** `['train_1', 'train_2', 'train_3', 'train_4', 'train_5']`

---

## Impact

### Before Fix:
- ❌ Random train order
- ❌ Order changed on every write
- ❌ Confusing to debug
- ❌ Unpredictable behavior

### After Fix:
- ✅ Consistent alphabetical order (train_1 first)
- ✅ Order never changes
- ✅ Easy to inspect and debug
- ✅ Predictable behavior

---

## Files Modified (4 Files, 8 Write Locations)

| File | Locations | Change |
|------|-----------|--------|
| `train_controller/train_manager.py` | 3 | Added sorted dict comprehension |
| `train_controller/api/train_controller_api.py` | 2 | Added sorted dict comprehension |
| `train_controller/api/train_api_server.py` | 1 (affects 5 writes) | Auto-sort in write_json_file() |
| `Train_Model/train_model_core.py` | 1 (affects 2 writes) | Auto-sort in safe_write_json() |

**Total:** 8 write locations fixed

---

## Backward Compatibility

✅ **Fully backward compatible**

- No changes to JSON structure
- No changes to key names
- Only affects the **order** keys appear in file
- All existing code continues to work
- File reading unaffected (order doesn't matter for reads)

---

## Related Issues

This fix also helps with:
- **Debugging** - easier to find specific trains in file
- **Version control** - diffs show actual changes, not reordering
- **Code assumptions** - if any code depends on order, it's now reliable

---

## Git Commit

```
Commit: 06fa177
Branch: phase3
Message: Fix: Maintain consistent train order in train_states.json
```

---

## Summary

**Status:** ✅ **FIXED**

**Problem:** Random train order in JSON file  
**Solution:** Sort keys before every write  
**Result:** Trains always in order (train_1, train_2, train_3, train_4, train_5)

**Your `train_states.json` will now maintain consistent order!** 📋✨


