# Hardware Controller Connection Fix

## Issues Found

### Issue 1: Missing `driver_velocity` Field
**Symptom:** Raspberry Pi terminal showing repeated `Periodic Update Error: 'driver_velocity'`

**Root Cause:** The `train_states.json` file had an incorrect structure with nested `inputs`/`outputs` sections, but was missing the `driver_velocity` field entirely.

**Fix:** Restored proper nested structure with all required fields including `driver_velocity` in the `outputs` section.

### Issue 2: LEDs Not Lighting Up
**Symptom:** Physical buttons on Raspberry Pi detected (console shows "gpiozero Button pressed"), but LEDs don't light up and UI buttons don't change color.

**Root Cause:** The REST API server was returning the nested `inputs`/`outputs` structure directly, but the hardware controller expected a flat structure where all fields are at the top level.

**Fix:** Modified the `get_train_state()` endpoint in `train_api_server.py` to flatten the structure by merging `inputs` and `outputs` before returning to the client.

## Files Modified

### 1. `train_controller/data/train_states.json`
- Restored proper nested structure with `inputs` and `outputs` sections
- Added ALL fields from `train_controller_api.py` defaults
- **Key defaults that match controller API:**
  - `interior_lights: true` (default ON)
  - `exterior_lights: true` (default ON)
  - `kp: null` (must be set through UI)
  - `ki: null` (must be set through UI)
  - `set_temperature: 70.0`

### 2. `train_controller/api/train_api_server.py`

#### Change 1: `get_train_state()` endpoint (Lines 216-235)
**Before:** Returned nested structure directly
```python
if train_key in data:
    return jsonify(data[train_key]), 200
```

**After:** Flattens structure before returning
```python
if train_key in data:
    train_section = data[train_key]
    
    # Flatten the structure: merge inputs and outputs into a single dict
    flat_state = {}
    if "inputs" in train_section:
        flat_state.update(train_section["inputs"])
    if "outputs" in train_section:
        flat_state.update(train_section["outputs"])
    
    flat_state["train_id"] = train_id
    return jsonify(flat_state), 200
```

#### Change 2: `sync_train_data_to_states()` background thread (Lines 103-212)
**Critical Fix:** Sync thread now ensures ALL fields exist with proper defaults, matching `train_controller_api.py` behavior.

**Before:** If `outputs` section was empty `{}`, it stayed empty (causing LED issues)

**After:** Sync thread fills in missing fields with defaults:
```python
# Example: if field is missing, set it to default
if "interior_lights" not in outputs_section:
    outputs_section["interior_lights"] = True  # Default ON
if "exterior_lights" not in outputs_section:
    outputs_section["exterior_lights"] = True  # Default ON
if "kp" not in outputs_section:
    outputs_section["kp"] = None  # Must be set through UI
# ... and so on for all fields
```

This ensures that even if `train_states.json` gets corrupted or has missing fields, the server will automatically restore them with proper defaults on the next sync cycle (500ms).

#### Change 3: `sync_states_to_train_data()` function (Lines 56-101)
- Updated to correctly write controller outputs to `train_data.json` inputs section
- Train Model reads controller outputs as its inputs (power_command, brake states, doors, etc.)

## How It Works Now

### Server File Structure (Correct)
```json
{
  "train_1": {
    "inputs": {
      "commanded_speed": 0.0,
      "train_velocity": 0.0,
      "driver_velocity": 0.0,  // ← This was missing!
      ...
    },
    "outputs": {
      "power_command": 0.0,
      "service_brake": false,
      ...
    }
  }
}
```

### API Response to Raspberry Pi (Flattened)
```json
{
  "train_id": 1,
  "commanded_speed": 0.0,
  "train_velocity": 0.0,
  "driver_velocity": 0.0,    // ← Now accessible!
  "power_command": 0.0,
  "service_brake": false,
  "exterior_lights": true,   // ← LED states now accessible!
  ...
}
```

### Data Flow
1. **Raspberry Pi → Server:** Button press updates state via `POST /api/train/1/state`
2. **Server:** Updates `train_states.json` with proper inputs/outputs categorization
3. **Server → Raspberry Pi:** Periodic `GET /api/train/1/state` returns flattened structure
4. **Hardware Controller:** Reads flat structure, updates LEDs based on state values
5. **LEDs:** Physical LEDs light up when corresponding state is true!

## Testing

Restart both the server and the Raspberry Pi hardware controller:

### On Server (Main PC):
```bash
cd train_controller/api
python train_api_server.py
```

### On Raspberry Pi:
```bash
cd train_controller/ui
python train_controller_hw_ui.py --train-id 1 --server http://10.4.0.227:5000 --timeout 10
```

**Expected Result:**
- No more `'driver_velocity'` errors
- Physical LEDs light up when buttons are pressed
- UI button colors change (red when active, gray when inactive)
- All hardware controls work properly

## Why This Structure?

The nested `inputs`/`outputs` structure in `train_states.json` is important because:

1. **Clear data flow:** Inputs come FROM other systems, outputs go TO other systems
2. **Prevents conflicts:** Server knows which fields to sync in which direction
3. **Matches software controller:** Consistency across both hardware and software modes

The API flattening is necessary because:

1. **Client simplicity:** Raspberry Pi code doesn't need to know about nested structure
2. **Backward compatibility:** Existing controller code expects flat state dictionary
3. **Cleaner access:** `state['driver_velocity']` vs `state['outputs']['driver_velocity']`

