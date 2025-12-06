# Phase 2 Bug Fix: Malformed Train Key Handling

## Issue Found

The `get_train_speeds()` method in `wayside_api_client.py` had unprotected `int()` conversions that could crash if `train_data.json` contained unexpected key formats.

### Vulnerability Details

**Location:** `track_controller/api/wayside_api_client.py`
- Line 244 (live data processing)
- Line 270 (cached data processing)

**Problematic Code:**
```python
for key, data in train_data.items():
    if key.startswith('train_'):
        train_id = int(key.split('_')[1])  # ← CRASH if malformed!
```

**Exception Handling Gap:**
The try-except blocks only caught:
- ✅ `requests.exceptions.Timeout`
- ✅ `requests.exceptions.RequestException`
- ❌ `ValueError` from `int()` conversion (NOT caught!)

### Attack Vectors

If `train_data.json` contains malformed keys:

1. **`"train_"`** (no number)
   - `split('_')[1]` = `""`
   - `int("")` → **ValueError: invalid literal for int()**

2. **`"train_abc"`** (non-numeric)
   - `split('_')[1]` = `"abc"`
   - `int("abc")` → **ValueError: invalid literal for int()**

3. **`"train_1a"`** (partial numeric)
   - `split('_')[1]` = `"1a"`
   - `int("1a")` → **ValueError: invalid literal for int()**

4. **`"train"`** (no underscore)
   - Passes `startswith('train_')` check? No, would be filtered out.
   - But `split('_')` = `["train"]`
   - `split('_')[1]` → **IndexError: list index out of range**

### Impact

**Before Fix:**
- ❌ Wayside API client crashes with unhandled `ValueError`
- ❌ Function fails to return any data (including valid trains)
- ❌ Wayside controller loses access to train velocities
- ❌ No graceful degradation or fallback to cached data

**Potential Causes:**
- Manual editing of `train_data.json` with typos
- Legacy code writing old format keys (`"specs"`, `"inputs"`, `"outputs"` at root)
- Race conditions during file writes
- Data corruption

## Solution Applied

### Fix: Defensive Key Parsing

Added try-except blocks around the `int()` conversion to gracefully skip malformed keys:

```python
for key, data in train_data.items():
    if key.startswith('train_'):
        try:
            train_id = int(key.split('_')[1])
            train_name = f"Train {train_id}"
            outputs = data.get('outputs', {})
            velocity_mph = outputs.get('velocity_mph', 0.0)
            train_speeds[train_name] = velocity_mph
        except (ValueError, IndexError) as e:
            # Skip malformed train keys (e.g., "train_", "train_abc")
            print(f"[Wayside API] Warning: Skipping malformed train key '{key}': {e}")
            continue
```

### What Changed

**Files Modified:**
1. `track_controller/api/wayside_api_client.py` (2 locations)
   - Line ~244: Live data processing loop
   - Line ~270: Cached data processing loop

**Exception Handling Added:**
- ✅ Catches `ValueError` (invalid int conversion)
- ✅ Catches `IndexError` (split result has no index [1])
- ✅ Logs warning with key name and error
- ✅ Continues to process other valid trains

### Behavior After Fix

**Scenario 1: All Valid Keys**
```json
{
    "train_1": { "outputs": { "velocity_mph": 45.0 } },
    "train_2": { "outputs": { "velocity_mph": 30.0 } }
}
```
- ✅ Returns: `{"Train 1": 45.0, "Train 2": 30.0}`
- ✅ No warnings

**Scenario 2: Mixed Valid and Malformed Keys**
```json
{
    "train_1": { "outputs": { "velocity_mph": 45.0 } },
    "train_": { "outputs": { "velocity_mph": 99.0 } },
    "train_abc": { "outputs": { "velocity_mph": 88.0 } },
    "train_2": { "outputs": { "velocity_mph": 30.0 } }
}
```
- ✅ Returns: `{"Train 1": 45.0, "Train 2": 30.0}` (only valid trains)
- ✅ Logs warnings:
  ```
  [Wayside API] Warning: Skipping malformed train key 'train_': invalid literal for int() with base 10: ''
  [Wayside API] Warning: Skipping malformed train key 'train_abc': invalid literal for int() with base 10: 'abc'
  ```

**Scenario 3: All Malformed Keys**
```json
{
    "train_": { ... },
    "train_abc": { ... }
}
```
- ✅ Returns: `{}` (empty dict, not None)
- ✅ Logs warnings for each malformed key
- ✅ Function doesn't crash

## Testing

### Unit Test Cases

```python
# Test 1: Normal operation (no malformed keys)
train_data = {
    "train_1": {"outputs": {"velocity_mph": 45.0}},
    "train_2": {"outputs": {"velocity_mph": 30.0}}
}
# Expected: {"Train 1": 45.0, "Train 2": 30.0}

# Test 2: Malformed key with empty number
train_data = {
    "train_1": {"outputs": {"velocity_mph": 45.0}},
    "train_": {"outputs": {"velocity_mph": 99.0}}
}
# Expected: {"Train 1": 45.0} + warning logged

# Test 3: Malformed key with non-numeric
train_data = {
    "train_1": {"outputs": {"velocity_mph": 45.0}},
    "train_abc": {"outputs": {"velocity_mph": 99.0}}
}
# Expected: {"Train 1": 45.0} + warning logged

# Test 4: All malformed keys
train_data = {
    "train_": {"outputs": {"velocity_mph": 99.0}},
    "train_xyz": {"outputs": {"velocity_mph": 88.0}}
}
# Expected: {} + warnings logged
```

### Integration Test

```bash
# Start server
python train_controller/api/train_api_server.py

# Run wayside API client test
python track_controller/api/wayside_api_client.py

# Expected output (if train_data.json is clean):
# --- Getting train speeds (from train_data.json) ---
# Found X trains
#   Train 1: 45.0 mph
#   Train 2: 30.0 mph
```

## Other API Clients Checked

Verified that other API clients do NOT have this vulnerability:
- ✅ `Train_Model/train_model_api_client.py` - No `int(key.split())` patterns found
- ✅ `ctc/api/ctc_api_client.py` - No `int(key.split())` patterns found

## Lessons Learned

### Best Practices for Robust API Clients

1. **Always validate external data** - Never trust JSON file contents
2. **Wrap all parsing operations** - `int()`, `float()`, `split()` can all fail
3. **Use specific exception handlers** - Catch `ValueError`, `IndexError`, `KeyError`, etc.
4. **Graceful degradation** - Skip bad data, process good data, log warnings
5. **Avoid assuming key formats** - Use regex validation or explicit checks

### Recommended Pattern

```python
# BAD: Assumes key format is perfect
train_id = int(key.split('_')[1])

# GOOD: Validates and handles errors
try:
    parts = key.split('_')
    if len(parts) != 2:
        raise ValueError(f"Expected format 'train_X', got '{key}'")
    train_id = int(parts[1])
except (ValueError, IndexError) as e:
    logger.warning(f"Skipping malformed key '{key}': {e}")
    continue
```

## Status

✅ **Bug Fixed** - Wayside API client now handles malformed train keys gracefully
✅ **No Linter Errors** - Code passes all checks
✅ **Tested** - Both live and cached data processing paths fixed
✅ **Documented** - Warning messages help debug data issues

---

**Severity:** Medium (could cause service disruption)
**Likelihood:** Low (requires malformed data in train_data.json)
**Impact:** High (wayside loses all train velocity data on crash)
**Priority:** High (defensive programming essential for production)

**Fixed:** 2024-12-06
**Phase:** Phase 2 (API Client Creation)

