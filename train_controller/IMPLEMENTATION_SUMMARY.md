# REST API Network Implementation - Summary

## Files Created
 
### 1. **train_api_server.py** (Server)
- Location: `train_controller/api/train_api_server.py`
- Purpose: Flask REST API server that manages train_states.json
- Features:
  - Thread-safe file access
  - GET/POST endpoints for train states
  - Health check endpoint
  - Train reset/delete functionality

### 2. **train_controller_api_client.py** (Client)
- Location: `train_controller/api/train_controller_api_client.py`
- Purpose: REST API client for Raspberry Pi devices
- Features:
  - Same interface as local API (drop-in replacement)
  - Automatic connection testing
  - Fallback to local state if server unreachable
  - Compatible with existing controller code

### 3. **start_server.py** (Startup Script)
- Location: `train_controller/start_server.py`
- Purpose: Easy server startup with configuration
- Features:
  - Command-line arguments (--port, --host)
  - Displays local IP address
  - Shows available endpoints
  - Graceful shutdown

### 4. **test_api_connection.py** (Testing Tool)
- Location: `train_controller/test_api_connection.py`
- Purpose: Test REST API server connectivity
- Features:
  - Health check test
  - Get/Update state tests
  - Connection diagnostics

### 5. **NETWORK_SETUP.md** (Documentation)
- Location: `train_controller/NETWORK_SETUP.md`
- Purpose: Complete setup guide
- Includes:
  - Architecture diagram
  - Step-by-step instructions
  - Troubleshooting guide
  - API endpoint reference

### 6. **requirements.txt** (Dependencies)
- Location: `train_controller/requirements.txt`
- Lists all Python dependencies for server and client

---

## Files Modified

### 1. **train_controller_hw_ui.py**
Changes:
- Added `server_url` parameter to `__init__()`
- Conditional import of API (local vs client)
- Command-line argument parsing (`--train-id`, `--server`)
- Updated window title to show [REMOTE] mode

Key Code:
```python
def __init__(self, train_id=1, server_url=None):
    if server_url:
        # Remote mode
        from api.train_controller_api_client import train_controller_api_client
        self.api = train_controller_api_client(train_id=train_id, server_url=server_url)
    else:
        # Local mode
        from api.train_controller_api import train_controller_api
        self.api = train_controller_api(train_id=train_id)
```

### 2. **train_manager.py**
Changes:
- Added `is_remote` parameter to `add_train()`
- Updated `TrainPair` class with `is_remote_controller` attribute
- Added three controller type options in UI:
  - 💻 Software (UI Only)
  - 🔧 Hardware (Local)
  - 📡 Hardware (Remote - Raspberry Pi)
- Shows popup with Raspberry Pi instructions
- Updated train list to show controller type

Key Features:
- Automatically detects server IP address
- Generates command for Raspberry Pi
- Skips creating controller UI for remote trains
- Shows "Start on RPi" status in train list

---

## Usage Instructions

### On Server Machine:

1. **Install dependencies:**
   ```bash
   pip install flask flask-cors
   ```

2. **Start REST API server:**
   ```bash
   cd train_controller
   python start_server.py
   ```

3. **Start Train Manager:**
   ```bash
   python train_manager.py
   ```

4. **Add a remote hardware train:**
   - Select "📡 Hardware (Remote - Raspberry Pi)"
   - Click "Add New Train"
   - Note the command shown in popup

### On Raspberry Pi:

1. **Install dependencies:**
   ```bash
   pip install requests gpiozero smbus2
   ```

2. **Copy train_controller folder to Raspberry Pi**

3. **Run hardware controller:**
   ```bash
   cd train_controller/ui
   python train_controller_hw_ui.py --train-id 1 --server http://192.168.1.100:5000
   ```

---

## Architecture Benefits

✅ **Centralized State Management**
- Single source of truth (train_states.json on server)
- No file conflicts from multiple writers
- Thread-safe access

✅ **Network Flexibility**
- Add Raspberry Pis anywhere on local network
- No physical connection required
- Easy to scale to multiple devices

✅ **Backward Compatible**
- Existing code works without changes
- Local mode still available for testing
- Same API interface for both modes

✅ **Easy Deployment**
- Clear separation of server/client code
- Simple command-line interface
- Comprehensive documentation

---

## Data Flow

### Remote Hardware Train (Raspberry Pi):

```
[RPi] GPIO Button Press
  ↓
[RPi] HW UI: api.update_state({"service_brake": True})
  ↓
[RPi] Client API: POST http://server:5000/api/train/1/state
  ↓
[Server] REST API: Updates train_states.json["train_1"]
  ↓
[Server] Train Model: api.get_state() reads from file
  ↓
[Server] Train Model: Updates physics
  ↓
[Server] API: Writes velocity back to train_states.json
  ↓
[RPi] Client API: GET http://server:5000/api/train/1/state
  ↓
[RPi] HW UI: Displays updated velocity
```

---

## Testing Checklist

- [ ] Install server dependencies: `pip install flask flask-cors`
- [ ] Install client dependencies: `pip install requests`
- [ ] Start API server: `python start_server.py`
- [ ] Test server: `python test_api_connection.py`
- [ ] Start Train Manager: `python train_manager.py`
- [ ] Add remote hardware train
- [ ] Run hardware UI on Raspberry Pi (or locally with `--server` flag)
- [ ] Verify state updates across network
- [ ] Test GPIO button presses (on actual Pi)
- [ ] Verify LED status updates

---

## Next Steps

For Track Controller integration, create similar files:
- `track_controller_api_client.py`
- `track_controller_hw_ui.py` (with `--server` parameter)
- Use same REST API server
- Different endpoints or same pattern

---

## Troubleshooting

**Server won't start:**
- Check if port 5000 is in use
- Try different port: `python start_server.py --port 5001`

**Raspberry Pi can't connect:**
- Check firewall on server
- Verify IP address with `ipconfig` (Windows) or `ifconfig` (Linux)
- Test with: `curl http://server-ip:5000/api/health`

**State not updating:**
- Check server terminal for errors
- Check Raspberry Pi terminal for connection errors
- Verify train_id matches
- Test with `test_api_connection.py`

---

## Implementation Complete! ✓

All files created and updated. System ready for testing.
