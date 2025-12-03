# System Architecture Analysis and Solution

## Current Problem

Your system has **inconsistent communication patterns** causing JSON synchronization issues:

### ✅ Train Controller - REST API (Working)
- **Server**: `train_api_server.py` on main computer
- **Communication**: REST API over HTTP
- **Files**: `train_states.json` (centralized on server)
- **Status**: Already implemented correctly!

### ❌ Track Controller (Wayside) - Direct File I/O (Problem)
- **Communication**: Direct JSON file read/write
- **Files**: 
  - `ctc_track_controller.json` (from CTC)
  - `track_to_wayside.json` (from Track Model)
  
  - `wayside_to_train.json` (to trains)
- **Status**: NEEDS REST API integration

### ❌ CTC - Direct File I/O (Problem)
- **Communication**: Direct JSON file read/write with file watchers
- **Files**:
  - `ctc_data.json` (internal state)
  - `ctc_track_controller.json` (to wayside)
- **Status**: NEEDS REST API integration

## Why This Causes Problems

### Scenario 1: Raspberry Pi can't access local files
```
Main Computer:             CTC writes → ctc_track_controller.json
Raspberry Pi (Wayside):    Tries to read → FILE NOT FOUND (different filesystem!)
```

### Scenario 2: Race conditions
```
Time 0ms:  CTC reads ctc_track_controller.json
Time 10ms: Wayside reads ctc_track_controller.json
Time 20ms: CTC writes updated data
Time 30ms: Wayside writes updated data → OVERWRITES CTC's changes!
```

### Scenario 3: Stale data
```
Main Computer:  Updates file locally
Raspberry Pi:   Sees old cached version (file system not synced)
Result:         Wayside makes decisions on outdated information
```

## The Solution: Central REST API Server

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    MAIN COMPUTER                            │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         CENTRAL REST API SERVER (Flask)               │  │
│  │                                                        │  │
│  │  Endpoints:                                           │  │
│  │    /api/train/<id>/state        (Train Controller)   │  │
│  │    /api/wayside/<id>/state      (Track Controller)   │  │
│  │    /api/ctc/trains              (CTC)                 │  │
│  │    /api/ctc/dispatch            (CTC)                 │  │
│  │    /api/track_model/blocks      (Track Model)        │  │
│  │                                                        │  │
│  │  Manages ALL JSON files in one place with locks      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐       │
│  │   CTC UI    │  │ Train Model │  │ Train Manager│       │
│  │  (Client)   │  │  (Client)   │  │   (Client)   │       │
│  └─────────────┘  └─────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
         ↑                    ↑                      ↑
         │   HTTP REST API    │                      │
         ├────────────────────┼──────────────────────┤
         │                    │                      │
┌────────┴────────┐  ┌────────┴────────┐  ┌─────────┴────────┐
│  Raspberry Pi 1 │  │  Raspberry Pi 2 │  │  Raspberry Pi N  │
│                 │  │                 │  │                  │
│  Wayside HW     │  │  Wayside HW     │  │  Train HW        │
│  Controller     │  │  Controller     │  │  Controller      │
│  (API Client)   │  │  (API Client)   │  │  (API Client)    │
└─────────────────┘  └─────────────────┘  └──────────────────┘
```

### Benefits
1. ✅ **Single Source of Truth**: All data lives on server
2. ✅ **Thread-Safe**: Server uses locks to prevent conflicts
3. ✅ **Network Transparent**: Raspberry Pis connect via IP address
4. ✅ **No File Conflicts**: Only server writes to files
5. ✅ **Consistent**: All clients use same API pattern
6. ✅ **Testable**: Can run locally or distributed

## Implementation Steps

### Phase 1: Extend REST API Server ✅ (Train Controller Done)
- [x] Train Controller API (already implemented)
- [ ] Add Track Controller (Wayside) endpoints
- [ ] Add CTC endpoints
- [ ] Add Track Model endpoints

### Phase 2: Create API Clients
- [ ] Track Controller API Client (similar to train_controller_api_client.py)
- [ ] CTC API Client
- [ ] Update Track Model to use API client

### Phase 3: Update Track Controller
- [ ] Replace direct JSON file I/O with API client calls
- [ ] Add `--server` flag to wayside UI
- [ ] Test local mode (no server)
- [ ] Test remote mode (with server)

### Phase 4: Update CTC
- [ ] Replace direct JSON file I/O with API client calls
- [ ] Replace file watchers with API polling or WebSockets
- [ ] Add `--server` flag to CTC UI
- [ ] Test integration

### Phase 5: Integration Testing
- [ ] Run server on main computer
- [ ] Connect Track Controller on Raspberry Pi 1
- [ ] Connect Track Controller on Raspberry Pi 2
- [ ] Run CTC, Train Model, Train Manager on main computer
- [ ] Verify all components sync correctly

## Files That Need Changes

### New Files to Create:
1. `api/unified_api_server.py` - Extended REST API with all endpoints
2. `track_controller/api/wayside_api_client.py` - Client for Raspberry Pis
3. `ctc/api/ctc_api_client.py` - Client for CTC
4. `start_unified_server.py` - Main server startup script

### Files to Modify:
1. `track_controller/New_SW_Code/sw_wayside_controller.py` - Use API instead of files
2. `track_controller/New_SW_Code/sw_wayside_controller_ui.py` - Add server flag
3. `ctc/ctc_main_temp.py` - Use API instead of files
4. `ctc/ctc_ui_temp.py` - Use API instead of files
5. `Train_Model/train_model_core.py` - Use API instead of some files
6. `combine_ctc_wayside_test.py` - Start server first

## Next Steps

Would you like me to:
1. **Implement the unified REST API server** with Track Controller and CTC endpoints?
2. **Create the API clients** for Track Controller and CTC?
3. **Update Track Controller** to use the API?
4. **Update CTC** to use the API?

I recommend doing them in order (1 → 2 → 3 → 4) for a smooth migration.

