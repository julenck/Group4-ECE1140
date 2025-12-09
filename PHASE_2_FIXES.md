# Phase 2 API Fixes - Respecting Module Boundaries

## 🎯 Overview

Based on the verified architecture, Phase 2 API clients had boundary violations. This document details all fixes needed.

---

## 🚨 Issues Found & Fixes

### Issue 1: CTC API Client - Boundary Violation

**Problem:**
- `send_command(train_id, speed, authority)` writes directly to `train_states.json`
- Server endpoint `/api/ctc/train/<id>/command` (line 575-610 in train_api_server.py) writes to train_states.json
- **Violation:** CTC should ONLY communicate with Wayside, not directly to trains!

**Correct Flow:**
```
CTC → ctc_track_controller.json → Wayside → wayside_to_train.json → Train Model
```

**Fix:**
1. **CTC API Client** should write commands to `ctc_track_controller.json` via server
2. **Server endpoint** should be `/api/ctc/commands` (not `/api/ctc/train/<id>/command`)
3. Server writes to `ctc_track_controller.json`, NOT `train_states.json`

**New CTC API Client Methods:**
```python
def send_command(self, train_name, speed, authority, active=1):
    """Send command via ctc_track_controller.json (Wayside reads this)"""
    # Writes to ctc_track_controller.json with format:
    # {"Trains": {"Train 1": {"Active": 1, "Suggested Speed": 30, "Suggested Authority": 100}}}
```

---

### Issue 2: Wayside API Client - Wrong Data Source

**Problem:**
- `get_train_positions()` reads from `/api/trains` endpoint which accesses `train_states.json`
- **Violation:** Wayside should read train physics from `train_data.json`, not train controller state!

**Correct Flow:**
```
Train Model → train_data.json → Wayside (reads velocities)
```

**Fix:**
1. **Wayside API Client** `get_train_positions()` should read from `train_data.json` via server
2. **Server endpoint** should be `/api/train_model/physics` (reads train_data.json)
3. Update field mapping: `train_data.json` uses different structure than `train_states.json`

**Fixed Wayside API Client Methods:**
```python
def get_train_physics(self):
    """Get train physics from train_data.json (Train Model writes this)"""
    # Reads from train_data.json:
    # {"train_1": {"outputs": {"velocity_mph": 45.0, ...}}}
```

---

### Issue 3: Server Endpoints - Don't Respect Boundaries

**Problems:**
1. `/api/ctc/train/<id>/command` writes to `train_states.json` (WRONG!)
2. Missing endpoints for proper module communication
3. Endpoints access wrong files for their module

**Fixes Needed:**

#### New/Fixed CTC Endpoints:
```python
# OLD (WRONG):
POST /api/ctc/train/<id>/command  # Writes to train_states.json ❌

# NEW (CORRECT):
POST /api/ctc/commands             # Writes to ctc_track_controller.json ✅
GET  /api/ctc/status              # Reads from ctc_track_controller.json ✅
```

#### New/Fixed Wayside Endpoints:
```python
# OLD (WRONG):
GET /api/trains                    # Reads train_states.json ❌

# NEW (CORRECT):
GET  /api/wayside/ctc_commands    # Reads ctc_track_controller.json ✅
POST /api/wayside/train_status    # Writes to ctc_track_controller.json (position) ✅
GET  /api/wayside/train_physics   # Reads train_data.json (velocities) ✅
POST /api/wayside/train_commands  # Writes to wayside_to_train.json ✅
```

#### New/Fixed Train Model Endpoints:
```python
GET  /api/train_model/<id>/commands      # Reads wayside_to_train.json ✅
GET  /api/train_model/<id>/control       # Reads train_states.json (outputs) ✅
POST /api/train_model/<id>/physics       # Writes to train_data.json ✅
POST /api/train_model/<id>/sensors       # Writes to train_states.json (inputs) ✅
```

#### Train Controller Endpoints (Keep existing, already correct):
```python
GET  /api/train_controller/<id>/state    # Reads train_states.json ✅
POST /api/train_controller/<id>/outputs  # Writes train_states.json (outputs) ✅
```

---

## 📝 Implementation Plan

### Step 1: Fix Server Endpoints (Priority: HIGH)
- [ ] Remove/deprecate `/api/ctc/train/<id>/command`
- [ ] Add `/api/ctc/commands` (writes to ctc_track_controller.json)
- [ ] Add `/api/wayside/train_physics` (reads train_data.json)
- [ ] Add `/api/wayside/ctc_commands` (reads ctc_track_controller.json)
- [ ] Add `/api/wayside/train_commands` (writes wayside_to_train.json)
- [ ] Add `/api/train_model/<id>/commands` (reads wayside_to_train.json)

### Step 2: Fix CTC API Client
- [ ] Update `send_command()` to use new `/api/ctc/commands` endpoint
- [ ] Update data format to match ctc_track_controller.json structure
- [ ] Update `get_trains()` to read from ctc_data.json (keep as is)

### Step 3: Fix Wayside API Client
- [ ] Update `get_train_positions()` to use `/api/wayside/train_physics`
- [ ] Fix field mapping (velocity_mph from train_data.json outputs)
- [ ] Update `get_ctc_commands()` to use `/api/wayside/ctc_commands`
- [ ] Update `update_train_commands()` to use `/api/wayside/train_commands`

### Step 4: Fix Train Model API Client
- [ ] Add `get_commands()` to read from wayside_to_train.json
- [ ] Split `update_physics()` to write to train_data.json
- [ ] Add `update_sensors()` to write to train_states.json inputs
- [ ] Keep `get_control()` to read from train_states.json outputs

### Step 5: Update Documentation
- [ ] Update PHASE_2_COMPLETE.md with corrections
- [ ] Add PHASE_2_FIXES.md (this file) to document
- [ ] Update endpoint examples with correct usage

---

## 🔄 File Access Matrix (CORRECTED)

| API Client | Endpoint | Server Accesses | Module Boundary |
|------------|----------|-----------------|-----------------|
| **CTC** | POST /api/ctc/commands | ctc_track_controller.json (W) | ✅ Correct |
| **CTC** | GET /api/ctc/status | ctc_track_controller.json (R) | ✅ Correct |
| **Wayside** | GET /api/wayside/ctc_commands | ctc_track_controller.json (R) | ✅ Correct |
| **Wayside** | POST /api/wayside/train_status | ctc_track_controller.json (W) | ✅ Correct |
| **Wayside** | GET /api/wayside/train_physics | train_data.json (R) | ✅ Correct |
| **Wayside** | POST /api/wayside/train_commands | wayside_to_train.json (W) | ✅ Correct |
| **Train Model** | GET /api/train_model/<id>/commands | wayside_to_train.json (R) | ✅ Correct |
| **Train Model** | POST /api/train_model/<id>/physics | train_data.json (W) | ✅ Correct |
| **Train Model** | POST /api/train_model/<id>/sensors | train_states.json inputs (W) | ✅ Correct |
| **Train Model** | GET /api/train_model/<id>/control | train_states.json outputs (R) | ✅ Correct |
| **Train Controller** | GET /api/train_controller/<id>/state | train_states.json (R) | ✅ Correct |
| **Train Controller** | POST /api/train_controller/<id>/outputs | train_states.json outputs (W) | ✅ Correct |

---

## ✅ Success Criteria

After fixes:
- [ ] CTC API Client only interacts with ctc_track_controller.json (via server)
- [ ] Wayside API Client reads train physics from train_data.json (via server)
- [ ] Wayside API Client reads CTC commands from ctc_track_controller.json (via server)
- [ ] Train Model API Client reads from wayside_to_train.json (via server)
- [ ] No module directly accesses another module's exclusive files
- [ ] All API client tests pass with correct data flow

---

## 📊 Status

- [x] Analysis complete
- [x] Architecture verified
- [x] Fix plan documented
- [ ] Server endpoints fixed
- [ ] API clients fixed
- [ ] Tests updated
- [ ] Documentation updated

**Next Step:** Implement server endpoint fixes

