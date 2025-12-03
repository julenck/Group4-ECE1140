# Train Data JSON Access Denied Fix

## Problem Summary

You were experiencing "Access Denied" errors when writing to `train_data.json`, which was causing the file to be reset and your power commands to drop to 0.

## Root Cause

Multiple processes/threads were trying to write to `train_data.json` simultaneously:

1. **Train Model UI** - Writes train outputs (velocity, position, etc.) every cycle (~500ms)
2. **Wayside Sync** - Writes commanded speed/authority from wayside controller
3. **Train Controller** - Reads power commands from the file
4. **Multiple concurrent operations** - File locking conflicts on Windows

### The Silent Failure Problem

The original `safe_write_json()` function in `train_model_core.py` had this behavior:

```python
except (PermissionError, OSError) as e:
    # Silently ignore - file may be locked by another process
    pass  # ❌ PROBLEM: Fails silently, no logging, data lost!
```

When a `PermissionError` occurred (file locked by another process), the function would:
- **Silently fail** without logging
- Leave the file unchanged or partially written
- Not retry enough times
- Potentially corrupt the JSON structure

This caused your power commands to remain at 0 because the Train Controller's updates were being lost.

## Fixes Applied

### 1. Improved File Writing (`safe_write_json` in `train_model_core.py`)

**Changes:**
- ✅ Uses unique temporary files (with process ID) to avoid conflicts
- ✅ Increased retries from 3 to 5 attempts
- ✅ Exponential backoff (50ms, 100ms, 200ms, 400ms, 800ms)
- ✅ Proper file descriptor handling with `fsync()` for atomic writes
- ✅ **Error logging** - Now prints when writes fail
- ✅ Atomic `os.replace()` to prevent partial writes

**Before:**
```python
tmp = path + ".tmp"  # ❌ Same temp file for all processes
for attempt in range(3):  # ❌ Only 3 retries
    time.sleep(0.1 * (attempt + 1))  # ❌ Linear backoff
    # ... silently fails on last attempt
```

**After:**
```python
tmp_fd, tmp_path = tempfile.mkstemp(suffix='.tmp', dir=tmp_dir, text=True)
for attempt in range(5):  # ✅ 5 retries
    wait_time = 0.05 * (2 ** attempt)  # ✅ Exponential backoff
    # ... logs errors on failure
```

### 2. Improved File Reading (`safe_read_json` in `train_model_core.py`)

**Changes:**
- ✅ Retry logic for `PermissionError` (3 attempts with delays)
- ✅ Error logging for all failure types
- ✅ Handles JSON decode errors gracefully

### 3. Backup and Restore System

**New Functions:**
- `create_backup(path)` - Creates `.backup` file before modifications
- `restore_from_backup(path)` - Restores from backup if main file is corrupted

**Where Applied:**
- `ensure_train_data()` - Creates backup before initializing
- `sync_wayside_to_train_data()` - Creates backup before syncing
- `write_train_data()` in `train_model_ui.py` - Creates backup before writing

**Benefits:**
- If a write fails mid-operation, the previous valid state can be restored
- Prevents complete data loss from corruption
- Automatic recovery on next read if corruption detected

### 4. Enhanced Error Visibility

All file operations now log errors:
```
[WRITE ERROR] Failed to write train_data.json after 5 attempts: PermissionError(...)
[READ ERROR] Failed to read train_data.json after 3 attempts: PermissionError(...)
[BACKUP WARNING] Could not create backup: ...
[RESTORE] Restored train_data.json from backup
```

## Testing the Fix

### Before Running:
1. Delete any existing `.tmp` files in `Train_Model/` directory
2. Delete `train_data.json.backup` if you want a fresh start

### What to Look For:
1. **No more silent failures** - You'll see error messages if file locking occurs
2. **Power commands persist** - Check `train_data.json` for non-zero power values
3. **Backup files created** - Look for `train_data.json.backup`
4. **Fewer conflicts** - Exponential backoff reduces collision probability

### Monitor Console Output:
```bash
# Good - no errors
[SYNC SUCCESS] train_data.json synchronized.

# If you see this occasionally, it's OK (retries are working):
[WRITE ERROR] Failed to write train_data.json after 5 attempts: ...

# If you see this, the restore system is working:
[RESTORE] Restored train_data.json from backup
```

## Additional Recommendations

### 1. Reduce Write Frequency (Optional)
If you still see frequent conflicts, consider reducing how often the Train Model writes:

In `train_model_ui.py`, change the update interval:
```python
# Current: 500ms
self.after(500, self.update_loop)

# Slower: 1000ms (reduces conflicts)
self.after(1000, self.update_loop)
```

### 2. Use API Server (Recommended)
The unified API server (`unified_api_server.py`) centralizes all file access and eliminates most conflicts. Make sure all components use the API server when running in integrated mode.

### 3. File System Considerations (Windows)
Windows file locking is more aggressive than Unix systems. The fixes account for this, but:
- Avoid opening `train_data.json` in editors while system is running
- Disable antivirus real-time scanning for the project folder (if safe to do so)
- Use SSD instead of HDD for faster file operations

## Files Modified

1. **Train_Model/train_model_core.py**
   - `safe_write_json()` - Complete rewrite with better error handling
   - `safe_read_json()` - Added retry logic
   - `create_backup()` - New function
   - `restore_from_backup()` - New function
   - `ensure_train_data()` - Added backup/restore
   - `sync_wayside_to_train_data()` - Added backup creation

2. **Train_Model/train_model_ui.py**
   - `write_train_data()` - Added backup creation before writes

## Verification Steps

1. Run your system: `python combine_ctc_wayside_test.py`
2. Dispatch a train and set power commands
3. Check console for any `[WRITE ERROR]` or `[READ ERROR]` messages
4. Verify `train_data.json` contains your power commands:
   ```json
   "train_1": {
       "inputs": {
           "commanded speed": 4.47388,  // ✅ Non-zero
           "commanded authority": 976.9  // ✅ Non-zero
       }
   }
   ```
5. Check that `train_data.json.backup` exists and is recent

## What to Do If Issues Persist

If you still see power commands resetting to 0:

1. **Check the console output** for error messages
2. **Verify file permissions** - Make sure the user has write access to `Train_Model/`
3. **Check for file locks** - Use Process Explorer (Windows) to see what's locking the file
4. **Increase retry count** - In `safe_write_json`, change `max_retries = 5` to `max_retries = 10`
5. **Add more logging** - Set `DEBUG_MODE = True` in `train_controller_api.py`

## Summary

The fix addresses the root cause by:
- ✅ Making file writes more robust with retries and exponential backoff
- ✅ Using unique temp files to avoid process conflicts
- ✅ Adding backup/restore to prevent data loss
- ✅ Logging errors so you know when problems occur
- ✅ Handling Windows file locking behavior properly

Your power commands should now persist correctly, and you'll see clear error messages if any issues occur.

