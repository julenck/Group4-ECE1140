# JSON File Update Fix - Raspberry Pi Distributed System

## 🔍 **Root Cause Analysis**

After a comprehensive audit of the distributed system, I identified the critical issue preventing JSON file updates on the Raspberry Pi.

### **The Problem**

The HW wayside controller was **mixing REST API calls with direct local file I/O**, even when running in server mode. This caused:

1. **Local file writes on Pi** that never synchronized back to the PC
2. **JSON files on Pi becoming stale** because writes only affected local copies
3. **PC never receiving position updates** from the Pi wayside controller
4. **Communication breakdown** between CTC and HW wayside

### **Specific Issues Found**

#### 1. **Three Critical File I/O Operations**
The controller directly wrote to local JSON files in these locations:

**Location 1** (Lines 1056-1080): Authority exhausted - deactivating train
```python
with open(self.ctc_comm_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
```

**Location 2** (Lines 1097-1116): End of line reached - deactivating train
```python
with open(self.ctc_comm_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
```

**Location 3** (Lines 1125-1144): Train moved to new block - updating position
```python
with open(self.ctc_comm_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
```

All three operations bypassed the REST API client completely.

#### 2. **File Paths Were Local**
```python
self.train_comm_file = os.path.join(project_root, "track_controller", "New_SW_Code", "wayside_to_train.json")
self.ctc_comm_file = os.path.join(project_root, "ctc_track_controller.json")
```

These paths pointed to local files on the Pi that weren't synchronized with the PC.

#### 3. **No API Check Before File Access**
The code didn't check `if self.wayside_api:` before performing file operations, so even when the API client was available and working, it still wrote to local files.

---

## ✅ **The Fix**

I modified the HW wayside controller to use **API-only mode** when `server_url` is set. The changes ensure:

### **1. Train Position Updates Now Use API**
All three file I/O locations now check for API availability first:

```python
if self.wayside_api:
    try:
        self.wayside_api.update_train_status(
            train_name=tname,
            position=int(position),
            state="moving" or "stopped",
            active=0 or 1
        )
    except Exception as e:
        print(f"[HW Wayside {self.wayside_id}] API failed: {e}")
else:
    # File I/O fallback (only when no API)
    ...
```

### **2. All CTC Communication Routes Through Server**
The flow now works correctly:

```
┌─────────────────────────────────────────────────────┐
│                   PC (Windows)                      │
│                                                     │
│  ┌──────────────┐                                  │
│  │   CTC UI     │                                  │
│  └──────┬───────┘                                  │
│         │                                           │
│         ↓                                           │
│  ┌──────────────────────────────────────────────┐  │
│  │  ctc_track_controller.json                   │  │
│  │  (Trains → Position, Active, Speed, Auth)    │  │
│  └──────────────────────────────────────────────┘  │
│         ↑                                           │
│         │ READ/WRITE via REST API                  │
│  ┌──────┴───────────────────────────────────────┐  │
│  │  REST API Server :5000                       │  │
│  │  /api/wayside/ctc_commands (GET)             │  │
│  │  /api/wayside/train_status (POST)            │  │
│  └──────────────────────────────────────────────┘  │
└───────────────────┬─────────────────────────────────┘
                    │ Network (WiFi/Ethernet)
                    │ http://<PC-IP>:5000
┌───────────────────┼─────────────────────────────────┐
│  Raspberry Pi     │                                 │
│                   ↓                                 │
│  ┌────────────────────────────────────────────┐    │
│  │  WaysideAPIClient                          │    │
│  │  - get_ctc_commands()                      │    │
│  │  - update_train_status()                   │    │
│  │  - send_train_commands()                   │    │
│  └────────────────────────────────────────────┘    │
│         ↑                                           │
│         │ Uses HTTP requests.get/post               │
│  ┌──────┴───────────────────────────────────────┐  │
│  │  HW_Wayside_Controller                       │  │
│  │  - Reads CTC commands via API                │  │
│  │  - Writes train positions via API            │  │
│  │  - NO LOCAL FILE I/O when server_url set    │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### **3. Proper Fallback Behavior**
- **When `server_url` is set**: API-only mode, no local file access
- **When `server_url` is None**: File I/O mode (for standalone PC testing)
- **When API call fails**: Error logged, but system continues

---

## 🧪 **Testing Instructions**

### **Prerequisites**
1. **PC and Raspberry Pi on same network**
2. **PC IP address known** (e.g., `10.5.127.125`)
3. **All JSON files on PC** in correct locations

### **Step 1: Start REST API Server on PC**

```bash
# Terminal 1 on PC
cd "C:\Users\<username>\...\Group4-ECE1140 CODE"
cd train_controller\api
python train_api_server.py
```

**Expected output:**
```
====================================================================
  TRAIN SYSTEM REST API SERVER v2.0 - BOUNDARY RESPECTING
====================================================================

Server starting on http://0.0.0.0:5000
 * Running on http://0.0.0.0:5000
```

### **Step 2: Start CTC + SW Wayside on PC**

```bash
# Terminal 2 on PC
cd "C:\Users\<username>\...\Group4-ECE1140 CODE"
python combine_ctc_wayside_test.py
```

**Expected:**
- CTC Dispatcher UI opens
- SW Wayside Controller UI opens
- Status shows "Wayside Controller 2 [HW] - Run on Raspberry Pi"

### **Step 3: Start HW Wayside on Raspberry Pi**

```bash
# On Raspberry Pi terminal
cd ~/projects/Group4-ECE1140

# Set server URL to your PC's IP
export SERVER_URL=http://10.5.127.125:5000

# Launch HW wayside
python launch_hw_wayside_only.py
```

**Expected output:**
```
🚂 Launching Hardware Wayside Controller B (Blocks 70-143)
🌐 Server URL: http://10.5.127.125:5000
✅ Hardware wayside components loaded
[HW Wayside B] Using REST API: http://10.5.127.125:5000
[Wayside API] ✓ Connected to server: http://10.5.127.125:5000
[Wayside API] ✓ Wayside Controller 2
🖥️  Creating UI...
✅ UI created successfully
[HW Wayside UI] Started trains processing cycle (1.0s period)
[HW Wayside UI] Started PLC processing cycle (0.2s period)
🚀 Starting Hardware Wayside Controller B...
```

### **Step 4: Dispatch a Train and Verify**

1. **On PC CTC UI**: Dispatch a train to a station in blocks 70-143
2. **Watch PC server terminal** for API calls:
   ```
   [Server] GET /api/wayside/ctc_commands - 200 OK
   [Server] GET /api/wayside/train_physics - 200 OK
   [Server] POST /api/wayside/train_status - 200 OK
   [Server] POST /api/wayside/train_commands - 200 OK
   ```

3. **Watch Raspberry Pi terminal** for train detection:
   ```
   [HW Wayside B] Picking up Train 1 at block 74 (handoff detected)
   [HW Wayside B] Train 1 commanded speed: 15 mph, authority: 500 yards
   [Wayside API] Train status updated
   [Wayside API] Train command sent
   ```

4. **Check PC JSON files** (should update in real-time):
   - `ctc_track_controller.json` - Train Position should change
   - `track_controller/New_SW_Code/wayside_to_train.json` - Commands should update

---

## 📊 **What Was Fixed**

| Location | Before | After |
|----------|--------|-------|
| **Train position updates** | Direct file write on Pi | API call to PC server |
| **Train deactivation** | Direct file write on Pi | API call to PC server |
| **End of line handling** | Direct file write on Pi | API call to PC server |
| **CTC communication** | Stale local files on Pi | Real-time via REST API |
| **Train command writes** | Already using API ✓ | No change needed ✓ |
| **CTC command reads** | Already using API ✓ | No change needed ✓ |

---

## 🎯 **Expected Behavior After Fix**

### **On Raspberry Pi:**
- ✅ **No local JSON file writes** when `SERVER_URL` is set
- ✅ **All position updates** sent via API to PC
- ✅ **Real-time train tracking** visible on PC
- ✅ **CTC commands** received from PC via API
- ✅ **Train commands** sent to PC via API

### **On PC:**
- ✅ **JSON files update in real-time** as Pi processes trains
- ✅ **CTC UI shows current train positions** from Pi
- ✅ **Server logs show API traffic** from Pi
- ✅ **Train handoffs work** between SW and HW waysides
- ✅ **All modules communicate** through central JSON files

---

## 🚨 **Troubleshooting**

### **Issue: "Connection refused" on Pi**

**Check:**
1. Server is running on PC: `http://<PC-IP>:5000/api/health`
2. Firewall allows port 5000 on PC
3. SERVER_URL is correct: `echo $SERVER_URL`
4. Ping PC from Pi: `ping <PC-IP>`

**Fix:**
```bash
# On Windows PC - Allow Python through firewall
# Or temporarily disable firewall for testing
# Then restart server
```

### **Issue: Pi shows "API failed" errors**

**Check:**
1. Server terminal shows incoming requests
2. Network connectivity is stable
3. PC JSON files exist and are readable

**Fix:**
- Check server terminal for error messages
- Verify JSON file paths in `train_api_server.py`
- Restart server with fresh JSON files

### **Issue: Trains not detected by Pi wayside**

**Check:**
1. Train is in blocks 70-143 (Pi's managed range)
2. CTC shows train as Active
3. `ctc_track_controller.json` has train entry

**Debug:**
```python
# On Pi, check what API is receiving:
import requests
resp = requests.get('http://<PC-IP>:5000/api/wayside/ctc_commands')
print(resp.json())  # Should show Trains dict
```

---

## 📁 **Files Modified**

| File | Changes |
|------|---------|
| `track_controller/hw_wayside/hw_wayside_controller.py` | ✓ Fixed 3 locations to use API instead of direct file I/O |
| `JSON_UPDATE_FIX_SUMMARY.md` | ✓ Created documentation (this file) |

**No other files were modified.** The fix was surgical and focused on the root cause.

---

## 📝 **Next Steps**

1. **Test the distributed setup** following Step-by-Step instructions above
2. **Verify train handoffs** from SW Wayside (blocks 0-73) to HW Wayside (blocks 70-143)
3. **Monitor server logs** to ensure API calls are flowing correctly
4. **Check JSON files on PC** update in real-time during operation
5. **Report any remaining issues** if JSON files still don't update

---

## ✅ **Status: READY FOR TESTING**

The fix is complete and ready for testing. The Pi should now properly update JSON files on the PC through the REST API server.

**Key Points:**
- ✅ No code changes needed on PC (server was already correct)
- ✅ Only HW wayside controller modified on Pi side
- ✅ Backward compatible with file I/O mode (when no `SERVER_URL`)
- ✅ Proper error handling and fallback behavior
- ✅ Follows existing REST API architecture

**Last Updated:** December 8, 2024
