# REST API Refactor - Complete Implementation Plan

## Overview
Convert all system components to communicate through a central REST API server instead of direct JSON file writes. This eliminates race conditions and enables proper multi-computer/Raspberry Pi deployment.

## Current Architecture (Problematic)
```
┌─────────────────┐
│  Main Computer  │
├─────────────────┤
│ Train Manager   │──┐
│ Train Model     │  ├──► train_data.json ◄──┐ (RACE CONDITIONS!)
│ CTC             │  │                         │
│ Track Controller│  └──► train_states.json ◄─┤
│                 │                            │
│ REST API Server │────────────────────────────┘
└─────────────────┘         ▲
         ▲                  │
         │                  │
    ┌────┴────┐        ┌────┴────┐
    │  RPi 1  │        │  RPi 2  │
    │ Train   │        │ Track   │
    │ HW Ctrl │        │ HW Ctrl │
    └─────────┘        └─────────┘
```

## Target Architecture (Correct)
```
┌─────────────────────────────────┐
│       Main Computer             │
├─────────────────────────────────┤
│                                 │
│  ┌─────────────────────────┐   │
│  │   REST API Server       │   │ ← SINGLE SOURCE OF TRUTH
│  │   (Port 5000)           │   │
│  │                         │   │
│  │  Manages:               │   │
│  │  - Train States         │   │
│  │  - Train Physics        │   │
│  │  - CTC Data             │   │
│  │  - Wayside State        │   │
│  │  - All JSON Files       │   │
│  └─────────────────────────┘   │
│            ▲                    │
│            │ HTTP/REST Only     │
│    ┌───────┼───────┬────────┐  │
│    │       │       │        │  │
│ Train   Train   CTC      Track │
│ Manager Model         Controller│
│  (API)   (API)  (API)    (API) │
└────────────────────────────────┘
         ▲       ▲
         │       │
    ┌────┴───┐ ┌┴────────┐
    │ RPi 1  │ │  RPi 2  │
    │ Train  │ │  Track  │
    │Hardware│ │ Hardware│
    └────────┘ └─────────┘
    (Already using API!)
```

## Implementation Phases

### Phase 1: Extend REST API Server (30-45 min)
**File:** `train_controller/api/train_api_server.py`

Add new endpoint groups:

#### 1.1 Train Physics Endpoints
```python
@app.route('/api/train/<int:train_id>/physics', methods=['GET'])
def get_train_physics(train_id):
    """Get train physics data (velocity, position, acceleration, etc.)"""
    
@app.route('/api/train/<int:train_id>/physics', methods=['POST'])
def update_train_physics(train_id):
    """Update train physics outputs from Train Model"""
```

#### 1.2 CTC Endpoints
```python
@app.route('/api/ctc/trains', methods=['GET'])
def get_all_ctc_trains():
    """Get all CTC train dispatch data"""
    
@app.route('/api/ctc/train/<int:train_id>/command', methods=['POST'])
def send_ctc_command(train_id):
    """Send CTC command (speed, authority) to train"""
    
@app.route('/api/ctc/dispatch', methods=['POST'])
def dispatch_train():
    """Dispatch new train from CTC"""
    
@app.route('/api/ctc/occupancy', methods=['GET'])
def get_track_occupancy():
    """Get track occupancy from wayside"""
```

#### 1.3 Wayside/Track Controller Endpoints
```python
@app.route('/api/wayside/state', methods=['GET'])
def get_wayside_state():
    """Get all wayside controller state"""
    
@app.route('/api/wayside/state', methods=['POST'])
def update_wayside_state():
    """Update wayside state (switches, lights, gates, occupancy)"""
    
@app.route('/api/wayside/switches', methods=['POST'])
def update_switches():
    """Update switch positions"""
    
@app.route('/api/wayside/lights', methods=['POST'])
def update_lights():
    """Update light states"""
```

### Phase 2: Create API Client Libraries (45 min - 1 hour)

#### 2.1 Train Model API Client
**File:** `Train_Model/train_model_api_client.py`

```python
class TrainModelAPIClient:
    def __init__(self, train_id, server_url="http://localhost:5000"):
        self.train_id = train_id
        self.server_url = server_url
        
    def get_inputs(self):
        """Get commanded speed, authority, etc. from server"""
        
    def update_physics(self, velocity, position, acceleration, temperature):
        """Send physics outputs to server"""
        
    def update_passengers(self, onboard, boarding, disembarking):
        """Send passenger data to server"""
```

#### 2.2 CTC API Client
**File:** `ctc/api/ctc_api_client.py`

```python
class CTCAPIClient:
    def __init__(self, server_url="http://localhost:5000"):
        self.server_url = server_url
        
    def get_trains(self):
        """Get all dispatched trains"""
        
    def dispatch_train(self, line, station, arrival_time):
        """Dispatch new train"""
        
    def send_command(self, train_id, speed, authority):
        """Send speed/authority command to train"""
        
    def get_occupancy(self):
        """Get track occupancy array"""
```

#### 2.3 Wayside API Client
**File:** `track_controller/api/wayside_api_client.py`

```python
class WaysideAPIClient:
    def __init__(self, wayside_id, server_url="http://localhost:5000"):
        self.wayside_id = wayside_id
        self.server_url = server_url
        
    def get_ctc_commands(self):
        """Get CTC commands (speed, authority, switches)"""
        
    def update_state(self, switches, lights, gates, occupancy):
        """Update wayside state"""
        
    def get_train_positions(self):
        """Get train positions in controlled blocks"""
```

### Phase 3: Modify Components (2-3 hours)

#### 3.1 Train Model (1 hour)
**Files to modify:**
- `Train_Model/train_model_core.py` - Replace `safe_write_json(train_data.json)` with API calls
- `Train_Model/train_model_ui.py` - Replace direct file writes with API calls
- `Train_Model/train_model_test_ui.py` - Same

**Changes:**
```python
# OLD (Direct file write)
safe_write_json(TRAIN_DATA_FILE, data)

# NEW (API call)
api_client.update_physics(velocity, position, acceleration, temperature)
```

#### 3.2 Train Manager (30 min)
**File:** `train_controller/train_manager.py`

**Changes:**
- Use REST API for train state instead of direct writes
- Keep server URL configuration
- Modify `add_train()`, `remove_train()`, `update_train()` to use HTTP requests

#### 3.3 CTC (45 min)
**Files to modify:**
- `ctc/ctc_main.py` - Replace JSON writes with API calls
- `ctc/ctc_ui.py` - Replace JSON writes with API calls
- `ctc/ctc_ui_temp.py` - Same

**Changes:**
```python
# OLD
with open('ctc_data.json', 'w') as f:
    json.dump(data, f)

# NEW
ctc_api.send_command(train_id, speed, authority)
```

#### 3.4 Track Controller (45 min)
**Files to modify:**
- `track_controller/New_SW_Code/sw_wayside_controller.py`
- `track_controller/hw_wayside/hw_wayside_controller.py`

**Changes:**
- Replace file I/O with wayside API client calls
- Get CTC commands via API
- Send occupancy/switch/light updates via API

### Phase 4: Testing & Deployment (1 hour)

#### 4.1 Local Testing
1. Start REST API server
2. Start Train Manager
3. Start Train Model
4. Verify all communication works

#### 4.2 Distributed Testing
1. Main PC: Run REST API server, Train Manager, Train Model, CTC
2. RPi 1: Run Train Controller HW
3. RPi 2: Run Track Controller HW
4. Verify all systems communicate properly

## Benefits of This Architecture

✅ **No Race Conditions** - Single process (server) manages all files
✅ **Multi-Computer Ready** - All communication via HTTP
✅ **Easy Debugging** - All data flow visible through API logs
✅ **Scalable** - Easy to add more Raspberry Pis or components
✅ **State Consistency** - Server is single source of truth
✅ **Network Resilience** - Clients can retry on connection loss

## Deployment Configuration

### Main Computer
```bash
# Start REST API Server (required!)
cd train_controller/api
python train_api_server.py

# Start other components (they connect to localhost:5000)
python train_manager.py
python train_model_ui.py
python ctc_ui.py
```

### Raspberry Pi 1 (Train Controller)
```bash
# Connect to main computer's server
python train_controller_hw_ui.py --train-id 1 --server http://<main-pc-ip>:5000
```

### Raspberry Pi 2 (Track Controller)
```bash
# Connect to main computer's server
python hw_main.py --server http://<main-pc-ip>:5000
```

## Files to Create

1. ✅ `train_controller/api/train_api_server.py` (extend existing)
2. ⬜ `Train_Model/train_model_api_client.py` (new)
3. ⬜ `ctc/api/ctc_api_client.py` (new)
4. ⬜ `track_controller/api/wayside_api_client.py` (new)

## Files to Modify

1. ⬜ `Train_Model/train_model_core.py`
2. ⬜ `Train_Model/train_model_ui.py`
3. ⬜ `train_controller/train_manager.py`
4. ⬜ `ctc/ctc_main.py`
5. ⬜ `ctc/ctc_ui.py`
6. ⬜ `track_controller/New_SW_Code/sw_wayside_controller.py`
7. ⬜ `track_controller/hw_wayside/hw_wayside_controller.py`

## Estimated Total Time: 4-5 hours

This is a significant refactoring but will make your system deployment-ready and eliminate all race condition issues.

