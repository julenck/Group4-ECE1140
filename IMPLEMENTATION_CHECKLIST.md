# Implementation Checklist

Use this checklist to track your progress integrating the REST API server.

## Pre-Implementation Setup

- [ ] Read `ARCHITECTURE_ANALYSIS.md` to understand the problem
- [ ] Read `API_INTEGRATION_GUIDE.md` for detailed instructions  
- [ ] Read `IMPLEMENTATION_SUMMARY_AND_NEXT_STEPS.md` for overview
- [ ] Make git commit or backup of current code
- [ ] Install dependencies: `pip install flask flask-cors requests`

## Phase 1: Server Testing (30 minutes)

### Test Server Locally

- [ ] Start server: `python start_unified_server.py`
- [ ] Server starts without errors
- [ ] Note the IP address shown: `__________________`
- [ ] Test health check: `curl http://localhost:5000/api/health`
- [ ] Response shows: `{"status": "ok"}`
- [ ] Keep server running in a terminal window

### Test API Endpoints

- [ ] Test trains endpoint: `curl http://localhost:5000/api/trains`
- [ ] Test CTC endpoint: `curl http://localhost:5000/api/ctc/state`
- [ ] Test wayside endpoint: `curl http://localhost:5000/api/wayside/1/state`
- [ ] Test track model endpoint: `curl http://localhost:5000/api/track_model/state`
- [ ] All endpoints return JSON (even if empty `{}`)

## Phase 2: Track Controller Integration (2-4 hours)

### Update sw_wayside_controller.py

- [ ] Open `track_controller/New_SW_Code/sw_wayside_controller.py`
- [ ] Add API client import at top (see `EXAMPLE_WAYSIDE_MODIFICATION.py`)
- [ ] Add `server_url` and `wayside_id` parameters to `__init__`
- [ ] Initialize `self.api_client = WaysideAPIClient(server_url, wayside_id)`
- [ ] Find all `json.load(open(self.ctc_comm_file))` patterns
- [ ] Replace with `self.api_client.get_ctc_commands()`
- [ ] Find all `json.load(open(self.track_comm_file))` patterns
- [ ] Replace with `self.api_client.get_track_data()`
- [ ] Find all `json.dump(..., open(self.train_comm_file))` patterns
- [ ] Replace with `self.api_client.send_train_commands(...)`
- [ ] Remove or comment out old file path attributes
- [ ] Save file

### Update sw_wayside_controller_ui.py

- [ ] Open `track_controller/New_SW_Code/sw_wayside_controller_ui.py`
- [ ] Add `import argparse` at top
- [ ] Add argument parser for `--server` and `--wayside-id` flags
- [ ] Pass `server_url` and `wayside_id` to controller initialization
- [ ] Update window title to show mode (Local/Remote)
- [ ] Save file

### Test Track Controller

- [ ] Terminal 1: Server running (`python start_unified_server.py`)
- [ ] Terminal 2: Test local mode: `python sw_wayside_controller_ui.py`
- [ ] Local mode works (no errors)
- [ ] Close local mode test
- [ ] Terminal 2: Test remote mode: `python sw_wayside_controller_ui.py --server http://localhost:5000 --wayside-id 1`
- [ ] Window title shows "Remote Mode"
- [ ] Server logs show wayside connection
- [ ] Remote mode works (no errors)
- [ ] Data updates correctly

## Phase 3: CTC Integration (2-4 hours)

### Update ctc_main_temp.py

- [ ] Open `ctc/ctc_main_temp.py`
- [ ] Add API client import at top
- [ ] Add `server_url` parameter to `dispatch_train()` function
- [ ] Initialize `api_client = CTCAPIClient(server_url)`
- [ ] Replace file I/O in dispatch_train with API client calls:
  - [ ] Replace reading `ctc_data.json` with `api_client.get_state()`
  - [ ] Replace writing `ctc_data.json` with `api_client.update_train()`
  - [ ] Replace writing `ctc_track_controller.json` with `api_client.send_track_controller_command()`
  - [ ] Replace file watcher with API polling: `api_client.get_train()`
- [ ] Save file

### Update ctc_ui_temp.py

- [ ] Open `ctc/ctc_ui_temp.py`
- [ ] Add `import argparse` at top
- [ ] Add argument parser for `--server` flag
- [ ] Add `server_url` parameter to `CTCUI.__init__`
- [ ] Initialize `self.api_client = CTCAPIClient(server_url)`
- [ ] Replace `load_data()` function with `self.api_client.get_state()`
- [ ] Replace `save_data()` function with `self.api_client.update_state()`
- [ ] Remove file watcher setup (if present)
- [ ] Add polling method: `poll_updates()` that calls `api_client.get_trains()`
- [ ] Schedule polling with `self.root.after(500, self.poll_updates)`
- [ ] Save file

### Test CTC

- [ ] Terminal 1: Server running
- [ ] Terminal 2: Test local mode: `python ctc/ctc_ui_temp.py`
- [ ] Local mode works
- [ ] Close local mode test
- [ ] Terminal 2: Test remote mode: `python ctc/ctc_ui_temp.py --server http://localhost:5000`
- [ ] Window title shows connection status
- [ ] Server logs show CTC connection
- [ ] Remote mode works
- [ ] Can dispatch train
- [ ] Commands appear in server logs

## Phase 4: Combined Test Update (30 minutes)

### Update combine_ctc_wayside_test.py

- [ ] Open `combine_ctc_wayside_test.py`
- [ ] Add `import subprocess` at top
- [ ] Add function to start server in subprocess
- [ ] Add `server_url` parameter to `run_ctc_ui()` function
- [ ] Add `server_url` parameter to `run_wayside_sw_ui_1()` function
- [ ] Add `server_url` parameter to `run_wayside_sw_ui_2()` function
- [ ] In `main()`, start server first before launching UIs
- [ ] Pass `server_url="http://localhost:5000"` to all component functions
- [ ] Update status window text to indicate server is running
- [ ] Save file

### Test Combined System

- [ ] Run: `python combine_ctc_wayside_test.py`
- [ ] Server starts automatically
- [ ] CTC UI opens (shows Remote Mode)
- [ ] Wayside 1 UI opens (shows Remote Mode)
- [ ] Wayside 2 UI opens (shows Remote Mode)
- [ ] Status window shows all systems running
- [ ] Dispatch train from CTC
- [ ] Wayside controllers receive commands
- [ ] Train completes route successfully

## Phase 5: Raspberry Pi Deployment (1 hour per Pi)

### Prepare Main Computer

- [ ] Write down server IP address: `__________________`
- [ ] Verify firewall allows port 5000
  - Windows: `netsh advfirewall firewall add rule name="Railway API" dir=in action=allow protocol=TCP localport=5000`
  - Linux: `sudo ufw allow 5000`
- [ ] Test from another computer: `curl http://[IP]:5000/api/health`

### Setup Raspberry Pi #1 (Wayside 1)

- [ ] Install Python 3 (if not installed)
- [ ] Install requests: `pip install requests`
- [ ] Copy track_controller folder to Pi
- [ ] Test connection: `curl http://[SERVER_IP]:5000/api/health`
- [ ] Connection successful
- [ ] Run: `python sw_wayside_controller_ui.py --server http://[SERVER_IP]:5000 --wayside-id 1`
- [ ] UI opens with "Remote Mode" in title
- [ ] Server logs show Pi connected
- [ ] Hardware GPIO works (if testing with hardware)

### Setup Raspberry Pi #2 (Wayside 2)

- [ ] Install Python 3 (if not installed)
- [ ] Install requests: `pip install requests`
- [ ] Copy track_controller folder to Pi
- [ ] Test connection: `curl http://[SERVER_IP]:5000/api/health`
- [ ] Connection successful
- [ ] Run: `python sw_wayside_controller_ui.py --server http://[SERVER_IP]:5000 --wayside-id 2`
- [ ] UI opens with "Remote Mode" in title
- [ ] Server logs show Pi connected
- [ ] Hardware GPIO works (if testing with hardware)

### Setup Additional Raspberry Pis (Train Controllers, if applicable)

- [ ] Follow same pattern as wayside Pis
- [ ] Use appropriate `--train-id` flag
- [ ] Verify connection in server logs

## Phase 6: Full System Testing (1-2 hours)

### Integration Test

- [ ] Start server on main computer
- [ ] Start CTC UI (remote mode) on main computer
- [ ] Start Wayside 1 on Raspberry Pi #1
- [ ] Start Wayside 2 on Raspberry Pi #2
- [ ] All components show "Remote Mode" or connected status
- [ ] Server logs show all connections

### Functional Test

- [ ] Dispatch Train 1 from CTC to a station
- [ ] CTC commands appear in server logs
- [ ] Wayside 1 receives commands (visible in UI)
- [ ] Wayside 1 processes PLC logic
- [ ] Train authority/speed commands sent to train
- [ ] Train model receives commands
- [ ] Train position updates
- [ ] CTC UI shows updated train position
- [ ] Train reaches destination
- [ ] No errors in any component

### Multi-Train Test

- [ ] Dispatch Train 2 from CTC
- [ ] Both trains operate simultaneously
- [ ] No conflicts or race conditions
- [ ] Both waysides handle their respective trains
- [ ] All data stays synchronized

### Failure Recovery Test

- [ ] Stop server briefly
- [ ] Components show connection error (expected)
- [ ] Restart server
- [ ] Components reconnect automatically
- [ ] Operation resumes normally
- [ ] No data loss

## Phase 7: Documentation and Cleanup

### Document Your Setup

- [ ] Record server IP address for team
- [ ] Document which Raspberry Pi runs which component
- [ ] Note any special configuration needed
- [ ] Create startup script if needed

### Performance Verification

- [ ] No lag in UI updates
- [ ] Commands execute promptly (<100ms)
- [ ] Multiple trains work smoothly
- [ ] Server CPU usage acceptable (<50%)
- [ ] No memory leaks over extended run

### Final Checks

- [ ] All JSON files are being created/updated by server only
- [ ] No "file not found" errors in logs
- [ ] No race condition errors
- [ ] Data always synchronized across components
- [ ] Raspberry Pis can be rebooted without issues
- [ ] System works with main computer and all Pis running

## Success Metrics

Mark these when achieved:

- [ ] ✅ Server runs stably for >1 hour without errors
- [ ] ✅ All Raspberry Pis connect successfully
- [ ] ✅ Trains can be dispatched and complete routes
- [ ] ✅ Multiple trains work simultaneously
- [ ] ✅ No JSON synchronization issues
- [ ] ✅ Team members can operate the system
- [ ] ✅ System is ready for demonstration/deployment

## Troubleshooting Reference

If you encounter issues, check:

- [ ] `API_INTEGRATION_GUIDE.md` - Troubleshooting section
- [ ] `QUICK_REFERENCE.md` - Common commands
- [ ] Server logs for error messages
- [ ] Firewall settings on main computer
- [ ] Network connectivity (ping test)
- [ ] Correct IP address being used
- [ ] Port 5000 not blocked or in use

## Notes / Issues Encountered

Use this space to document any issues or solutions:

```
Issue:


Solution:


---

Issue:


Solution:


---
```

## Completion Date

- Started: ____________
- Completed: ____________
- Total time: ____________
- Team members involved: ________________________

## Post-Implementation

- [ ] Update team documentation
- [ ] Train team members on new system
- [ ] Create troubleshooting guide for your specific setup
- [ ] Schedule regular testing
- [ ] Monitor system performance

---

**Congratulations!** 🎉

Once all checkboxes are complete, you have successfully migrated your railway control system to use a centralized REST API server, eliminating all JSON synchronization issues!

