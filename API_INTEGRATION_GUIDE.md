# API Integration Guide

## Overview

This guide explains how to integrate the Unified REST API Server into your existing railway system components to fix the JSON synchronization issues you're experiencing.

## The Problem You're Facing

Currently, your system has:
- ✅ **Train Controller**: Uses REST API (working correctly)
- ❌ **Track Controller (Wayside)**: Uses direct file I/O (causing sync issues)
- ❌ **CTC**: Uses direct file I/O with file watchers (causing sync issues)

When running on Raspberry Pis:
1. Files written on main computer aren't visible to Raspberry Pis
2. Multiple processes writing to same files cause race conditions
3. File watchers don't detect remote changes
4. Stale data causes incorrect behavior

## The Solution

Use the **Unified REST API Server** as a central hub for all data exchange:

```
Main Computer → Runs REST API Server → Single source of truth
    ↓                ↑                      ↓
    ↓                ↑                      ↓
Raspberry Pi 1   Raspberry Pi 2    All components talk to server
(Wayside HW)     (Train HW)        via HTTP (works across network)
```

## Step-by-Step Integration

### Phase 1: Install Dependencies

On **main computer** and **all Raspberry Pis**:

```bash
pip install flask flask-cors requests
```

### Phase 2: Start the Unified Server

On the **main computer**, start the server FIRST before any other components:

```bash
python start_unified_server.py
```

**Important**: Write down the IP address shown (e.g., `192.168.1.100`)

The server will display:
```
From Raspberry Pis:    http://192.168.1.100:5000
```

Keep this terminal window open and the server running!

### Phase 3: Update Track Controller (Wayside)

#### Option A: Quick Integration (Recommended First)

Modify `sw_wayside_controller.py` to accept a server URL and use the API client:

**At the top of the file** (after imports):

```python
# Add import for API client
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from track_controller.api.wayside_api_client import WaysideAPIClient
```

**In the `__init__` method**, replace file paths with API client:

```python
def __init__(self, vital, plc="", server_url=None, wayside_id=1):
    self.vital = vital
    
    # Initialize API client instead of direct file access
    self.api_client = WaysideAPIClient(server_url=server_url, wayside_id=wayside_id)
    
    # ... rest of initialization ...
```

**Replace all file read operations** like:

```python
# OLD CODE (direct file access):
with open(self.ctc_comm_file, 'r') as f:
    ctc_data = json.load(f)

# NEW CODE (API client):
ctc_data = self.api_client.get_ctc_commands()
```

**Replace all file write operations** like:

```python
# OLD CODE (direct file access):
with open(self.train_comm_file, 'w') as f:
    json.dump(output_data, f, indent=4)

# NEW CODE (API client):
self.api_client.send_train_commands(output_data)
```

#### Update the UI to accept `--server` flag

In `sw_wayside_controller_ui.py`, add command-line argument support:

```python
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', type=str, help='REST API server URL (e.g., http://192.168.1.100:5000)')
    parser.add_argument('--wayside-id', type=int, default=1, help='Wayside controller ID')
    args = parser.parse_args()
    
    vital = sw_vital_check.sw_vital_check()
    controller = sw_wayside_controller.sw_wayside_controller(
        vital, 
        plc="track_controller\\New_SW_Code\\Green_Line_PLC_XandLup.py",
        server_url=args.server,
        wayside_id=args.wayside_id
    )
    ui = sw_wayside_controller_ui(controller)
    
    # Update title to show mode
    mode = "Remote Mode" if args.server else "Local Mode"
    ui.title(f"Wayside Controller {args.wayside_id} ({mode})")
    
    ui.mainloop()

if __name__ == "__main__":
    main()
```

**Usage**:
- Local mode (testing): `python sw_wayside_controller_ui.py`
- Remote mode (Raspberry Pi): `python sw_wayside_controller_ui.py --server http://192.168.1.100:5000 --wayside-id 1`

### Phase 4: Update CTC

#### Update CTC Main Logic

In `ctc_main_temp.py`, replace file I/O with API client:

**At the top**:

```python
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ctc.api.ctc_api_client import CTCAPIClient
```

**Replace `dispatch_train` function** to use API client:

```python
def dispatch_train(train, line, station, arrival_time_str, 
                   server_url=None, dwell_time_s=10):
    """Dispatch a train using API client instead of direct file I/O."""
    
    # Create API client
    api_client = CTCAPIClient(server_url=server_url)
    
    # Check connection
    if server_url and not api_client.health_check():
        print("ERROR: Cannot connect to server!")
        return
    
    # Calculate route and speed (existing logic)
    dest_id = route_lookup_via_station[station]["id"]
    total_dist = sum(route_lookup_via_id[i]["meters_to_next"] for i in range(dest_id + 1))
    
    # ... (existing time/speed calculations) ...
    
    # Dispatch via API instead of writing files
    api_client.dispatch_train(
        train_name=train,
        line=line,
        station=station,
        arrival_time=arrival_time_str,
        speed=speed_meters_s,
        authority=total_dist
    )
    
    # Monitor train progress via API
    for i in range(dest_id + 1):
        station_name = route_lookup_via_id[i]["name"]
        authority_meters = route_lookup_via_id[i]["meters_to_next"]
        
        # Update via API
        api_client.update_train(train, {
            "Authority": authority_meters,
            "Suggested Speed": speed_meters_s
        })
        
        api_client.send_track_controller_command(
            train, 
            speed=speed_meters_s, 
            authority=authority_meters
        )
        
        # Poll for train position via API
        while True:
            train_data = api_client.get_train(train)
            train_pos = train_data.get("Position")
            if train_pos == route_lookup_via_id[i]["block"]:
                break
            time.sleep(0.5)
        
        # Update current station
        api_client.update_train(train, {"Current Station": station_name})
        time.sleep(dwell_time_s)
```

#### Update CTC UI

In `ctc_ui_temp.py`, add `--server` flag:

```python
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', type=str, help='REST API server URL')
    args = parser.parse_args()
    
    # Pass server URL to CTC UI
    ctc_ui = CTCUI(server_url=args.server)
    ctc_ui.run()
```

**In the CTCUI class**, replace file I/O with API client:

```python
class CTCUI:
    def __init__(self, server_url=None):
        self.api_client = CTCAPIClient(server_url=server_url)
        # ... rest of init ...
    
    def load_data(self):
        """Load data via API instead of file."""
        return self.api_client.get_state()
    
    def save_data(self, data):
        """Save data via API instead of file."""
        self.api_client.update_state(data)
```

**Remove file watchers** - API polling is more reliable:

```python
def poll_updates(self):
    """Poll server for updates instead of watching files."""
    trains = self.api_client.get_trains()
    # Update UI with train data
    self.update_train_display(trains)
    
    # Schedule next poll
    self.root.after(500, self.poll_updates)  # Poll every 500ms
```

### Phase 5: Update Combined Test File

Update `combine_ctc_wayside_test.py` to start the server first:

```python
import subprocess
import time

def start_api_server():
    """Start the unified API server in a separate process."""
    server_process = subprocess.Popen(
        ["python", "start_unified_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(3)  # Wait for server to start
    return server_process

def run_ctc_ui(server_url): 
    dispatcher_ui = ctc_ui.CTCUI(server_url=server_url)
    dispatcher_ui.run()

def run_wayside_sw_ui_1(server_url): 
    vital1 = wayside_sw.sw_vital_check.sw_vital_check()
    controller1 = wayside_sw.sw_wayside_controller.sw_wayside_controller(
        vital1,
        "track_controller\\New_SW_Code\\Green_Line_PLC_XandLup.py",
        server_url=server_url,
        wayside_id=1
    )
    ui1 = wayside_sw.sw_wayside_controller_ui(controller1)
    ui1.title("Green Line Wayside Controller 1 (Remote Mode)")
    ui1.mainloop()

def main():
    # Start API server first
    print("Starting Unified API Server...")
    server_process = start_api_server()
    server_url = "http://localhost:5000"
    
    # Start CTC in thread
    ctc_thread = threading.Thread(target=run_ctc_ui, args=(server_url,))
    ctc_thread.daemon = True
    ctc_thread.start()
    
    # Start Wayside controllers in threads
    wayside_thread_1 = threading.Thread(target=run_wayside_sw_ui_1, args=(server_url,))
    wayside_thread_1.daemon = True
    wayside_thread_1.start()
    
    # ... rest of main ...
```

### Phase 6: Raspberry Pi Setup

#### On Raspberry Pi (Wayside Controller):

1. **Copy files to Raspberry Pi**:
   ```bash
   scp -r track_controller/ pi@raspberrypi.local:~/
   ```

2. **Start wayside controller with server URL**:
   ```bash
   cd track_controller/New_SW_Code
   python sw_wayside_controller_ui.py --server http://192.168.1.100:5000 --wayside-id 1
   ```

Replace `192.168.1.100` with your main computer's IP address!

## Testing Checklist

### ✅ Phase 1: Test Server Locally

```bash
# Terminal 1: Start server
python start_unified_server.py

# Terminal 2: Test health check
curl http://localhost:5000/api/health
```

Expected: `{"status": "ok", ...}`

### ✅ Phase 2: Test Wayside Local Mode

```bash
python track_controller/New_SW_Code/sw_wayside_controller_ui.py
```

Should work without `--server` flag (local file mode)

### ✅ Phase 3: Test Wayside Remote Mode

```bash
# Terminal 1: Server running
python start_unified_server.py

# Terminal 2: Wayside with server
python track_controller/New_SW_Code/sw_wayside_controller_ui.py --server http://localhost:5000
```

Should connect to server and work identically to local mode

### ✅ Phase 4: Test CTC Integration

```bash
# Terminal 1: Server
python start_unified_server.py

# Terminal 2: CTC
python ctc/ctc_ui_temp.py --server http://localhost:5000
```

Dispatch a train and verify commands appear in server logs

### ✅ Phase 5: Test Raspberry Pi Connection

On Raspberry Pi:

```bash
# Test server connection
curl http://192.168.1.100:5000/api/health

# Run wayside controller
python sw_wayside_controller_ui.py --server http://192.168.1.100:5000 --wayside-id 1
```

Check main computer terminal - should see "Wayside 1 connected" messages

## Common Issues and Solutions

### Issue: "Cannot connect to server"

**Solution**:
1. Check server is running: `curl http://localhost:5000/api/health`
2. Check firewall: `sudo ufw allow 5000` (Linux) or Windows Firewall settings
3. Verify IP address: Use `ipconfig` (Windows) or `ifconfig` (Linux/Mac)

### Issue: "Module not found: requests"

**Solution**:
```bash
pip install requests
```

### Issue: "Port 5000 already in use"

**Solution**:
```bash
python start_unified_server.py --port 5001
```
Then use `http://...:5001` in all client connections

### Issue: Raspberry Pi can't reach server

**Solution**:
1. Verify same network: `ping 192.168.1.100` from Raspberry Pi
2. Check server binding: Must use `--host 0.0.0.0` not `localhost`
3. Test from Pi: `curl http://192.168.1.100:5000/api/health`

### Issue: Data not updating

**Solution**:
1. Check server logs - should see "updated" messages
2. Verify polling interval (500ms default)
3. Check if using old file-based code anywhere

## File Modification Summary

### ✅ Files Created (Already Done):
- `unified_api_server.py` - Main server
- `start_unified_server.py` - Server startup script
- `track_controller/api/wayside_api_client.py` - Wayside API client
- `ctc/api/ctc_api_client.py` - CTC API client

### ⚠️ Files to Modify (You Need to Do):
- `track_controller/New_SW_Code/sw_wayside_controller.py` - Use API client
- `track_controller/New_SW_Code/sw_wayside_controller_ui.py` - Add --server flag
- `ctc/ctc_main_temp.py` - Use API client
- `ctc/ctc_ui_temp.py` - Use API client, remove file watchers
- `combine_ctc_wayside_test.py` - Start server first

## Migration Strategy

### Week 1: Preparation
1. ✅ Create unified server (done)
2. ✅ Create API clients (done)
3. Test server locally on main computer

### Week 2: Track Controller Integration
1. Modify `sw_wayside_controller.py` to use API client
2. Test locally with and without server
3. Deploy to Raspberry Pi 1 and test

### Week 3: CTC Integration
1. Modify `ctc_main_temp.py` to use API client
2. Replace file watchers with polling
3. Test full system: CTC → Server → Wayside

### Week 4: Full System Testing
1. Test with all components running
2. Test with Raspberry Pis
3. Stress test with multiple trains
4. Document any issues and fix

## Next Steps

You now have:
1. ✅ Unified REST API Server
2. ✅ API Clients for Wayside and CTC
3. ✅ Startup scripts and documentation

**What to do next:**
1. Review this guide
2. Start with Phase 1 (install dependencies and test server)
3. Move to Phase 3 (integrate Track Controller)
4. Then Phase 4 (integrate CTC)
5. Finally Phase 6 (deploy to Raspberry Pis)

**Need Help?** 
- Check server logs for connection messages
- Use `curl` to test endpoints manually
- Compare with working Train Controller implementation

Good luck with your integration! 🚂

