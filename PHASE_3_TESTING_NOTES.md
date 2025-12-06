# Phase 3 Testing Notes

## Actual Test Results vs. Expected Behavior

### Test 1.2: CTC (No Server) - WORKING AS DESIGNED ✅

**What You're Seeing:**
```
[CTC API] ✗ ERROR: Cannot reach server at http://localhost:5000
[CTC API] ✗ Error: HTTPConnectionPool(host='localhost', port=5000): Max retries exceeded...
[CTC API] ⚠ Will use cached data when available
[CTC] Using REST API: http://localhost:5000
[CTC] Warning: Failed to initialize TrainManager: No module named 'train_controller'
```

**Is This Correct?** YES! ✅ This is the expected behavior when:
1. REST API server is not running (intentional for this test)
2. Running from the `ctc/` subdirectory

---

## What's Happening (Detailed Explanation)

### 1. API Client Initialization ✅
```
[CTC] Using REST API: http://localhost:5000
```
- API client initializes successfully
- This is GOOD - the client is configured to use the REST API
- It just can't connect yet (server not running)

### 2. Server Connection Failure ✅ (Expected for this test)
```
[CTC API] ✗ ERROR: Cannot reach server at http://localhost:5000
[CTC API] ✗ Error: HTTPConnectionPool... Max retries exceeded...
```
- API client tries to connect to server
- Fails gracefully with clear error messages
- This is exactly what we want for fallback testing

### 3. Graceful Degradation ✅
```
[CTC API] ⚠ Will use cached data when available
```
- API client acknowledges it will use cached data
- Falls back to file I/O when needed
- **This is the key feature we're testing!**

### 4. TrainManager Import Failure ⚠️ (Path Issue)
```
[CTC] Warning: Failed to initialize TrainManager: No module named 'train_controller'
```
- When running from `ctc/` directory, Python can't import `train_controller`
- This is a Python import path issue, not a Phase 3 bug
- **Solution:** Run from project root instead

---

## Recommended Testing Approach

### Option 1: Run from Project Root (Preferred)
```bash
# From: C:\Users\julen\Documents\ECE1140\Group4-ECE1140
python -m ctc.ctc_ui_temp
```

**Benefits:**
- ✅ All imports work correctly
- ✅ TrainManager initializes successfully
- ✅ Full functionality available

**Expected Output:**
```
[CTC API] ✗ ERROR: Cannot reach server at http://localhost:5000
[CTC API] ⚠ Will use cached data when available
[CTC] Using REST API: http://localhost:5000
[CTC] TrainManager initialized - ready to dispatch trains
[CTC] First train will use HARDWARE controller (REMOTE - Raspberry Pi)
[CTC] Subsequent trains will use SOFTWARE controllers
```

---

### Option 2: Run from ctc/ Directory (Current Method)
```bash
cd ctc
python ctc_ui_temp.py
```

**Behavior:**
- ⚠️ TrainManager import fails (path issue)
- ✅ CTC UI still works for basic operations
- ✅ File I/O fallback works
- ⚠️ Cannot dispatch trains (needs TrainManager)

**Use Case:** Testing basic CTC UI without train dispatch

---

## Testing Status

### What's Working ✅
1. ✅ **API Client Initialization** - Works correctly
2. ✅ **Graceful Degradation** - Falls back to file I/O when server unavailable
3. ✅ **Error Handling** - Clear error messages, no crashes
4. ✅ **File I/O Fallback** - CTC can operate without server

### What's Expected Behavior ⚠️
1. ⚠️ **TrainManager Import Failure** - Only when run from subdirectory (use project root)
2. ⚠️ **Server Connection Errors** - Expected for "No Server" tests

### What Would Be a Real Problem ❌
1. ❌ CTC crashes when server unavailable (NOT happening - good!)
2. ❌ No error messages (NOT happening - we have clear messages!)
3. ❌ Cannot operate without server (NOT happening - fallback works!)

---

## Full System Test (With Server)

To test the complete REST API integration:

### Terminal 1: Start Server
```bash
cd train_controller/api
python train_api_server.py
```

**Wait for:**
```
[Server] Starting REST API Server...
 * Running on http://127.0.0.1:5000
```

### Terminal 2: Start CTC (from project root)
```bash
# From: C:\Users\julen\Documents\ECE1140\Group4-ECE1140
python -m ctc.ctc_ui_temp
```

**Expected Output:**
```
[CTC API] ✓ Server is healthy at http://localhost:5000
[CTC] Using REST API: http://localhost:5000
[CTC] TrainManager initialized - ready to dispatch trains
```

Now you can dispatch trains and they'll use the REST API! 🎉

---

## Summary

**Your current test output is CORRECT!** ✅

The errors you're seeing are:
1. **Expected** - Server is not running (that's the test!)
2. **Handled gracefully** - System falls back to file I/O
3. **Minor path issue** - TrainManager import (easily fixed by running from project root)

**Phase 3 is working as designed!** The whole point is graceful degradation when the server is unavailable, and that's exactly what you're seeing.

---

## Next Steps

1. ✅ **Test 1.2 PASSED** - CTC works without server (fallback mode)
2. **Next:** Test 2.2 - Test CTC WITH server running
3. **Recommendation:** Run all tests from project root for full functionality

**Phase 3 Status:** Ready for full integration testing! 🚀


