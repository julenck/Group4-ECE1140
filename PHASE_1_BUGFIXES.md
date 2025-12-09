# Phase 1 Bug Fixes ✅

## Issues Found During Testing

### Issue 1: `NoneType * float` Error
**Error Message:**
```
Periodic Update Error: unsupported operand type(s) for *: 'NoneType' and 'float'
ADC Read Error: unsupported operand type(s) for *: 'NoneType' and 'float'
```

**Root Cause:**
- Server sets `kp: null` and `ki: null` by default (must be set through UI)
- Code used: `state.get('kp', 5000.0)` 
- **Problem:** `.get()` only uses default if key is MISSING, not if key exists with value `None`
- When `kp = None`, calculation `None * error` causes TypeError

**Fix Applied:**
Changed from: `state.get('kp', 5000.0)` 
Changed to: `state.get('kp') or 5000.0`

This returns `5000.0` if `kp` is either `None` OR missing.

**Files Fixed:**
1. `train_controller/ui/train_controller_hw_ui.py` (3 locations)
   - Line ~123: `calculate_power_command()` method 1
   - Line ~299: `calculate_power_command()` method 2
   - Line ~90: `vital_control_check_and_update()`
   
2. `train_controller/train_controller_hardware.py` (1 location)
   - Line ~230: `set_driver_velocity_adc()` - also fixed `commanded_speed`

### Issue 2: Station Side Flashing "Right"
**Symptom:**
Station side displaying "Right" briefly then disappearing, especially on unused train slots (3-5).

**Root Cause:**
Server was using `"Right"` as default value for `station_side` in 4 places. Should be empty string `""` (no station until beacon is read).

**Fix Applied:**
Changed all occurrences of:
```python
"station_side": "Right"  # Wrong default
```
To:
```python
"station_side": ""  # Correct - empty until beacon read
```

**Files Fixed:**
1. `train_controller/api/train_api_server.py` (4 locations)
   - Line ~146: Default train initialization
   - Line ~235: Sync thread beacon data
   - Line ~352: Update endpoint initialization
   - Line ~428: Reset endpoint defaults

### Issue 3: Train 2 Has Duplicate Flat Fields
**Symptom:**
Train 2 in `train_states.json` had BOTH:
- Flat fields at root level (legacy format): `"train_id": 2`, `"commanded_speed": 0.0`, etc.
- Nested structure (correct format): `"inputs": {...}`, `"outputs": {...}`

**Root Cause:**
Old version of train_manager wrote flat format, then API wrote nested format on top. Both formats coexisted, causing confusion.

**Fix Applied:**
Added automatic cleanup logic in server:

1. **In `update_train_state()` endpoint:**
```python
# CLEAN UP: Remove flat fields (legacy format)
keys_to_remove = [k for k in data[train_key].keys() if k not in ['inputs', 'outputs']]
for k in keys_to_remove:
    del data[train_key][k]
```

2. **In `sync_train_data_to_states()` background thread:**
Same cleanup logic runs every 500ms to auto-clean any legacy fields.

**Result:**
- Server automatically removes flat fields
- Only keeps proper `inputs` and `outputs` structure
- Works for all trains (past, present, future)

## Testing

### Before Fixes:
```
❌ Periodic Update Error: unsupported operand type(s) for *: 'NoneType' and 'float'
❌ ADC Read Error: unsupported operand type(s) for *: 'NoneType' and 'float'
❌ Station side flashing "Right" randomly
❌ train_2 has duplicate fields in JSON
```

### After Fixes:
```
✅ No NoneType errors
✅ Station side stays empty until beacon read
✅ Clean nested structure for all trains
✅ LEDs update properly
✅ UI displays work correctly
```

## How to Apply Fixes

### On Main PC:
```bash
# Server already has fixes - just restart it
cd train_controller/api
python train_api_server.py
```

### On Raspberry Pi:
```bash
# Copy updated files
scp train_controller/ui/train_controller_hw_ui.py jamesstruyk@raspberrypi:~/projects/Group4-ECE1140/train_controller/ui/
scp train_controller/train_controller_hardware.py jamesstruyk@raspberrypi:~/projects/Group4-ECE1140/train_controller/

# Restart hardware UI
cd ~/projects/Group4-ECE1140/train_controller/ui
python train_controller_hw_ui.py --train-id 1 --server http://10.4.0.227:5000 --timeout 10
```

## What Was Fixed

| Issue | File | Lines | Change |
|-------|------|-------|--------|
| NoneType error | `train_controller_hw_ui.py` | 123, 299, 90 | Use `or` operator for None handling |
| NoneType error | `train_controller_hardware.py` | 230 | Use `or` operator for None handling |
| Station default | `train_api_server.py` | 146, 235, 352, 428 | Changed "Right" → "" |
| Flat fields | `train_api_server.py` | 386-389, 178-181 | Added auto-cleanup logic |

## Files Modified (Total: 3)

1. ✅ `train_controller/api/train_api_server.py` - Fixed defaults and added cleanup
2. ✅ `train_controller/ui/train_controller_hw_ui.py` - Fixed None handling (4 places)
3. ✅ `train_controller/train_controller_hardware.py` - Fixed None handling (1 place)

## Automatic Maintenance

The server now automatically:
- ✅ Cleans up flat fields every 500ms
- ✅ Ensures all fields have proper defaults
- ✅ Uses empty string for station_side (not "Right")
- ✅ Preserves nested inputs/outputs structure

**Phase 1 Status: Complete with bug fixes ✅**

Ready for Phase 2 when you are!

