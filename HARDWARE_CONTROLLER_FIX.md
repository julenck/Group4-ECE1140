# Hardware Controller Input/Output Fix

## Problem
The hardware train controller (`train_controller_hw_ui.py`) wasn't properly reading inputs from and writing outputs to the Train Model when running in remote mode (Raspberry Pi connected to server).

## Root Cause
The REST API server (`train_api_server.py`) was only syncing data **one way**:
- ✅ Train Model → train_data.json → server → train_states.json → Controller (WORKING)
- ❌ Controller → train_states.json → server → train_data.json → Train Model (MISSING!)

Controllers could read train state but their outputs (like `power_command`) weren't being written back to `train_data.json` where the Train Model reads from.

## Solution

### 1. Fixed REST API Server Bidirectional Sync

**File**: `train_controller/api/train_api_server.py`

**Added** `sync_states_to_train_data()` function that writes controller outputs back to train_data.json:
- `power_command` (most important!)
- `service_brake`
- `emergency_brake`
- `left_door` / `right_door`
- `interior_lights` / `exterior_lights`
- `set_temperature`

**Modified** `sync_train_data_to_states()` to call the new reverse sync function every 500ms.

**Modified** `update_train_state()` POST endpoint to immediately sync outputs to train_data.json (no waiting).

### 2. Updated Hardware Controller Comments

**File**: `train_controller/ui/train_controller_hw_ui.py`

**Clarified** that in remote mode, the REST API client automatically fetches state from server (no need to call `update_from_train_data()`).

## Data Flow (Fixed)

### Train Model → Controller (Inputs)
```
Train Model
    ↓ (writes outputs to)
train_data.json
    ↓ (server syncs every 500ms)
train_states.json
    ↓ (REST API GET request)
Controller (Raspberry Pi)
```

### Controller → Train Model (Outputs)
```
Controller (Raspberry Pi)
    ↓ (REST API POST request)
train_states.json
    ↓ (server syncs immediately)
train_data.json
    ↓ (Train Model reads from)
Train Model
```

## File Structure

```
Train_Model/
├── train_data.json                    ← Train Model reads/writes here

train_controller/
├── data/
│   └── train_states.json              ← Server syncs to/from this
└── api/
    ├── train_api_server.py            ← Server (FIXED - bidirectional sync)
    ├── train_controller_api.py        ← Local API (file-based)
    └── train_controller_api_client.py ← Remote API (REST client)
```

## Testing

### Before Fix:
- ❌ Hardware controller sends `power_command=5000`
- ❌ Train Model never receives it (reads 0 from train_data.json)
- ❌ Train doesn't move

### After Fix:
- ✅ Hardware controller sends `power_command=5000` via REST API
- ✅ Server writes to train_states.json
- ✅ Server immediately syncs to train_data.json
- ✅ Train Model reads `power_command=5000`
- ✅ Train accelerates!

## How to Test

**Terminal 1 (Start Server):**
```bash
cd C:\Projects\Group4-ECE1140\train_controller
python start_server.py
```

**Terminal 2 (Start System):**
```bash
cd C:\Projects\Group4-ECE1140
python combine_ctc_wayside_test.py
```

**On Raspberry Pi (or PC for local testing):**
```bash
cd ~/Group4-ECE1140/train_controller/ui
python3 train_controller_hw_ui.py --train-id 1 --server http://<laptop-ip>:5000
```

Watch the Train Model UI - the train should now respond to controller inputs!

## Changes Summary

| File | Lines Changed | Purpose |
|------|--------------|---------|
| `train_api_server.py` | ~40 lines added | Added bidirectional sync + immediate output sync |
| `train_controller_hw_ui.py` | ~5 lines changed | Clarified remote mode comments |

## Server Console Output (After Fix)

You should see:
```
[Server] Bidirectional sync thread started (500ms interval)
[Server] Syncing train_data.json ↔ train_states.json
[Server] Train 1 state updated: ['power_command']
[Server] Train 1 state updated: ['driver_velocity']
```

The key indicator is seeing "state updated" messages when the controller makes changes.

## Troubleshooting

**Issue**: Train still not responding to controller

**Check**:
1. Server is running and sync thread started
2. Controller successfully connects (check for "✓ Connected to server" message)
3. Server shows "Train X state updated" when controller changes values
4. train_data.json file is being updated (check timestamps)

**Debug**:
```bash
# Watch train_data.json for changes
watch -n 1 cat Train_Model/train_data.json

# Check server logs for sync messages
# Should see updates every 500ms when data changes
```

## Notes

- The sync runs every 500ms (matching the UI update rate)
- Controller outputs are synced **immediately** on POST (no 500ms delay)
- The fix works for both local mode (file-based) and remote mode (REST API)
- Software controller already worked correctly (uses local file API directly)

---

**Status**: ✅ **FIXED** - Hardware controller now reads inputs and writes outputs correctly in both local and remote modes!

