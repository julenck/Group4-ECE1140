# CTC Data JSON Corruption Fix

## Problem

An extra closing curly bracket `}` was being added to `ctc_data.json`, causing JSON parsing errors:

```json
{
    "Dispatcher": {
        "Trains": {
            ...
        }
    }
}
}  ← Extra bracket causing errors!
```

**Symptoms:**
- `JSONDecodeError` when loading CTC data
- Trains not dispatching correctly
- CTC UI showing errors or empty data

---

## Solution 1: Thread-Safe Atomic Writes (Primary Fix)

All writes to `ctc_data.json` now use thread-safe atomic operations:

**Files:** `ctc/ctc_ui_temp.py`, `ctc/ctc_main_temp.py`

**How it works:**
1. Validates JSON structure before writing (checks balanced braces)
2. Writes to a temporary file first
3. Performs atomic rename (replaces old file in one operation)
4. If anything fails, temp file is deleted, original file untouched

**Functions:**
- `safe_write_json()` in `ctc_main_temp.py` - used by dispatch thread
- `save_data()` in `ctc_ui_temp.py` - used by UI thread

**Benefits:**
- ✅ Thread-safe - no race conditions
- ✅ Atomic - file is never in corrupt state
- ✅ Validated - corrupt data rejected before write
- ✅ Recoverable - original file preserved on error

---

## Solution 2: Automatic Detection and Cleanup (Fallback)

The `dispatch_train()` function also includes automatic detection and cleanup:

**File:** `ctc/ctc_main_temp.py`

**What it does:**
1. ✅ Reads `ctc_data.json`
2. ✅ Detects extra closing braces
3. ✅ Automatically removes them
4. ✅ Validates JSON structure
5. ✅ Falls back to fresh structure if unrepairable

**When it runs:**
- Every time you dispatch a train
- Automatically - no manual intervention needed
- Prints warning if it fixes the file

**Console output (if fix applied):**
```
[CTC Dispatch] Warning: Removed extra closing brace from ctc_data.json
```

---

## Solution 3: Manual Fix Script (Emergency Recovery)

If the file becomes corrupted, you can manually run the fix script:

```bash
python fix_ctc_data.py
```

**What it does:**
1. Counts opening `{` and closing `}` braces
2. Removes extra closing braces from the end
3. Validates the JSON structure
4. Saves the fixed version
5. If unrepairable, creates fresh default structure

**Example output:**
```
Attempting to fix ctc_data.json...
Found 8 opening braces and 9 closing braces
JSON is malformed: Extra data: line 57 column 1 (char 1234)
Attempting to fix...
Removed extra closing brace. Now have 8 closing braces
✓ Fixed! JSON is now valid
✓ Saved fixed version to ctc_data.json
```

**If already valid:**
```
Attempting to fix ctc_data.json...
Found 8 opening braces and 8 closing braces
JSON is already valid!
```

---

## Root Cause Analysis

The extra bracket was caused by:
- **Race condition** between multiple threads writing to the same file simultaneously
  - `ctc_ui_temp.py` (UI thread) writes during maintenance operations
  - `ctc_main_temp.py` (dispatch thread) writes during train updates
  - Both threads call `json.dump()` on the same file without synchronization
- **Non-atomic writes** - Python's `json.dump()` is not thread-safe
  - Thread A opens file, starts writing
  - Thread B opens same file, starts writing
  - File corruption: extra characters appended

**Preventions now in place:**
1. ✅ **Thread-safe atomic writes** - temp file + atomic rename
2. ✅ **Pre-write validation** - check structure before writing
3. ✅ **Balanced brace checking** - detect corruption before it happens
4. ✅ **File validation** before parsing (automatic cleanup on read)
5. ✅ **Fallback to default** structure if unrepairable
6. ✅ **Manual fix script** for recovery

---

## How to Verify File Integrity

### Quick Check:
```bash
python -m json.tool ctc_data.json
```

**If valid:**
```
{
    "Dispatcher": {
        "Trains": {
            ...
        }
    }
}
```

**If invalid:**
```
Expecting ',' delimiter: line 57 column 1 (char 1234)
```

### Count Braces:
```bash
python -c "
with open('ctc_data.json') as f:
    content = f.read()
    print(f'{ brackets: {content.count(\"{\")}')
    print(f'}} brackets: {content.count(\"}\")}')
    print(f'Difference: {content.count(\"}\") - content.count(\"{\")}')
"
```

**Should show:**
```
{ brackets: 8
} brackets: 8
Difference: 0
```

---

## When to Use Each Solution

### Use Automatic Prevention (Built-in):
- ✅ **Always** - it runs automatically
- ✅ During normal operation
- ✅ No action needed from you

### Use Manual Fix Script:
- ⚠️ If you see `JSONDecodeError` in console
- ⚠️ If CTC UI won't load
- ⚠️ If trains won't dispatch
- ⚠️ If you manually edited the file and broke it

---

## Testing the Fix

### Test 1: Manually Corrupt the File
```bash
# Add extra } to end of file
echo "}" >> ctc_data.json

# Verify it's broken
python -m json.tool ctc_data.json
# Should show error

# Fix it
python fix_ctc_data.py
# Should show "Fixed! JSON is now valid"

# Verify it's fixed
python -m json.tool ctc_data.json
# Should show valid JSON
```

### Test 2: Dispatch Train (Auto-fix)
```bash
# Start system
python combine_ctc_wayside_test.py

# Dispatch a train
# If file was corrupted, you'll see:
# [CTC Dispatch] Warning: Removed extra closing brace from ctc_data.json

# Train should dispatch successfully
```

---

## File Structure Reference

**Correct structure:**
```json
{
    "Dispatcher": {
        "Trains": {
            "Train 1": {
                "Line": "",
                "Suggested Speed": "",
                "Authority": "",
                "Station Destination": "",
                "Arrival Time": "",
                "Position": 0,
                "State": 0,
                "Current Station": ""
            },
            "Train 2": { ... },
            "Train 3": { ... },
            "Train 4": { ... },
            "Train 5": { ... }
        }
    }
}
```

**Total braces:** 
- Opening `{`: 8
- Closing `}`: 8
- **Must be equal!**

---

## Troubleshooting

### Issue: "JSON is malformed" even after running fix script

**Solution:**
```bash
# Backup current file
cp ctc_data.json ctc_data.json.backup

# Let script create fresh structure
python fix_ctc_data.py

# Manually copy any important train data from backup if needed
```

### Issue: Extra braces keep appearing

**Check for:**
1. Multiple instances of the system running
2. Old processes still writing to the file
3. Text editors with auto-save enabled

**Solution:**
```bash
# Kill all Python processes
pkill -9 python

# Clean start
python combine_ctc_wayside_test.py
```

---

## Related Files

- `ctc_data.json` - Main CTC data file (can get corrupted)
- `ctc/ctc_main_temp.py` - Dispatch logic (has auto-fix built-in)
- `fix_ctc_data.py` - Manual fix script

---

## Git Commit

```
Commit 1: 275cfa2 - Fix: Add safety checks for malformed ctc_data.json
  - Added automatic cleanup on read
  - Created manual fix script
  
Commit 2: 3f7096e - Fix: Thread-safe JSON writes to prevent corruption
  - Implemented atomic writes via temp file
  - Added pre-write validation
  - Fixed race condition between UI and dispatch threads
  - Replaced all json.dump() with safe_write_json()
  
Branch: phase3
```

---

## Summary

**Status:** ✅ **FULLY FIXED**

**Root Cause:** Race condition between multiple threads writing to the same file  
**Primary Fix:** Thread-safe atomic writes with validation  
**Fallback:** Automatic cleanup on read + manual fix script  
**Impact:** Extra `}` will no longer appear!

**You're protected!** The race condition has been eliminated at the source. 🛡️


