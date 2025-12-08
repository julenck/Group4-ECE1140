# Quick Fix Summary - JSON Update Issue on Raspberry Pi

## What Was Wrong

The HW wayside controller on the Raspberry Pi was writing to **local JSON files** instead of using the **REST API** to update the PC. This meant:
- Position updates written on Pi never reached the PC
- CTC couldn't see train movements in HW wayside's blocks
- Communication was broken between PC and Pi

## What Was Fixed

Modified `track_controller/hw_wayside/hw_wayside_controller.py` in **3 locations**:

1. **Line ~1056**: Authority exhausted → Now uses API to deactivate train
2. **Line ~1097**: End of line reached → Now uses API to deactivate train  
3. **Line ~1125**: Train moved to new block → Now uses API to update position

All three now check `if self.wayside_api:` and use API calls instead of direct file writes.

## Files Changed

- ✅ `track_controller/hw_wayside/hw_wayside_controller.py` (3 fixes)
- ✅ `JSON_UPDATE_FIX_SUMMARY.md` (documentation)
- ✅ `QUICK_FIX_SUMMARY.md` (this file)
- ✅ `test_pi_connection.py` (diagnostic tool)

## Quick Test

### On PC (2 terminals):

**Terminal 1: Start Server**
```bash
cd train_controller/api
python train_api_server.py
```

**Terminal 2: Start CTC + SW Wayside**
```bash
python combine_ctc_wayside_test.py
```

### On Raspberry Pi:

```bash
export SERVER_URL=http://YOUR_PC_IP:5000
python launch_hw_wayside_only.py
```

**OR test connection first:**
```bash
python test_pi_connection.py http://YOUR_PC_IP:5000
```

## Expected Result

✅ Pi connects to PC server via REST API  
✅ JSON files on PC update when Pi processes trains  
✅ CTC sees train positions from Pi wayside  
✅ Server logs show API calls from Pi  
✅ No local file writes on Pi  

## Troubleshooting

**"Connection refused"**
- Check server is running on PC
- Verify PC IP address: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)
- Check firewall allows port 5000
- Test: `curl http://YOUR_PC_IP:5000/api/health`

**"API failed" errors on Pi**
- Check network connectivity
- Verify SERVER_URL is correct
- Look at PC server terminal for errors
- Restart both server and Pi wayside

**Trains not detected**
- Verify train is in blocks 70-143 (Pi's range)
- Check CTC shows train as Active
- Look at `ctc_track_controller.json` on PC

## Status

✅ **COMPLETE** - Ready for testing  
📝 See `JSON_UPDATE_FIX_SUMMARY.md` for detailed explanation  
🧪 Use `test_pi_connection.py` to verify setup
