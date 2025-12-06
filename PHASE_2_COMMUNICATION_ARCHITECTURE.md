# Phase 2: Complete Communication Architecture Analysis

## 📋 ACTUAL Communication Flow (From Code Analysis)

### Files Used for Inter-Module Communication:

1. **`ctc_track_controller.json`** - CTC ↔ Wayside (BIDIRECTIONAL)
   - CTC WRITES: `Active`, `Suggested Speed`, `Suggested Authority`
   - CTC READS: `Train Position`, `Train State` (written by wayside)
   - Wayside READS: Commands from CTC
   - Wayside WRITES: `Train Position`, `Train State`, `Active` status back

2. **`wayside_to_train.json`** - Wayside → Train Model (ONE-WAY)
   - Wayside WRITES: `Commanded Speed`, `Commanded Authority`, `Beacon` data
   - Train Model READS: Commands from wayside

3. **`train_data.json`** - Train Model internal file (SINGLE EXTERNAL READER)
   - Train Model WRITES: `velocity_mph`, `position`, `acceleration`, `temperature_F`, etc.
   - Wayside READS: Train velocities (via `load_train_speeds()` method)
   - **Train Controller does NOT read this file!**

4. **`train_states.json`** - Train Model ↔ Train Controller (BIDIRECTIONAL with INPUTS/OUTPUTS structure)
   ```json
   {
     "train_1": {
       "inputs": {     // Train Model WRITES here
         "commanded_speed": ...,
         "commanded_authority": ...,
         "speed_limit": ...,
         "train_velocity": ...,
         "train_temperature": ...,
         "current_station": ...,
         "next_stop": ...,
         "station_side": ...,
         "beacon_read_blocked": ...,
         "train_model_engine_failure": ...,
         "train_model_signal_failure": ...,
         "train_model_brake_failure": ...,
         "train_controller_engine_failure": ...,  // Train Controller also writes here
         "train_controller_signal_failure": ...,
         "train_controller_brake_failure": ...
       },
       "outputs": {    // Train Controller WRITES here
         "power_command": ...,
         "service_brake": ...,
         "emergency_brake": ...,
         "right_door": ...,
         "left_door": ...,
         "interior_lights": ...,
         "exterior_lights": ...,
         "set_temperature": ...,
         etc.
       }
     }
   }
   ```
   - Train Controller READS: Both inputs and outputs sections
   - Train Controller WRITES: outputs section (+ its own failure flags in inputs)
   - Train Model READS: outputs section
   - Train Model WRITES: inputs section (all sensor/beacon/physics data)

---

## 🔄 Complete Communication Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     COMPLETE SYSTEM FLOW                            │
└─────────────────────────────────────────────────────────────────────┘

CTC ←────────────→ ctc_track_controller.json ←────────────→ Wayside
(writes commands)         (R/W)                    (writes position)
                                                          │
                                                          │ reads velocity
                                                          ↓
                                                   train_data.json ◄───┐
                                                   (Train Model         │
                                                    internal file)      │
                                                          ↑              │
                         wayside_to_train.json ──────► Train Model ────┘
                         (Wayside writes                   │
                          commands)                        │ writes inputs
                                                          ↓
                                             train_states.json
                                             ┌─────────────────┐
                                             │ inputs section  │ ← Train Model writes
                                             │ outputs section │ ← Train Controller writes
                                             └─────────────────┘
                                                    ↕
                                           Train Controller
                                           (reads inputs + outputs)
                                           (writes outputs)
                                           
LEGEND:
- train_data.json: Train Model's internal physics file (Wayside reads velocity)
- train_states.json: Bidirectional Train Model ↔ Train Controller communication
  - inputs: Train Model → Train Controller (physics, beacon, commanded speed/auth)
  - outputs: Train Controller → Train Model (power, brakes, doors, lights)
```

---

## 📁 File Access Matrix

| Module | File | Operation | What Data |
|--------|------|-----------|-----------|
| **CTC** | `ctc_track_controller.json` | READ/WRITE | Commands: Active, Suggested Speed, Authority<br>Reads: Train Position, Train State |
| **Wayside** | `ctc_track_controller.json` | READ/WRITE | Reads: CTC commands<br>Writes: Train Position, Train State |
| **Wayside** | `train_data.json` | READ | Train velocities ONLY (not positions - wayside calculates those!) |
| **Wayside** | `wayside_to_train.json` | WRITE | Commanded Speed/Authority to trains |
| **Train Model** | `wayside_to_train.json` | READ | Commanded Speed/Authority from wayside |
| **Train Model** | `train_states.json` (inputs) | WRITE | Beacon data, sensor data, physics (velocity, temp), commanded speed/auth |
| **Train Model** | `train_states.json` (outputs) | READ | Control outputs (power, brakes, doors) from Train Controller |
| **Train Model** | `train_data.json` | WRITE | Physics outputs (velocity, position, temperature) - Internal file |
| **Train Controller** | `train_states.json` (inputs & outputs) | READ/WRITE | Reads: inputs (from Train Model) + outputs (own state)<br>Writes: outputs (control commands) + failure flags in inputs |
| **Train Controller** | ~~`train_data.json`~~ | ~~READ~~ | **NOT USED** - Legacy code, Train Model writes to train_states.json instead |

---

## ⚠️ **Legacy Code Note**

### `update_from_train_data()` Method is REDUNDANT

The method `train_controller_api.update_from_train_data()` exists in the codebase but is **legacy code**:

**What it does:** Reads from `train_data.json` and copies data to `train_states.json`

**Why it's redundant:** Train Model already writes ALL necessary data to `train_states.json` inputs section, including:
- commanded_speed ✓
- commanded_authority ✓  
- speed_limit ✓
- train_velocity ✓
- train_temperature ✓
- Failure flags ✓

**Current status:** Still called in SW and HW controller UIs (lines 891, 304, 541) but could be removed

**Recommendation:** In Phase 3, remove calls to `update_from_train_data()` since Train Model handles this communication via train_states.json

---

## 🚨 VIOLATIONS in Current API Clients

### ❌ **Violation 1: CTC API Client** 
**Problem:** `send_command(train_id, speed, authority)` writes directly to `train_states.json` (line 587-606 in train_api_server.py)

**Why It's Wrong:** CTC should ONLY communicate with Wayside via `ctc_track_controller.json`, not directly to train states!

**Should Be:** Write to `ctc_track_controller.json` with CTC commands that wayside reads

---

### ❌ **Violation 2: Wayside API Client**
**Problem:** `get_train_positions()` reads from `/api/trains` endpoint which reads `train_states.json`

**Why It's Wrong:** Wayside should read train positions from `train_data.json` (train model physics), not train controller state!

**Should Be:** Read from `train_data.json` to get train velocities and positions

---

### ❌ **Violation 3: Train Model API Client**
**Problem:** Structure may allow direct communication with non-adjacent modules

**Should Be:** Only communicate with wayside (for commands) and train controller (for control outputs)

---

### ❌ **Violation 4: Server Endpoints Don't Respect Boundaries**
**Problem:** Server has endpoints like `/api/ctc/train/<id>/command` that write to `train_states.json`

**Why It's Wrong:** This bypasses the proper wayside layer

**Should Be:** CTC endpoints should only interact with wayside-related files

---

## ✅ CORRECT REST API Architecture

### What the REST API Server Should Do:

1. **Be the ONLY process that reads/writes JSON files**
2. **Provide module-specific endpoints that respect communication boundaries**
3. **Act as a "file system proxy" - clients call endpoints, server manipulates correct files**

### Module-Specific Endpoints Needed:

#### CTC Endpoints:
```python
POST /api/ctc/command           # Write to ctc_track_controller.json
GET  /api/ctc/train_status      # Read from ctc_track_controller.json
```

#### Wayside Endpoints:
```python
GET  /api/wayside/ctc_commands  # Read from ctc_track_controller.json
POST /api/wayside/train_status  # Write Train Position to ctc_track_controller.json
GET  /api/wayside/train_physics # Read from train_data.json (velocities)
POST /api/wayside/train_commands # Write to wayside_to_train.json
```

#### Train Model Endpoints:
```python
GET  /api/train_model/<id>/commands      # Read from wayside_to_train.json
GET  /api/train_model/<id>/control       # Read from train_states.json (outputs)
POST /api/train_model/<id>/physics       # Write to train_data.json
POST /api/train_model/<id>/sensors       # Write to train_states.json (inputs)
```

#### Train Controller Endpoints:
```python
GET  /api/train_controller/<id>/state    # Read from train_states.json (inputs + outputs)
POST /api/train_controller/<id>/control  # Write to train_states.json (outputs)
# Note: Train Controller does NOT need train_data.json endpoints!
```

---

## 🔧 What Needs to be Fixed:

1. **Redesign Server Endpoints** to respect module boundaries
2. **Rewrite API Clients** to use correct endpoints
3. **Remove Cross-Boundary Violations** (e.g., CTC → train_states.json)
4. **Add Missing Endpoints** for proper file access patterns
5. **Update Sync Logic** in server to respect communication flow

---

## Next Steps:

1. ✅ Document current architecture (THIS FILE)
2. ⬜ Create corrected server endpoint design
3. ⬜ Rewrite API clients with proper boundaries
4. ⬜ Test that all communication flows work correctly
5. ⬜ Update Phase 2 documentation

**Status:** Architecture analysis COMPLETE. Ready for fixes.

