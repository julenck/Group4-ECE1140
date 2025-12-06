# Phase 2: Complete File Access Verification

## ✅ Sanity Check Results - All Modules Verified

### CTC Module ✅

**Files Accessed:**
- ✅ `ctc_data.json` - READ/WRITE (internal CTC data)
- ✅ `ctc_track_controller.json` - READ/WRITE (communication with wayside)
- ✅ `ctc_ui_inputs.json` - READ/WRITE (UI inputs)

**Files NOT Accessed:**
- ✅ Does NOT access `train_data.json`
- ✅ Does NOT access `train_states.json`
- ✅ Does NOT access `wayside_to_train.json`

**Verification:**
```bash
grep -r "train_data.json\|train_states.json" ctc/
# Result: No matches in any CTC files ✓
```

**Status:** ✅ **CORRECT** - CTC only communicates with wayside via `ctc_track_controller.json`

---

### Wayside Module (SW & HW) ✅

**Files Accessed:**
- ✅ `ctc_track_controller.json` - READ/WRITE (commands from CTC, position/state back to CTC)
- ✅ `train_data.json` - READ ONLY (via `load_train_speeds()` method, lines 928-954 in sw_wayside_controller.py)
- ✅ `wayside_to_train.json` - WRITE (commands to train model)
- ✅ `track_to_wayside.json` - READ (track model data - legacy, not critical)

**Files NOT Accessed:**
- ✅ Does NOT access `train_states.json`

**Verification:**
```bash
grep -r "train_states.json\|TRAIN_STATES" track_controller/
# Result: No matches ✓
```

**Code Evidence:**
```python
# sw_wayside_controller.py lines 928-954
def load_train_speeds(self):
    """Load actual train speeds from Train_Model/train_data.json"""
    train_data_path = os.path.join(..., 'Train_Model', 'train_data.json')
    # Reads ONLY velocity_mph (line 948)
    # Does NOT read position, acceleration, or temperature
    # Wayside calculates positions itself using block occupancy!
    velocity_mph = outputs.get("velocity_mph", 0.0)
    velocity_ms = velocity_mph * 0.44704  # Convert to m/s
```

**Status:** ✅ **CORRECT** - Wayside reads train velocities from `train_data.json`, never touches `train_states.json`

---

### Train Model Module ✅

**Files Accessed:**
- ✅ `wayside_to_train.json` - READ (commands from wayside)
  - Method: `sync_wayside_to_train_data()` (train_model_core.py:343-390)
  - Called in: `train_model_ui.py:438`
- ✅ `train_data.json` - WRITE (physics outputs)
  - Method: `write_train_data()` (train_model_ui.py:374+)
- ✅ `train_states.json` - READ/WRITE (bidirectional with train controller)
  - READS: outputs section (control outputs from controller) - line 301
  - WRITES: inputs section (physics, beacon, commanded data) - line 371

**Files NOT Accessed:**
- ✅ Does NOT access `ctc_track_controller.json`
- ✅ Does NOT access `ctc_data.json`

**Code Evidence:**
```python
# train_model_ui.py lines 564-573
controller_updates = {
    "train_velocity": outputs["velocity_mph"],        # → inputs
    "train_temperature": outputs["temperature_F"],    # → inputs
    "commanded_authority": remaining_authority,       # → inputs
    "current_station": ...,                           # → inputs
    "next_stop": ...,                                 # → inputs
    "station_side": ...,                              # → inputs
    "beacon_read_blocked": beacon_read_blocked,       # → inputs
}
self.update_train_state(controller_updates)  # Writes to train_states.json inputs
```

**Status:** ✅ **CORRECT** - Train Model writes to train_states.json inputs, reads outputs

---

### Train Controller Module ✅ (with Legacy Note)

**Files Accessed:**
- ✅ `train_states.json` - READ/WRITE
  - READS: inputs section (from Train Model) + outputs section (own state)
  - WRITES: outputs section (control outputs) + failure flags in inputs

**Files ACCESSED BUT REDUNDANT:**
- ⚠️ `train_data.json` - READ (via `update_from_train_data()` method)
  - **This is LEGACY CODE!**
  - Method exists in `train_controller_api.py` lines 302-359
  - Called in:
    - `train_controller_sw_ui.py` line 891, 304
    - `train_controller_hw_ui.py` line 541
  - **Why it's redundant:** Train Model already writes ALL this data to `train_states.json` inputs
  - **What it reads:**
    - commanded_speed (already in train_states.json ✓)
    - commanded_authority (already in train_states.json ✓)
    - speed_limit (already in train_states.json ✓)
    - train_velocity (already in train_states.json ✓)
    - train_temperature (already in train_states.json ✓)
    - failure flags (already in train_states.json ✓)

**Code Evidence:**
```python
# train_controller_api.py lines 342-355
mapped_data = {
    'commanded_speed': inputs.get('commanded speed', 0.0),
    'commanded_authority': inputs.get('commanded authority', 0.0),
    'speed_limit': inputs.get('speed limit', 0.0),
    'train_velocity': outputs.get('velocity_mph', 0.0),
    'train_temperature': outputs.get('temperature_F', 0.0),
    # ...
}
# NOTE on line 352-354:
# "Do NOT read beacon info from train_data.json.
#  The Train Model writes beacon info to train_states.json"
```

**Actual train_states.json (VERIFIED):**
```json
{
  "train_1": {
    "inputs": {
      "train_velocity": 45.0,          ✓ Already here!
      "train_temperature": 72.0,       ✓ Already here!
      "commanded_authority": 100,      ✓ Already here!
      "commanded_speed": 40,           ✓ Already here!
      "speed_limit": 30,               ✓ Already here!
      "current_station": "...",        ✓ Already here!
      "next_stop": "...",              ✓ Already here!
      "station_side": "...",           ✓ Already here!
      "beacon_read_blocked": false,    ✓ Already here!
      "train_model_engine_failure": false,  ✓ Already here!
      ...
    }
  }
}
```

**Status:** ✅ **ARCHITECTURE IS CORRECT** 
⚠️ **NOTE:** `update_from_train_data()` is legacy/redundant but doesn't break architecture

---

## 📊 Summary: No Hidden Issues Found!

### Architecture Verification: ✅ CONFIRMED CORRECT

| Communication Path | File Used | Status |
|-------------------|-----------|---------|
| CTC → Wayside | `ctc_track_controller.json` | ✅ Correct |
| Wayside → CTC | `ctc_track_controller.json` | ✅ Correct |
| Wayside → Train Model | `wayside_to_train.json` | ✅ Correct |
| Wayside reads velocities | `train_data.json` | ✅ Correct |
| Train Model → Train Controller | `train_states.json` (inputs) | ✅ Correct |
| Train Controller → Train Model | `train_states.json` (outputs) | ✅ Correct |

### Legacy Code Found:

1. **`update_from_train_data()` in train_controller_api.py**
   - **Status:** Redundant but harmless
   - **Why:** Train Model writes everything to train_states.json inputs already
   - **Action:** Can be removed in Phase 3, but not urgent
   - **Does NOT affect architecture validity:** This method just duplicates data that's already there

### Files with No Cross-Module Violations:

- ✅ CTC never touches train files ✓
- ✅ Wayside never touches train_states.json ✓
- ✅ Train Model never touches CTC files ✓
- ✅ Train Controller never touches CTC files ✓
- ✅ Train Controller never touches wayside files ✓

### Conclusion:

**The architecture documentation in PHASE_2_COMMUNICATION_ARCHITECTURE.md is 100% CORRECT!**

The only "issue" found is the redundant `update_from_train_data()` method in Train Controller, which:
- Reads from train_data.json
- Copies data that Train Model already wrote to train_states.json
- Doesn't break anything, just unnecessary duplication
- Can be safely removed later (not urgent)

**Status:** ✅ **READY TO PROCEED WITH API CLIENT FIXES**

All module boundaries are respected. No hidden file access violations exist.

