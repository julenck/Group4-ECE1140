# Critical Fix: kp/ki Random Reset to None

## 🐛 The Problem

**User Report:**
> "kp and ki are both getting set to null for trains, we think its random and we dont know why its happening"

**Symptoms:**
- User sets `kp=5000`, `ki=500` via UI ✅
- Values save successfully
- Later (seems random), values reset to `None` ❌
- Train controller calculations fail with `NoneType` errors
- User has to re-enter values repeatedly

---

## 🔍 Root Cause Analysis

### The Bugs

**There were actually 3 critical locations with this bug:**
1. REST API server sync thread (`train_api_server.py`)
2. REST API server update endpoint (`train_api_server.py`)
3. **Local file API** (`train_controller_api.py`) ← **This was the real culprit!**

All 3 would **wipe out outputs** (including kp/ki) when the `inputs` key was missing:

**Location 1: `sync_train_data_to_states()` (line 194-198)** - Runs every 500ms
```python
# BEFORE (BUG):
if "inputs" not in train_states[key]:
    train_states[key] = {  # ❌ REPLACES EVERYTHING!
        "inputs": {},
        "outputs": {}  # ← Wipes out existing kp/ki
    }
```

**Location 2: `update_train_state()` (line 418)** - Called when UI updates kp/ki
```python
# BEFORE (BUG):
if "inputs" not in data[train_key]:
    data[train_key] = {"inputs": {}, "outputs": {}}  # ❌ WIPES OUT EXISTING VALUES!
```

**Location 3: `save_state()` in `train_controller_api.py` (lines 235-243)** - **THE REAL CULPRIT!**
```python
# BEFORE (BUG):
if 'inputs' in existing and 'outputs' in existing:
    inputs = existing['inputs'].copy()
    outputs = existing['outputs'].copy()
else:
    inputs = self.default_inputs.copy()
    outputs = self.default_outputs.copy()  # ❌ WIPES OUT kp/ki!
```

**Why Location 3 is the worst:**
- This is the **local file API** used by controllers
- Gets called **every single time** the controller saves state
- Even if the server fix worked, this would still reset kp/ki!
- Both local mode AND remote mode use this code path

### How It Happened

**Scenario 1: Sync Thread Wipes Values (Most Common)**

1. User sets `kp=5000`, `ki=500` via UI ✅
2. Values stored in `train_states.json`:
   ```json
   {
       "train_1": {
           "inputs": { ... },
           "outputs": {
               "kp": 5000.0,
               "ki": 500.0,
               ...
           }
       }
   }
   ```
3. Sync thread runs every 500ms
4. For ANY reason, `inputs` key is missing from `train_states[key]`:
   - File corruption
   - Race condition
   - Legacy format
   - JSON parse error
5. Line 195: **REPLACES ENTIRE DICT** with `{"inputs": {}, "outputs": {}}`
6. Your `kp=5000`, `ki=500` are **WIPED OUT** ❌
7. Lines 289-292 set them back to `None` as defaults
8. Train controller gets `None` values, calculations fail

**Scenario 2: Update Endpoint Wipes Values (Less Common)**

1. User clicks "Apply" to set new kp/ki values
2. POST request to `/api/train/1/state`
3. If `inputs` missing for any reason, line 418 **REPLACES ENTIRE DICT**
4. New kp/ki values written, but other values lost

---

## ✅ The Fix

### Strategy: Preserve, Don't Replace

**Never replace the entire train dict. Only add missing structure.**

### Location 1: Sync Thread (lines 194-208)

**Before:**
```python
if "inputs" not in train_states[key]:
    train_states[key] = {
        "inputs": {},
        "outputs": {}
    }
```

**After:**
```python
if "inputs" not in train_states[key]:
    # CRITICAL: Don't replace entire dict - preserve outputs (kp, ki, etc.)!
    if isinstance(train_states[key], dict):
        # Only add missing inputs, preserve existing outputs
        if "outputs" in train_states[key]:
            kp_val = train_states[key]["outputs"].get("kp")
            ki_val = train_states[key]["outputs"].get("ki")
            if kp_val is not None or ki_val is not None:
                print(f"[Server] Warning: {key} missing inputs but has kp={kp_val}, ki={ki_val} - preserving outputs")
        train_states[key]["inputs"] = {}
    else:
        # Completely malformed - must replace
        print(f"[Server] Warning: {key} is not a dict, replacing with default structure")
        train_states[key] = {"inputs": {}, "outputs": {}}
```

**Key Changes:**
- ✅ Only adds `inputs` key, preserves existing `outputs`
- ✅ Warning logged if kp/ki would have been lost
- ✅ Only replaces dict if completely malformed (not a dict)

### Location 2: Update Endpoint (Server - lines 416-450)

**Before:**
```python
if "inputs" not in data[train_key]:
    data[train_key] = {"inputs": {}, "outputs": {}}
```

**After:**
```python
if "inputs" not in data[train_key]:
    # CRITICAL: Don't replace entire dict - preserve outputs (kp, ki, etc.)!
    if isinstance(data[train_key], dict):
        # Only add missing inputs, preserve existing outputs
        if "outputs" in data[train_key]:
            kp_val = data[train_key]["outputs"].get("kp")
            ki_val = data[train_key]["outputs"].get("ki")
            if kp_val is not None or ki_val is not None:
                print(f"[Server] Warning: train_{train_id} missing inputs but has kp={kp_val}, ki={ki_val} - preserving outputs")
        data[train_key]["inputs"] = {}
    else:
        # Completely malformed - must replace
        print(f"[Server] Warning: train_{train_id} is not a dict, replacing with default structure")
        data[train_key] = {"inputs": {}, "outputs": {}}

# Ensure outputs section exists before writing to it
if "inputs" not in data[train_key]:
    data[train_key]["inputs"] = {}
if "outputs" not in data[train_key]:
    data[train_key]["outputs"] = {}
```

**Key Changes:**
- ✅ Preserves outputs when inputs missing
- ✅ Ensures outputs exists before writing kp/ki
- ✅ Warning logged if values would be lost

### Location 3: Local API save_state() (train_controller_api.py - lines 232-255) **CRITICAL!**

**Before:**
```python
if train_key in all_states and isinstance(all_states[train_key], dict):
    existing = all_states[train_key]
    if 'inputs' in existing and 'outputs' in existing:
        inputs = existing['inputs'].copy()
        outputs = existing['outputs'].copy()
    else:
        inputs = self.default_inputs.copy()
        outputs = self.default_outputs.copy()  # ❌ RESETS kp/ki TO None!
```

**After:**
```python
if train_key in all_states and isinstance(all_states[train_key], dict):
    existing = all_states[train_key]
    # Check inputs and outputs SEPARATELY (don't reset both!)
    if 'inputs' in existing and isinstance(existing['inputs'], dict):
        inputs = existing['inputs'].copy()
    else:
        inputs = self.default_inputs.copy()
    
    if 'outputs' in existing and isinstance(existing['outputs'], dict):
        outputs = existing['outputs'].copy()  # ✅ PRESERVES kp/ki!
    else:
        # Check if we're about to lose kp/ki values (legacy format)
        if 'kp' in existing or 'ki' in existing:
            print(f"[API] Warning: train_{self.train_id} has flat kp/ki - preserving")
            outputs = self.default_outputs.copy()
            outputs['kp'] = existing.get('kp', None)
            outputs['ki'] = existing.get('ki', None)
        else:
            outputs = self.default_outputs.copy()
```

**Key Changes:**
- ✅ **Checks inputs and outputs SEPARATELY** - doesn't reset both if one is missing!
- ✅ Preserves existing outputs even if inputs missing
- ✅ Handles legacy flat format (kp/ki at root level)
- ✅ Warning logged if legacy format detected
- ✅ **THIS WAS THE MAIN BUG** - happens on every save, not just sync!

### Location 4: Default Value Setting (Server - lines 297-302)

**Added protective comments:**
```python
# CRITICAL: Only set kp/ki to None if they don't exist
# NEVER overwrite existing values (user may have set them via UI)
if "kp" not in outputs_section:
    outputs_section["kp"] = None  # Must be set through UI
if "ki" not in outputs_section:
    outputs_section["ki"] = None  # Must be set through UI
```

**Note:** This logic was already correct (only sets if key missing), but added comments to prevent future bugs.

---

## 🧪 Testing

### Manual Test

**Test 1: Set values and verify persistence**

1. Start server and system:
   ```bash
   # Terminal 1
   cd train_controller/api
   python train_api_server.py
   
   # Terminal 2
   cd ../..
   python combine_ctc_wayside_test.py
   ```

2. Dispatch train and open hardware controller UI

3. Enter `kp=5000`, `ki=500`, click "Apply"

4. **Check `train_states.json`** - should see values:
   ```json
   {
       "train_1": {
           "outputs": {
               "kp": 5000.0,
               "ki": 500.0,
               ...
           }
       }
   }
   ```

5. **Wait 10 seconds** (sync thread runs 20 times)

6. **Check `train_states.json` again** - values should **still be there** ✅

7. **Check server logs** - should see:
   ```
   [Server] Syncing train_data.json ↔ train_states.json
   ```
   **Should NOT see:**
   ```
   [Server] Warning: train_1 missing inputs but has kp=... - preserving outputs
   ```
   (Unless there was actually a problem - in which case the fix saved your values!)

### Automated Test

**Simulate missing inputs:**

1. Manually corrupt `train_states.json`:
   ```json
   {
       "train_1": {
           "outputs": {
               "kp": 5000.0,
               "ki": 500.0
           }
           // ← Note: "inputs" key is MISSING!
       }
   }
   ```

2. Wait for next sync cycle (500ms)

3. **Check server logs** - should see:
   ```
   [Server] Warning: train_1 missing inputs but has kp=5000.0, ki=500.0 - preserving outputs
   ```

4. **Check `train_states.json`** - should now have:
   ```json
   {
       "train_1": {
           "inputs": {},  // ← Added
           "outputs": {
               "kp": 5000.0,  // ← PRESERVED!
               "ki": 500.0    // ← PRESERVED!
           }
       }
   }
   ```

---

## 📊 Impact

### Before Fix:
- ❌ kp/ki randomly reset to None
- ❌ Happens every 500ms if inputs missing
- ❌ Users frustrated, have to re-enter values
- ❌ Train controller calculations fail
- ❌ `NoneType * float` errors

### After Fix:
- ✅ kp/ki values preserved even if inputs missing
- ✅ Sync thread repairs structure without data loss
- ✅ Update endpoint protects existing values
- ✅ Warning logs help diagnose issues
- ✅ Train controller calculations work reliably

---

## 🚨 Related Issues

This fix also addresses the underlying cause of:
- **Phase 1 Bug**: `NoneType * float` errors (PHASE_1_BUGFIXES.md)
- The Phase 1 fix used `state.get('kp') or 5000.0` to handle None values
- This new fix **prevents** kp/ki from becoming None in the first place

**Defense in depth:**
1. **Phase 1 Fix**: Handle None gracefully (use `or` operator)
2. **This Fix**: Prevent None from happening (preserve values)

---

## 📝 Files Modified

| File | Lines | Change | Severity |
|------|-------|--------|----------|
| `train_controller/api/train_api_server.py` | 194-208 | Preserve outputs in sync thread | High |
| `train_controller/api/train_api_server.py` | 416-450 | Preserve outputs in update endpoint | High |
| `train_controller/api/train_controller_api.py` | 232-255 | **Preserve outputs in save_state()** | **CRITICAL** |
| `train_controller/api/train_api_server.py` | 297-302 | Added protective comments | Low |

**Total:** 2 files, 4 critical sections fixed

**Most Important Fix:** `train_controller_api.py` - This is the local API used by controllers, gets called on EVERY state save!

---

## 🎯 Git Commits

```
Commit 1: 6c53228 - CRITICAL FIX: Prevent kp/ki values from being reset to None (SERVER)
Commit 2: f3d514f - CRITICAL FIX (Part 2): Fix kp/ki reset bug in train_controller_api.py (LOCAL API)
Branch: phase3
```

**Both fixes were required!** The server fix (6c53228) alone wasn't enough because the local API (f3d514f) had the same bug.

---

## 💡 Lessons Learned

### Never Replace, Always Merge

**Bad Pattern:**
```python
if "inputs" not in data[key]:
    data[key] = {"inputs": {}, "outputs": {}}  # ❌ WIPES EVERYTHING
```

**Good Pattern:**
```python
if "inputs" not in data[key]:
    if isinstance(data[key], dict):
        data[key]["inputs"] = {}  # ✅ ONLY ADD MISSING KEY
    else:
        data[key] = {"inputs": {}, "outputs": {}}  # ✅ ONLY IF COMPLETELY BROKEN
```

### Log Warnings for Data Loss

When you detect a situation where data **would have** been lost, log it:
```python
if kp_val is not None or ki_val is not None:
    print(f"[Server] Warning: preserved kp={kp_val}, ki={ki_val}")
```

This helps:
- ✅ Diagnose issues
- ✅ Verify fix is working
- ✅ Detect corruption early

---

## ✅ Status

**Problem:** ✅ **FIXED (2 commits required!)**  
**Testing:** ⏳ **NEEDS VERIFICATION**  
**Documentation:** ✅ **UPDATED**

**Critical Discovery:**
The first fix (commit 6c53228) only fixed the **server**, but the bug ALSO existed in the **local file API** (`train_controller_api.py`). The second fix (commit f3d514f) was **THE REAL FIX** that actually solves the problem!

**Your kp and ki values should now be safe!** 🎉🔒

**Please test again and confirm kp/ki persist!**


