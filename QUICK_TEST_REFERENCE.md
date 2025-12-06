# Quick Test Reference for Phase 3

## ⚠️ Important: Always Run from Project Root!

To avoid import errors, **always** run commands from:
```
C:\Users\julen\Documents\ECE1140\Group4-ECE1140
```

---

## Level 1: Component Tests (No Server)

### ✅ Test CTC (No Server)
```bash
python -m ctc.ctc_ui_temp
```

**Expected:** API errors (server not running), but UI opens and works

---

### ✅ Test Wayside (No Server)  
**Option 1:** Use integrated launcher (recommended)
```bash
python combine_ctc_wayside_test.py
```

**Option 2:** Run directly
```bash
python -m track_controller.New_SW_Code.sw_wayside_controller_ui
```

**Expected:** File I/O fallback works, no crashes

---

### ✅ Test Train Model (No Server)
```bash
python -m Train_Model.train_model_ui
```

**Expected:** "[Train Model root] Using file-based I/O"

---

## Level 2: Integrated Tests (With Server)

### Terminal 1: Start REST API Server
```bash
cd train_controller/api
python train_api_server.py
```

**Wait for:** `* Running on http://127.0.0.1:5000`

---

### Terminal 2: Start Full System
```bash
# Go back to project root!
cd ../..
python combine_ctc_wayside_test.py
```

**Expected:**
- `[CTC API] ✓ Server is healthy`
- `[CTC] Using REST API: http://localhost:5000`
- `[Wayside 1] Using file-based I/O` (or REST API if configured)

---

## Common Mistakes to Avoid

### ❌ DON'T DO THIS:
```bash
cd ctc
python ctc_ui_temp.py          # ❌ Import error!
```

```bash
cd track_controller/New_SW_Code
python sw_wayside_controller_ui.py   # ❌ Import error!
```

### ✅ DO THIS INSTEAD:
```bash
# From project root:
python -m ctc.ctc_ui_temp              # ✅ Works!
python -m track_controller.New_SW_Code.sw_wayside_controller_ui  # ✅ Works!

# OR use the integrated launcher:
python combine_ctc_wayside_test.py     # ✅ Best option!
```

---

## Quick Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'track_controller'`
**Solution:** You're in the wrong directory. Go to project root!
```bash
cd C:\Users\julen\Documents\ECE1140\Group4-ECE1140
```

### Issue: `Cannot reach server at http://localhost:5000`
**Check:**
1. Is the server running? (`python train_controller/api/train_api_server.py`)
2. Are you testing fallback mode? (This error is expected!)

### Issue: Train doesn't dispatch
**Check:**
1. Is TrainManager initialized? (Check console for "TrainManager initialized")
2. Did you run from project root? (Import path issue)

---

## Full Integration Test (Complete Checklist)

### ✅ Step 1: Verify You're in Project Root
```bash
pwd  # Should show: .../Group4-ECE1140
```

### ✅ Step 2: Start Server
```bash
# Terminal 1
cd train_controller/api
python train_api_server.py
```

### ✅ Step 3: Start System
```bash
# Terminal 2 (new terminal, from project root!)
python combine_ctc_wayside_test.py
```

### ✅ Step 4: Dispatch Train
1. CTC UI opens automatically
2. Go to "Manual" tab
3. Fill in: Train, Line, Destination, Arrival Time
4. Click "Dispatch"
5. Train Model & Controller UIs appear

### ✅ Step 5: Verify REST API Usage
**Check console for:**
- `[CTC] ✓ Train 'Train 1' dispatched via REST API`
- `[Server] POST /api/ctc/dispatch - 200 OK`
- No "falling back to file I/O" messages (server is working!)

---

## Testing Status

| Test | Status | Command |
|------|--------|---------|
| Test 1.1: Train Model (No Server) | ✅ Works | `python -m Train_Model.train_model_ui` |
| Test 1.2: CTC (No Server) | ✅ Works | `python -m ctc.ctc_ui_temp` |
| Test 1.3: Wayside (No Server) | ✅ Works | `python combine_ctc_wayside_test.py` |
| Test 2: Full System (With Server) | 🔄 Ready | See "Full Integration Test" above |

---

## Pro Tips

1. **Use `combine_ctc_wayside_test.py` for most testing** - It handles imports correctly
2. **Keep 2 terminals open:**
   - Terminal 1: REST API server
   - Terminal 2: System launcher
3. **Check server logs** to verify API calls are working
4. **Restart server** if you make changes to `train_api_server.py`

---

**Phase 3 Testing: Ready to Go!** 🚀


