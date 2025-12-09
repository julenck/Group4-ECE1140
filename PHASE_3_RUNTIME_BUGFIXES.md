# Phase 3 Runtime Bug Fixes

## Issues Fixed During Testing

### Bug 1: CTC API Client Import Error ✅

**Symptom:**
```
[CTC] Warning: Failed to initialize API client: No module named 'api.ctc_api_client'
```

**Root Cause:**
- When running from project root via `combine_ctc_wayside_test.py`, the import path was incorrect
- Used `from api.ctc_api_client import CTCAPIClient`
- Should use absolute import: `from ctc.api.ctc_api_client import CTCAPIClient`

**Fix Applied:**
```python
# BEFORE (line 43)
from api.ctc_api_client import CTCAPIClient

# AFTER
from ctc.api.ctc_api_client import CTCAPIClient
```

**File:** `ctc/ctc_ui_temp.py` line 43

---

### Bug 2: FileNotFoundError on Second Train Dispatch ✅

**Symptom:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'ctc\\ctc_ui_inputs.json'
```

**Root Cause:**
- Code used `self.os.path.join('ctc', 'ctc_ui_inputs.json')` which creates a relative path
- Relative paths don't work correctly when running from different directories
- Need to use `__file__` to get the actual script location

**Fix Applied:**
```python
# BEFORE (lines 307-314)
with open(self.os.path.join('ctc', 'ctc_ui_inputs.json'), "r") as f1:
    data1 = self.json.load(f1)
# ...
with open(self.os.path.join('ctc', 'ctc_ui_inputs.json'), "w") as f1:
    self.json.dump(data1, f1, indent=4)

# AFTER
import os
ctc_dir = os.path.dirname(os.path.abspath(__file__))
input_file = os.path.join(ctc_dir, 'ctc_ui_inputs.json')
with open(input_file, "r") as f1:
    data1 = self.json.load(f1)
# ...
with open(input_file, "w") as f1:
    self.json.dump(data1, f1, indent=4)
```

**File:** `ctc/ctc_ui_temp.py` lines 306-316

---

### Bug 3: AttributeError in Train Model UI ✅

**Symptom:**
```
AttributeError: 'TrainModelUI' object has no attribute 'info_labels'. Did you mean: 'winfo_pixels'?
```

**Root Cause:**
- `_update_ui()` method tries to access `self.info_labels` 
- Sometimes called via `self.after(1, lambda: self._run_cycle(...))` before UI is fully initialized
- `info_labels` is created in `create_info_panel()` which might not have run yet

**Fix Applied:**
```python
# BEFORE (line 631)
def _update_ui(self, outputs, ctrl, merged_inputs, disembarking):
    try:
        self.info_labels["Velocity (mph)"].config(...)

# AFTER
def _update_ui(self, outputs, ctrl, merged_inputs, disembarking):
    # Guard: Don't update if UI components aren't fully initialized yet
    if not hasattr(self, 'info_labels') or not self.info_labels:
        return
    try:
        self.info_labels["Velocity (mph)"].config(...)
```

**File:** `Train_Model/train_model_ui.py` line 633

---

## Impact

### Before Fixes:
- ❌ CTC couldn't load API client when run from combine launcher
- ❌ Second train dispatch crashed with FileNotFoundError  
- ❌ Train Model UI crashed with AttributeError on startup
- ❌ System unusable for testing

### After Fixes:
- ✅ CTC API client loads correctly
- ✅ Can dispatch multiple trains without errors
- ✅ Train Model UI initializes gracefully
- ✅ **System fully functional for testing!**

---

## Testing

To verify the fixes work:

```bash
# From project root
python combine_ctc_wayside_test.py

# Then in CTC UI:
# 1. Dispatch Train 1 - should work ✅
# 2. Dispatch Train 2 - should work ✅ (previously crashed)
# 3. Both trains should have working UIs ✅
```

**Expected Console Output:**
```
[CTC] Using REST API: http://localhost:5000
[CTC] TrainManager initialized - ready to dispatch trains
[Train Model 1] Using file-based I/O
[CTC] Successfully dispatched Train 1 with hardware_remote controller
# (dispatch second train)
[Train Model 2] Using file-based I/O  
[CTC] Successfully dispatched Train 2 with software controller
```

**No errors about:**
- ❌ `No module named 'api.ctc_api_client'`
- ❌ `FileNotFoundError: ctc\\ctc_ui_inputs.json`
- ❌ `AttributeError: 'TrainModelUI' object has no attribute 'info_labels'`

---

## Files Modified

| File | Lines | Change |
|------|-------|--------|
| `ctc/ctc_ui_temp.py` | 43 | Fixed API client import path |
| `ctc/ctc_ui_temp.py` | 306-311 | Fixed file path construction using `__file__` |
| `Train_Model/train_model_ui.py` | 633-635 | Added guard for `info_labels` attribute |

---

## Related Issues

These fixes are part of Phase 3 integration testing. See also:
- `PHASE_3_BUGFIXES.md` - Bug fixes during development
- `PHASE_3_TESTING_GUIDE.md` - Testing procedures
- `QUICK_TEST_REFERENCE.md` - Quick testing commands

---

## Git Commit

```
Commit: b721ebc
Message: Fix critical runtime errors in combine test
Branch: phase3
```

**Status:** ✅ **FIXED** - All runtime errors resolved, system ready for testing!


