# Hardware Train Controller Testing Guide

This guide helps you test the Train Model Test UI → Server → Hardware Controller flow.

## System Architecture

```
Train Model Test UI (PC)
    ↓ writes train_data.json (local)
    ↓ sends REST POST (remote mode with --server flag)
    ↓
REST API Server (PC)
    ↓ reads train_data.json every 500ms
    ↓ updates train_states.json
    ↓ serves via GET /api/train/<id>/state
    ↓
Hardware Controller (Raspberry Pi)
    ↓ fetches via REST GET every 500ms
    ↓ displays inputs on screen
```

## Setup Steps

### 1. Start the REST API Server (on PC)
```bash
cd train_controller
python start_server.py
```

**Expected output:**
```
════════════════════════════════════════
  TRAIN SYSTEM REST API SERVER
════════════════════════════════════════

✓ Server starting on 0.0.0.0:5000
✓ Local IP address: 192.168.1.100
[Server] Train data sync thread started (500ms interval)
```

**Note the Local IP address** - you'll need this for the next steps.

### 2. Start Hardware Controller (on Raspberry Pi)
```bash
cd train_controller/ui
python train_controller_hw_ui.py --train-id 1 --server http://192.168.1.100:5000
```

Replace `192.168.1.100` with your actual server IP.

**Expected output:**
```
[Hardware Controller] Remote mode enabled
[Hardware Controller] Server: http://192.168.1.100:5000
[Hardware Controller] Train ID: 1
```

The UI should open and show "Train 1 Hardware Controller (Remote Mode)" in the title.

### 3. Start Train Model Test UI with Server Connection
```bash
cd "Train Model"
python train_model_test_ui.py --train-id 1 --server http://192.168.1.100:5000
```

**Expected output:**
- Window title: "Train 1 Model Test UI (Remote Mode)"
- No connection errors in terminal

## Testing the Flow

### Test 1: Verify Server Communication

**On PC (server terminal):**
Watch for these messages every 500ms:
```
[Server] Train data sync thread running...
```

**Check server is reachable from Pi:**
```bash
# On Raspberry Pi
curl http://192.168.1.100:5000/api/health
```

Expected response:
```json
{
  "status": "ok",
  "message": "Train API Server running",
  "timestamp": "2025-11-13T..."
}
```

### Test 2: Send Inputs from Test UI

**In Train Model Test UI:**
1. Change "Commanded Speed" to `50`
2. Change "Speed Limit" to `45`
3. Click "Step Simulation" (or wait for auto-update)

**Watch server terminal:**
```
[Test UI] Sending data to server...
[Server] Train 1 state updated: ['commanded_speed', 'speed_limit', ...]
```

**On Raspberry Pi terminal:**
```
[Hardware Controller] State fetched from server
[Hardware Controller] Commanded speed: 50.0
[Hardware Controller] Speed limit: 45.0
```

**On Hardware Controller UI:**
- Commanded Speed should show `50.0`
- Speed Limit should show `45.0`

### Test 3: Verify Data Flow Direction

**Hardware Controller → Server:**
- Press any button on Pi (e.g., "Service Brake")
- Check that button state is sent to server

**Server → Test UI:**
- The sync happens automatically via train_data.json

**Test UI → Server:**
- Change any input in Test UI
- Should appear on Hardware Controller within 1 second

## Troubleshooting

### Problem: "Connection timeout" on Raspberry Pi

**Check:**
1. Server is running: `curl http://192.168.1.100:5000/api/health`
2. Firewall allows port 5000
3. IP address is correct

**Fix:**
```bash
# On Windows PC, allow port 5000
netsh advfirewall firewall add rule name="Flask Port 5000" dir=in action=allow protocol=TCP localport=5000
```

### Problem: Test UI not sending to server

**Check terminal output:**
```
[Test UI] Error sending to server: Connection refused
```

**Fix:**
- Verify you started Test UI with `--server` flag
- Verify server URL is correct
- Check server is running

### Problem: Hardware Controller shows old data

**Check:**
1. Server sync thread is running (look for log messages)
2. train_data.json exists and is being updated
3. train_states.json is being written by server

**Debug command:**
```bash
# Watch train_states.json changes
watch -n 1 cat train_controller/data/train_states.json
```

### Problem: Data not reaching Hardware Controller

**Check full flow:**

1. **Test UI writes locally:**
```bash
cat "Train Model/train_data.json" | grep "commanded speed"
```

2. **Test UI sends to server (with --server flag):**
```bash
# Check server terminal for POST messages
```

3. **Server receives and stores:**
```bash
cat train_controller/data/train_states.json | grep "commanded_speed"
```

4. **Pi fetches from server:**
```bash
# On Pi, check terminal for GET messages
curl http://192.168.1.100:5000/api/train/1/state
```

## Key Files

- `Train Model/train_data.json` - Local storage (Test UI writes here)
- `train_controller/data/train_states.json` - Server storage (synced from train_data.json)
- Server reads from train_data.json every 500ms
- Server writes to train_states.json
- Hardware Controller reads via REST API every 500ms

## Common Mistakes

### ❌ Starting Test UI without --server flag
```bash
# WRONG - writes locally only
python train_model_test_ui.py
```

### ✅ Starting Test UI with --server flag
```bash
# CORRECT - writes locally AND sends to server
python train_model_test_ui.py --train-id 1 --server http://192.168.1.100:5000
```

### ❌ Using localhost on Pi
```bash
# WRONG - Pi can't reach server via localhost
python train_controller_hw_ui.py --train-id 1 --server http://localhost:5000
```

### ✅ Using actual server IP
```bash
# CORRECT - Pi reaches server via network
python train_controller_hw_ui.py --train-id 1 --server http://192.168.1.100:5000
```

## Verification Checklist

- [ ] Server running on PC
- [ ] Server shows sync thread started
- [ ] Server IP address noted
- [ ] Hardware Controller started with correct server URL
- [ ] Test UI started with --server flag
- [ ] Test UI title shows "(Remote Mode)"
- [ ] Changing inputs in Test UI updates Hardware Controller
- [ ] No timeout errors in any terminal
- [ ] Server terminal shows state updates

## Expected Behavior

When everything works:
1. Change "Commanded Speed" to 60 in Test UI
2. Within 0-1 seconds, Hardware Controller shows 60
3. Press "Service Brake" button on Pi
4. Test UI should eventually reflect brake state (via file sync)

## Need More Help?

Check server logs:
```bash
cd train_controller
python start_server.py 2>&1 | tee server.log
```

Check what's in train_states.json:
```bash
cat train_controller/data/train_states.json | python -m json.tool
```

Verify network connectivity:
```bash
ping 192.168.1.100  # From Pi to PC
```
