# Phase 3 Testing Guide

## Overview
This guide explains how to test the REST API integration completed in Phase 3. All components (Train Model, Train Manager, CTC, Wayside) now use the REST API with graceful fallback to file I/O.

---

## Prerequisites

### Required Software
- ✅ Python 3.7+
- ✅ Flask (REST API server)
- ✅ requests library (API clients)
- ✅ All existing dependencies (tkinter, etc.)

### System Setup
- ✅ REST API server running on port 5000
- ✅ All components on same network (for distributed testing)
- ✅ Firewall allows port 5000 (for Raspberry Pi testing)

---

## Testing Levels

### Level 1: Component-Level Testing (File I/O Fallback)
Test each component in isolation WITHOUT REST API server to verify file I/O fallback works.

### Level 2: Integrated Testing (Local REST API)
Test all components together WITH REST API server on localhost.

### Level 3: Distributed Testing (Network REST API)
Test with components on different machines (main PC + Raspberry Pis).

---

## Level 1: Component-Level Testing (Fallback Mode)

### Test 1.1: Train Model (No Server)

**Purpose:** Verify Train Model works without REST API server

**Steps:**
```bash
cd Train_Model
python train_model_ui.py
# Don't start the REST API server!
```

**Expected Console Output:**
```
[Train Model root] Using file-based I/O (no server_url)
```

**Verify:**
- ✅ Train Model UI opens successfully
- ✅ Physics updates write to `train_data.json`
- ✅ No API errors or crashes
- ✅ Train responds to controller inputs

---

### Test 1.2: CTC (No Server)

**Purpose:** Verify CTC works without REST API server

**Steps:**
```bash
cd ctc
python ctc_ui_temp.py
# Don't start the REST API server!
```

**Expected Console Output:**
```
[CTC] Warning: Failed to initialize API client: ...
[CTC] Falling back to file-based I/O
```

**Verify:**
- ✅ CTC UI opens successfully
- ✅ Train dispatch writes to `ctc_data.json` and `ctc_ui_inputs.json`
- ✅ No API errors or crashes
- ✅ Trains can be dispatched using file I/O

---

### Test 1.3: Wayside (No Server)

**Purpose:** Verify Wayside works without REST API server

**Steps:**
```bash
cd track_controller/New_SW_Code
python sw_wayside_test.py  # Or however wayside is normally run
# Don't start the REST API server!
```

**Expected Console Output:**
```
[Wayside 1] Using file-based I/O (no server_url)
```

**Verify:**
- ✅ Wayside controller runs successfully
- ✅ Reads CTC commands from `ctc_track_controller.json`
- ✅ Reads train speeds from `train_data.json`
- ✅ No API errors or crashes

---

## Level 2: Integrated Testing (Local REST API)

### Test 2.1: Start the REST API Server

**Terminal 1:**
```bash
cd train_controller/api
python train_api_server.py
```

**Expected Output:**
```
[Server] Starting REST API Server...
[Server] Communication file paths:
[Server]   train_states.json: EXISTS
[Server]   train_data.json: EXISTS
[Server]   ctc_data.json: EXISTS
[Server]   ctc_track_controller.json: EXISTS
[Server]   wayside_to_train.json: EXISTS
[Server] Bidirectional sync thread started (500ms interval)
 * Running on http://127.0.0.1:5000
```

**Verify Server Endpoints:**
```bash
# Test server is responding
curl http://localhost:5000/api/health

# Should return:
# {"status": "healthy"}
```

---

### Test 2.2: Test Train Model with REST API

**Terminal 2:**
```bash
# Run Train Manager with server URL
cd train_controller
python train_manager.py --server-url http://localhost:5000
```

**Or programmatically:**
```python
from train_controller.train_manager import TrainManager

manager = TrainManager(server_url="http://localhost:5000")
train_id = manager.add_train(create_uis=True)
```

**Expected Console Output:**
```
[Train Manager] Using REST API: http://localhost:5000
[TrainManager] Using SOFTWARE controller for train 1
[Train Model 1] Using REST API: http://localhost:5000
```

**Verify:**
- ✅ Train Model UI opens
- ✅ Console shows "Using REST API"
- ✅ Physics updates go through REST API (check server logs)
- ✅ No file writes to `train_data.json` (server handles it)

**Server Logs Should Show:**
```
[Server] POST /api/train/1/physics - 200 OK
[Server] POST /api/train/1/beacon - 200 OK
```

---

### Test 2.3: Test CTC with REST API

**Terminal 3:**
```bash
export CTC_SERVER_URL="http://localhost:5000"
cd ctc
python ctc_ui_temp.py
```

**Expected Console Output:**
```
[CTC] Using REST API: http://localhost:5000
[CTC] TrainManager initialized - ready to dispatch trains
```

**Test Dispatch:**
1. Fill in train details (Line, Destination, Arrival Time)
2. Click "Dispatch" button

**Expected Output:**
```
[CTC] ✓ Train 'Train 1' dispatched via REST API
[CTC] Successfully dispatched Train 1 with hardware_remote controller
```

**Server Logs Should Show:**
```
[Server] POST /api/ctc/dispatch - 200 OK
[Server] POST /api/train/1/state - 200 OK
```

**Verify:**
- ✅ Train dispatches successfully
- ✅ Server logs show API calls
- ✅ Train appears in active trains table

---

### Test 2.4: Test Wayside with REST API

**Create test script:**
```python
# test_wayside_api.py
import sys
sys.path.append('track_controller/New_SW_Code')
from sw_wayside_controller import sw_wayside_controller

wayside = sw_wayside_controller(
    vital=True,
    plc="Green_Line_PLC_XandLup.py",
    server_url="http://localhost:5000",
    wayside_id=1
)

# Test loading CTC commands
wayside.load_inputs_ctc()
print(f"Active trains: {wayside.active_trains}")

# Test loading train speeds
speeds = wayside.load_train_speeds()
print(f"Train speeds: {speeds}")
```

**Run:**
```bash
python test_wayside_api.py
```

**Expected Output:**
```
[Wayside 1] Using REST API: http://localhost:5000
Active trains: {'Train 1': {...}, 'Train 2': {...}}
Train speeds: {'Train 1': 0.0, 'Train 2': 0.0}
```

**Server Logs Should Show:**
```
[Server] GET /api/wayside/1/ctc_commands - 200 OK
[Server] GET /api/wayside/train_physics - 200 OK
```

---

## Level 3: Distributed Testing (Raspberry Pi)

### Test 3.1: Main PC Setup

**On Main PC - Terminal 1 (Server):**
```bash
cd train_controller/api
python train_api_server.py
```

**Get Server IP Address:**
```bash
# Windows
ipconfig | findstr IPv4

# Linux/Mac
ifconfig | grep inet

# Example output: 192.168.1.100
```

---

### Test 3.2: Raspberry Pi - Hardware Train Controller

**On Raspberry Pi:**
```bash
cd ~/Group4-ECE1140/train_controller/ui
python train_controller_hw_ui.py --train-id 1 --server http://192.168.1.100:5000
```

**Expected Output:**
```
[HW UI] Using REMOTE API: http://192.168.1.100:5000 (timeout: 5.0s)
✓ Connected to server
✓ Initial state received
GPIO buttons detected
```

**Verify:**
- ✅ Raspberry Pi connects to main PC server
- ✅ Physical buttons work
- ✅ LEDs light up
- ✅ State updates go through REST API

**Main PC Server Logs:**
```
[Server] GET /api/train/1/state - 200 OK (from 192.168.1.X)
[Server] POST /api/train/1/state - 200 OK (from 192.168.1.X)
```

---

### Test 3.3: Raspberry Pi - Hardware Wayside Controller

**On Raspberry Pi:**
```bash
cd ~/Group4-ECE1140/track_controller/hw_wayside
python hw_wayside_main.py --server http://192.168.1.100:5000 --wayside-id 2
```

**Expected Output:**
```
[Wayside 2] Using REST API: http://192.168.1.100:5000
Connected to server successfully
```

**Verify:**
- ✅ Raspberry Pi connects to main PC server
- ✅ Reads CTC commands via REST API
- ✅ Reads train positions via REST API
- ✅ Hardware switches/lights controlled properly

---

## Test Scenarios

### Scenario A: Normal Operation (All API Calls Succeed)

**Setup:**
1. Start REST API server
2. Start all components with `server_url` parameter

**Expected:**
- ✅ All components use REST API
- ✅ No file I/O operations
- ✅ Server logs all operations
- ✅ Real-time updates across all components

**Verify:**
- Monitor server logs for API calls
- Check that JSON files are NOT being written directly
- Verify data flows correctly through server

---

### Scenario B: Server Restart (Graceful Recovery)

**Setup:**
1. Start all components with REST API
2. Stop the REST API server (Ctrl+C)
3. Restart the REST API server

**Expected:**
- ✅ Components detect server failure
- ✅ Fall back to file I/O temporarily
- ✅ Reconnect when server restarts
- ✅ Resume REST API operation
- ✅ No data loss during transition

**Verify:**
- Components log "API failed, falling back to file I/O"
- File I/O happens during server downtime
- Components automatically switch back to API when server returns

---

### Scenario C: Network Instability (Partial Failures)

**Setup:**
1. Start components with REST API
2. Simulate network issues:
   - Temporarily block port 5000 on firewall
   - OR disconnect network cable
   - OR kill server process

**Expected:**
- ✅ API timeouts logged with retry attempts
- ✅ Fallback to file I/O after max retries
- ✅ No crashes or data loss
- ✅ System continues operating in degraded mode

**Verify:**
- Check logs for "timed out after X.Xs" messages
- Verify file I/O fallback activates
- Confirm no exceptions or crashes

---

### Scenario D: Mixed Mode (Some Components Use API, Some Don't)

**Setup:**
1. Start REST API server
2. Start Train Model WITH server_url
3. Start CTC WITHOUT server_url
4. Start Wayside WITH server_url

**Expected:**
- ✅ Train Model uses REST API
- ✅ CTC uses file I/O
- ✅ Wayside uses REST API
- ✅ All components interoperate correctly through server-managed files

**Verify:**
- Mixed mode works without conflicts
- Server syncs file I/O changes to API clients
- No race conditions despite mixed mode

---

## Performance Testing

### Latency Measurements

**Tool:**
```python
import time

# Measure API call latency
start = time.time()
api_client.update_physics(...)
latency = (time.time() - start) * 1000  # Convert to ms
print(f"API latency: {latency:.2f}ms")
```

**Expected Latencies:**
- Localhost: 1-5ms
- Local network (Raspberry Pi): 10-50ms
- File I/O: 1-10ms

**Acceptable:** Any latency < 100ms (control loop is 500ms)

---

### Throughput Testing

**Test:** Dispatch 5 trains rapidly through CTC

**Steps:**
1. Start REST API server
2. Start CTC with API enabled
3. Dispatch trains 1, 2, 3, 4, 5 as fast as possible

**Expected:**
- ✅ All trains dispatch successfully
- ✅ No timeouts or failures
- ✅ Server handles concurrent requests
- ✅ No race conditions or corrupted data

**Server Logs:**
```
[Server] POST /api/ctc/dispatch - 200 OK (Train 1)
[Server] POST /api/ctc/dispatch - 200 OK (Train 2)
[Server] POST /api/ctc/dispatch - 200 OK (Train 3)
[Server] POST /api/ctc/dispatch - 200 OK (Train 4)
[Server] POST /api/ctc/dispatch - 200 OK (Train 5)
```

---

## Failure Mode Testing

### Failure Mode 1: Server Not Running

**Test:**
1. Do NOT start REST API server
2. Start components (they should fall back to file I/O)

**Expected:**
```
[Train Model 1] Warning: Failed to initialize API client: Connection refused
[Train Model 1] Falling back to file-based I/O
[CTC] Warning: Failed to initialize API client: Connection refused
[CTC] Falling back to file-based I/O
```

**Verify:**
- ✅ Components start successfully
- ✅ File I/O works normally
- ✅ No crashes or exceptions

---

### Failure Mode 2: Server Crashes During Operation

**Test:**
1. Start REST API server
2. Start all components with API enabled
3. Kill server process (simulate crash)
4. Continue operating

**Expected:**
```
[Train Model 1] API write failed: Connection refused, falling back to file I/O
[CTC] API dispatch error: Connection refused, falling back to file I/O
```

**Verify:**
- ✅ Components detect server failure
- ✅ Switch to file I/O automatically
- ✅ Continue operating in degraded mode
- ✅ No data loss

---

### Failure Mode 3: Network Timeout

**Test:**
1. Start server on main PC
2. Start Raspberry Pi with very short timeout
3. Introduce network delay (e.g., saturate bandwidth)

**Command:**
```bash
python train_controller_hw_ui.py --train-id 1 --server http://192.168.1.100:5000 --timeout 0.1
```

**Expected:**
```
[HW UI] Using REMOTE API: http://192.168.1.100:5000 (timeout: 0.1s)
[Train Controller API] Get state timed out after 0.1s
[Train Controller API] Get state timed out after 0.1s
[Train Controller API] Get state timed out after 0.1s
[Train Controller API] Using cached state
```

**Verify:**
- ✅ Timeout detected and logged
- ✅ Retries attempted (3 times by default)
- ✅ Cached data used when available
- ✅ Component continues operating

---

## Integration Test Procedures

### Full System Integration Test

**Terminal 1: Start Server**
```bash
cd train_controller/api
python train_api_server.py
```

**Terminal 2: Start Main System**
```bash
cd C:\Users\julen\Documents\ECE1140\Group4-ECE1140
python combine_ctc_wayside_test.py
```

**Test Sequence:**
1. ✅ CTC UI appears
2. ✅ Wayside UI appears
3. ✅ Dispatch Train 1 from CTC
4. ✅ Train Model UI appears
5. ✅ Train Controller UI appears
6. ✅ Verify console shows "Using REST API" messages
7. ✅ Dispatch Train 2 from CTC
8. ✅ Second train appears
9. ✅ Both trains operate independently

**Server Logs Should Show:**
```
[Server] POST /api/ctc/dispatch - 200 OK
[Server] POST /api/train/1/state - 200 OK
[Server] POST /api/train/1/physics - 200 OK
[Server] POST /api/train/1/beacon - 200 OK
[Server] GET /api/wayside/1/ctc_commands - 200 OK
[Server] GET /api/wayside/train_physics - 200 OK
```

---

### Communication Flow Verification

**Purpose:** Verify correct module boundaries are respected

**Test:**
1. Start full system with REST API
2. Dispatch train from CTC
3. Monitor server logs to verify communication path

**Expected Communication Path:**

```
CTC
  ↓ POST /api/ctc/dispatch
Server (writes to ctc_track_controller.json)
  ↓ GET /api/wayside/1/ctc_commands
Wayside
  ↓ POST /api/wayside/1/train_commands
Server (writes to wayside_to_train.json)
  ↓ GET /api/train_model/1/wayside_commands
Train Model
  ↓ POST /api/train/1/physics
Server (writes to train_data.json)
  ↓ Bidirectional sync
Server (syncs to train_states.json)
  ↓ GET /api/train/1/state
Train Controller
  ↓ POST /api/train/1/state
Server
```

**Verify:**
- ✅ Each module only uses its designated API endpoints
- ✅ No direct file I/O (except fallback scenarios)
- ✅ Data flows in correct direction
- ✅ Module boundaries respected

---

## Test Checklist

### Component Tests (File I/O Fallback)
- [ ] Train Model runs without server
- [ ] Train Manager runs without server
- [ ] CTC runs without server
- [ ] Wayside runs without server

### Component Tests (REST API)
- [ ] Train Model uses REST API when server available
- [ ] Train Manager uses REST API when server available
- [ ] CTC uses REST API when server available
- [ ] Wayside uses REST API when server available

### Integration Tests
- [ ] Full system runs with REST API
- [ ] Multiple trains can be dispatched
- [ ] All components communicate correctly
- [ ] Server logs show all API calls

### Failure Mode Tests
- [ ] Server not running - components use file I/O
- [ ] Server crashes during operation - graceful degradation
- [ ] Network timeout - retries and cached data
- [ ] Partial API failure - fallback to file I/O
- [ ] Mixed mode - some components use API, some don't

### Performance Tests
- [ ] API latency < 100ms
- [ ] No timeouts under normal operation
- [ ] Multiple trains don't cause slowdowns
- [ ] Server handles concurrent requests

### Distributed Tests (Raspberry Pi)
- [ ] Hardware train controller connects remotely
- [ ] Hardware wayside controller connects remotely
- [ ] Network communication stable
- [ ] No excessive latency

---

## Troubleshooting

### Issue: "Failed to initialize API client"

**Possible Causes:**
1. Server not running
2. Wrong server URL
3. Network connectivity issues
4. Port 5000 blocked by firewall

**Debug Steps:**
```bash
# Test if server is reachable
curl http://localhost:5000/api/health

# Check if port is open
netstat -an | grep 5000  # Linux/Mac
netstat -an | findstr 5000  # Windows

# Ping server (from Raspberry Pi)
ping 192.168.1.100
```

---

### Issue: "API update failed, falling back to file I/O"

**Possible Causes:**
1. Server endpoint not responding
2. Network timeout
3. Invalid data format

**Debug Steps:**
1. Check server logs for errors
2. Increase timeout value
3. Verify data format matches API expectations

---

### Issue: Components Still Using File I/O Despite Server Running

**Possible Causes:**
1. `server_url` parameter not passed to component
2. API client import failed
3. Component initialized before server started

**Debug Steps:**
1. Check console for "Using REST API" vs "Using file-based I/O"
2. Verify `server_url` parameter is passed correctly
3. Restart components after server is running

---

## Success Criteria

### Phase 3 Testing Passes If:
- ✅ All components run without server (file I/O fallback)
- ✅ All components use REST API when server available
- ✅ Full system integration works end-to-end
- ✅ Server logs show all expected API calls
- ✅ No data loss in any scenario
- ✅ Graceful degradation on failures
- ✅ Raspberry Pi deployment works over network

---

## Next Steps After Testing

1. **If All Tests Pass:**
   - Merge `phase3` branch to `main`
   - Deploy to production Raspberry Pis
   - Monitor for issues

2. **If Issues Found:**
   - Document issues
   - Fix bugs
   - Re-test before deployment

3. **Future Enhancements:**
   - Add authentication to REST API
   - Implement WebSocket for real-time updates
   - Add monitoring and metrics
   - Create admin dashboard

---

## Quick Test Command Reference

```bash
# Start server
cd train_controller/api && python train_api_server.py

# Test server health
curl http://localhost:5000/api/health

# Start full system
python combine_ctc_wayside_test.py

# Start Raspberry Pi train controller
python train_controller_hw_ui.py --train-id 1 --server http://<server-ip>:5000

# Monitor server logs
# (Watch Terminal 1 where server is running)
```

---

**Testing Guide Complete!** Ready for systematic validation of Phase 3 integration! 🧪


