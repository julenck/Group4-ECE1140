# Phase 2 Complete ✅ - API Client Libraries Created & FIXED

## ⚠️ IMPORTANT UPDATE: Phase 2 Architectural Fixes Applied

**Original Phase 2** created API client libraries but had module boundary violations.

**Phase 2 was FIXED** to respect the verified communication architecture.

**📄 Complete Fix Documentation:**
- **`PHASE_2_FIXES_SUMMARY.md`** ← Read this for complete details!
- `PHASE_2_FIXES.md` - Fix plan  
- `PHASE_2_COMMUNICATION_ARCHITECTURE.md` - Verified architecture
- `PHASE_2_FILE_ACCESS_VERIFICATION.md` - Verification results

**Key Fixes:**
- ✅ CTC now communicates via ctc_track_controller.json (not train_states.json)
- ✅ Wayside now reads train physics from train_data.json (not train_states.json)
- ✅ Train Model now reads from wayside_to_train.json
- ✅ All module boundaries respected

---

## What Was Done (Original + Fixes)

Phase 2 focused on creating API client libraries that will allow all system components to communicate with the central REST API server instead of directly reading/writing JSON files.

### API Clients Created (3 files)

#### 2.1 Train Model API Client ✅
**File:** `Train_Model/train_model_api_client.py`

**Class:** `TrainModelAPIClient`

**Methods Implemented:**
- `__init__(train_id, server_url, timeout, max_retries)` - Initialize client with connection test
- `get_inputs()` - Get commanded speed, authority, and controller commands from server
- `update_physics(velocity, position, acceleration, temperature)` - Send physics outputs to server
- `update_passengers(onboard, boarding, disembarking)` - Send passenger data to server
- `update_beacon_data(current_station, next_stop, station_side)` - Send beacon data to server
- `update_failure_modes(engine_failure, signal_failure, brake_failure)` - Send failure mode data to server

**Features:**
- Automatic connection testing on initialization
- Retry logic with configurable max retries
- Request timeout handling
- Local caching for offline resilience
- Detailed error messages and status logging

**Default Configuration:**
- Server URL: `http://localhost:5000`
- Timeout: 5.0 seconds
- Max Retries: 3

#### 2.2 CTC API Client ✅
**File:** `ctc/api/ctc_api_client.py`

**Class:** `CTCAPIClient`

**Methods Implemented:**
- `__init__(server_url, timeout, max_retries)` - Initialize client with connection test
- `get_trains()` - Get all dispatched trains from server
- `dispatch_train(line, station, arrival_time)` - Dispatch new train from CTC
- `send_command(train_id, speed, authority)` - Send speed/authority command to train
- `get_occupancy()` - Get track occupancy array from wayside
- `update_train_position(train_id, block_number)` - Update train position for CTC tracking

**Features:**
- Automatic connection testing on initialization
- Retry logic with configurable max retries
- Request timeout handling
- Local caching for trains and occupancy data
- Returns train ID on successful dispatch
- Detailed error messages and status logging

**Default Configuration:**
- Server URL: `http://localhost:5000`
- Timeout: 5.0 seconds
- Max Retries: 3

#### 2.3 Wayside API Client ✅
**File:** `track_controller/api/wayside_api_client.py`

**Class:** `WaysideAPIClient`

**Methods Implemented:**
- `__init__(wayside_id, server_url, timeout, max_retries)` - Initialize client with connection test
- `get_ctc_commands()` - Get CTC commands (speed, authority, switches) from server
- `update_state(switches, lights, gates, occupancy)` - Update complete wayside state
- `update_switches(switch_positions)` - Update switch positions only
- `update_lights(light_states)` - Update light states only
- `get_train_positions()` - Get train positions in controlled blocks
- `update_occupancy(occupancy)` - Update track occupancy array

**Features:**
- Automatic connection testing on initialization
- Retry logic with configurable max retries
- Request timeout handling
- Local caching for state and train data
- Wayside-specific filtering (wayside_1, wayside_2, etc.)
- Detailed error messages and status logging

**Default Configuration:**
- Server URL: `http://localhost:5000`
- Timeout: 5.0 seconds
- Max Retries: 3

## Common Features Across All Clients

### 1. Robust Error Handling
- Automatic retry with exponential backoff
- Timeout protection
- Graceful degradation with cached data
- Detailed error logging

### 2. Connection Testing
- All clients test connection on initialization
- Clear status messages (✓ success, ⚠ warning, ✗ error)
- Automatic fallback to cached data if server unreachable

### 3. Caching
- Local cache for critical data
- Automatic cache updates on successful requests
- Cache used as fallback when server unreachable

### 4. Configuration
- Configurable server URL (default: localhost:5000)
- Configurable timeout (default: 5 seconds)
- Configurable retry count (default: 3 attempts)

### 5. Testing Support
- Each client has `__main__` test code
- Can be run standalone to test server connectivity
- Example usage included in each file

## Testing the API Clients

### Prerequisites
Make sure the REST API server is running:
```bash
cd train_controller/api
python train_api_server.py
```

### Test Train Model API Client (FIXED - Now Boundary-Respecting)
```bash
cd Train_Model
python train_model_api_client.py
# Or with custom server URL:
python train_model_api_client.py http://192.168.1.100:5000
```

**Expected Output (CORRECTED):**
```
Testing Train Model API Client with server: http://localhost:5000
[Train Model API] ✓ Connected to server: http://localhost:5000
[Train Model API] ✓ Managing Train 1

--- Getting wayside commands (from wayside_to_train.json) ---
Commanded speed: 0 mph
Commanded authority: 0
Current station: N/A
Next station: N/A
# Or if no commands:
No wayside commands available

--- Getting control outputs (from train_states.json outputs) ---
Power command: 0.0 W
Service brake: False
Emergency brake: False
# Or if train doesn't exist:
No control outputs available

--- Updating physics (to train_data.json) ---
Physics update: SUCCESS

--- Updating beacon data (to train_states.json inputs) ---
Beacon update: SUCCESS
```

**What's Different:**
- ✅ Now reads commands from wayside_to_train.json (not train_states directly)
- ✅ Separates wayside commands from train controller outputs
- ✅ Shows correct boundary: Wayside → Train Model → Train Controller

### Test CTC API Client (FIXED - Now Uses CTC-Wayside Boundary)
```bash
cd ctc
python api/ctc_api_client.py
# Or with custom server URL:
python api/ctc_api_client.py http://192.168.1.100:5000
```

**Expected Output (CORRECTED):**
```
Testing CTC API Client with server: http://localhost:5000
[CTC API] ✓ Connected to server: http://localhost:5000

--- Getting all trains ---
Found 5 trains
  Train 1
  Train 2
  Train 3
  Train 4
  Train 5

--- Dispatching a train ---
[CTC API] ✓ Train 'Train 1' dispatched successfully
Dispatched train: Train 1

--- Sending command via CTC → wayside boundary ---
Sending command to Train 1 via ctc_track_controller.json...
Command: SUCCESS

--- Getting status from wayside ---
Status received: 5 trains tracked
  Train 1: Pos=0, Active=1
  Train 2: Pos=0, Active=0
  Train 3: Pos=0, Active=0

--- Getting track occupancy ---
Occupied blocks: [42]...
```

**What's Different:**
- ✅ Commands sent to ctc_track_controller.json (NOT train_states.json)
- ✅ Status read back from wayside shows train positions
- ✅ Uses train names ("Train 1") not numeric IDs
- ✅ Correct boundary: CTC ↔ ctc_track_controller.json ↔ Wayside

### Test Wayside API Client (FIXED - Now Reads from Correct Files)
```bash
cd track_controller
python api/wayside_api_client.py
# Or with custom server URL:
python api/wayside_api_client.py http://192.168.1.100:5000
```

**Expected Output (CORRECTED):**
```
Testing Wayside API Client with server: http://localhost:5000
[Wayside API] ✓ Connected to server: http://localhost:5000
[Wayside API] ✓ Wayside Controller 1

--- Getting CTC commands (from ctc_track_controller.json) ---
Received CTC commands
  5 trains in CTC data
  Keys: ['Trains', 'Block Closure', 'Switch Suggestion']
# Or if no commands:
No CTC commands available

--- Getting train speeds (from train_data.json) ---
Found 1 trains
  Train 1: 45.0 mph
# Or if no trains:
No trains found (train_data.json may be empty)

--- Sending train commands (to wayside_to_train.json) ---
Train command: SUCCESS
  Includes: Speed, Authority, Current Station, Next Station

--- Reporting train status (to ctc_track_controller.json) ---
Status report: SUCCESS

--- Updating switch positions ---
Switch update: SUCCESS

--- Updating light states ---
Light update: SUCCESS
```

**What's Different:**
- ✅ Reads CTC commands from ctc_track_controller.json (boundary-respecting)
- ✅ Reads train SPEEDS ONLY from train_data.json (NOT positions - wayside calculates positions!)
- ✅ Uses correct train_data.json field: velocity_mph from outputs section
- ✅ Demonstrates reporting status back to CTC
- ✅ Demonstrates sending commands to trains (including beacon data)
- ✅ Correct boundaries: CTC ↔ Wayside ↔ Train Model

## Files Created (Total: 3)

1. ✅ `Train_Model/train_model_api_client.py` - 11,885 bytes
2. ✅ `ctc/api/ctc_api_client.py` - 11,306 bytes (created `ctc/api/` directory)
3. ✅ `track_controller/api/wayside_api_client.py` - 15,105 bytes

## Integration with Existing Code

These API clients are designed to be **drop-in replacements** for direct JSON file access:

### Before (Direct File Access):
```python
# OLD CODE - Direct file writes
with open('train_data.json', 'w') as f:
    json.dump(data, f)
```

### After (API Client):
```python
# NEW CODE - API calls
from train_model_api_client import TrainModelAPIClient

api_client = TrainModelAPIClient(train_id=1)
api_client.update_physics(velocity=45.0, position=1000.0, 
                         acceleration=2.5, temperature=72.0)
```

## What's Next: Phase 3

Phase 3 will modify the actual component files to use these API clients:

1. **Train Model** (1 hour)
   - Modify `train_model_core.py`
   - Modify `train_model_ui.py`
   - Modify `train_model_test_ui.py`

2. **CTC** (45 minutes)
   - Modify `ctc_main.py`
   - Modify `ctc_ui.py`
   - Modify `ctc_ui_temp.py`

3. **Track Controller** (45 minutes)
   - Modify `sw_wayside_controller.py`
   - Modify `hw_wayside_controller.py`

## Success Criteria for Phase 2 ✅

- [x] Train Model API Client created with all required methods
- [x] CTC API Client created with all required methods
- [x] Wayside API Client created with all required methods
- [x] All clients have connection testing
- [x] All clients have retry logic and error handling
- [x] All clients have local caching for resilience
- [x] All clients have standalone test code
- [x] No linter errors

**Phase 2 Status: COMPLETE ✅**

Ready to proceed to Phase 3 when you are!

## Known Issues / Design Notes

### CTC Train Dispatch vs Train States

**Issue:** The server currently has two separate train tracking systems:
1. **CTC System** - Uses `ctc_data.json` with train names as keys (e.g., `"Train 1"`)
2. **Train State System** - Uses `train_states.json` with numeric IDs (e.g., `"train_1"`, `"train_2"`)

**Impact:**
- `dispatch_train()` creates entries in `ctc_data.json` 
- `send_command()` requires trains to exist in `train_states.json`
- These aren't automatically synchronized

**Expected Behavior:**
```bash
# When you run the CTC test:
--- Dispatching a train ---
[CTC API] ✓ Train 'Train 1' dispatched successfully
Dispatched train: Train 1                    # ✅ Works

--- Sending command to existing train ---
Command: FAILED (train may not exist...)     # ⚠️  Fails if train not in train_states.json
```

**Resolution:** This will be addressed in Phase 3 when we modify the CTC components to properly integrate with the unified train state system.

## Architecture Overview

```
┌─────────────────────────────────────┐
│       Main Computer                 │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  REST API Server (Port 5000)│   │
│  │  Single Source of Truth     │   │
│  └──────────▲──────────────────┘   │
│             │                       │
│    ┌────────┼────────┬───────┐     │
│    │        │        │       │     │
│  Train   Train     CTC    Wayside  │
│  Model     Ctrl           Ctrl     │
│  API       API     API     API     │
│ Client   Client  Client  Client    │
│   ✅       ✅       ✅       ✅      │
└─────────────────────────────────────┘
         ▲                      ▲
         │                      │
    ┌────┴──────┐        ┌──────┴────┐
    │  RPi 1    │        │   RPi 2   │
    │ Hardware  │        │ Hardware  │
    │ Train Ctrl│        │ Wayside   │
    └───────────┘        └───────────┘
```

All API clients are now ready to use! 🎉

## Phase 2 Bug Fixes

### Malformed Train Key Handling (Wayside API)
- **Issue:** `get_train_speeds()` had unprotected `int()` conversions that could crash on malformed keys
- **Fix:** Added try-except blocks to catch `ValueError` and `IndexError`
- **Impact:** Wayside API now gracefully skips malformed train keys and logs warnings
- **Documentation:** See `PHASE_2_BUGFIX_MALFORMED_KEYS.md` for details

### train_data.json Structure Cleanup
- **Issue:** File had legacy root-level train data mixed with named trains
- **Fix:** Removed root-level specs/inputs/outputs, keeping only named trains (train_1 through train_5)
- **Impact:** Clean, consistent structure for all API clients to consume

