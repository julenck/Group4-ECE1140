# Train States JSON Access Denied Fix (ADDITIONAL FIX)

## Problem Update

After fixing `train_data.json`, you encountered a **second issue** with `train_states.json`:

```
[READ ERROR] JSON decode error in train_states.json: Expecting value: line 1 column 1 (char 0)
```

This indicates the file was being corrupted (written as empty or partial) due to the same file locking issues.

## Root Cause (Same Issue, Different File)

`train_states.json` had the **same problems** as `train_data.json`:
- Multiple processes writing simultaneously
- Direct writes without atomic operations
- Silent failures on `PermissionError`
- No backup/restore mechanism
- JSON decode errors not always logged

## Fixes Applied to `train_controller_api.py`

### 1. New Safe Write Function (`_safe_write_json`)

**Features:**
- ✅ Unique temporary files per process (no conflicts)
- ✅ 5 retries with exponential backoff (50ms → 800ms)
- ✅ Atomic writes with `fsync()`
- ✅ Error logging (no more silent failures)
- ✅ Returns success/failure status

```python
def _safe_write_json(path: str, data: dict) -> bool:
    # Uses tempfile.mkstemp() for unique temp files
    # Exponential backoff on PermissionError
    # Logs all errors
    # Returns True/False for success tracking
```

### 2. Backup/Restore Functions

**New Functions:**
- `_create_backup(path)` - Creates `.backup` before modifications
- `_restore_from_backup(path)` - Restores from backup if corruption detected

**Where Applied:**
- Before every `save_state()` call
- Automatic restore on JSON decode errors in `get_state()`

### 3. Enhanced Error Logging in `get_state()`

**Before:**
```python
except json.JSONDecodeError as e:
    if DEBUG_MODE:  # ❌ Only logs if debug enabled
        print(f"JSON decode error: {e}")
```

**After:**
```python
except json.JSONDecodeError as e:
    # ✅ ALWAYS log JSON errors
    print(f"[READ ERROR] JSON decode error in {self.state_file}: {e}")
    
    # ✅ Try to restore from backup on first attempt
    if attempt == 0:
        print(f"[RESTORE] Attempting to restore from backup...")
        if _restore_from_backup(self.state_file):
            continue  # Retry after restore
    
    # ✅ Use cached state if available
    if self._cached_state is not None:
        print(f"[CACHE] Using cached state due to JSON error")
        return self._cached_state.copy()
```

### 4. Improved `save_state()` Method

**Changes:**
- ✅ Creates backup before every write
- ✅ Uses `_safe_write_json()` for atomic writes
- ✅ Attempts restore from backup if read fails
- ✅ Logs all errors (no silent failures)
- ✅ Tracks write success/failure

**Error Flow:**
```
save_state() called
    ↓
Create backup
    ↓
Try to read existing state
    ↓ (if corrupted)
Restore from backup
    ↓
Merge new state
    ↓
Write with _safe_write_json()
    ↓ (retry up to 5 times)
Success or logged error
```

## Files Modified

**train_controller/api/train_controller_api.py:**
1. Added imports: `tempfile`, `shutil`
2. Added `_safe_write_json()` function
3. Added `_create_backup()` function
4. Added `_restore_from_backup()` function
5. Updated `get_state()` - Always log errors, auto-restore from backup
6. Updated `save_state()` - Use atomic writes, create backups, better error handling

## Testing the Complete Fix

### Before Running:
1. Delete any existing `.tmp` files:
   ```bash
   Remove-Item Train_Model\*.tmp
   Remove-Item train_controller\data\*.tmp
   ```

2. Delete old backup files if you want fresh backups:
   ```bash
   Remove-Item Train_Model\train_data.json.backup
   Remove-Item train_controller\data\train_states.json.backup
   ```

### What to Look For:

#### ✅ Good Signs:
- No `[READ ERROR]` or `[WRITE ERROR]` messages
- Both backup files exist:
  - `Train_Model/train_data.json.backup`
  - `train_controller/data/train_states.json.backup`
- Power commands are non-zero
- Train responds to commands
- No JSON decode errors

#### ⚠️ Warning Signs (But OK if occasional):
- Occasional `[WRITE ERROR]` (< 1% of writes)
- `[CACHE] Using cached state` message (means retry worked)

#### ❌ Critical Issues:
- Frequent `[READ ERROR]` or `[WRITE ERROR]` (> 10%)
- `[RESTORE ERROR]` messages
- No backup files created
- Power commands still 0

### Monitor Console Output:

```bash
python combine_ctc_wayside_test.py 2>&1 | Select-String "ERROR|RESTORE|CACHE|BACKUP"
```

**What You Should See:**
```
# Good - system working normally
[API INIT] Initializing train_controller_api for train_id=1
[API INIT] State saved successfully

# Acceptable - backup system working
[BACKUP WARNING] Could not create backup... (very rare)

# Good recovery - restore working
[READ ERROR] JSON decode error...
[RESTORE] Attempting to restore from backup...
[RESTORE] Restored train_states.json from backup

# Temporary solution - cache working
[CACHE] Using cached state due to JSON error
```

## Verification Steps

### 1. Check Both Files Exist:
```powershell
Test-Path Train_Model\train_data.json
Test-Path train_controller\data\train_states.json
Test-Path Train_Model\train_data.json.backup
Test-Path train_controller\data\train_states.json.backup
```

All should return `True`

### 2. Verify Files Are Not Empty:
```powershell
(Get-Item Train_Model\train_data.json).Length
(Get-Item train_controller\data\train_states.json).Length
```

Both should be > 100 bytes

### 3. Check File Contents:
```powershell
# Check train_data.json for non-zero power
Get-Content Train_Model\train_data.json | Select-String "commanded speed"

# Check train_states.json is valid JSON
Get-Content train_controller\data\train_states.json | ConvertFrom-Json
```

### 4. Monitor File Updates:
```powershell
# Watch both files for changes
while ($true) {
    Get-Item Train_Model\train_data.json, train_controller\data\train_states.json | 
        Select-Object Name, LastWriteTime
    Start-Sleep -Seconds 1
}
```

Both should update regularly (every 0.5-1 second)

## Error Messages Explained

### `[READ ERROR] JSON decode error in train_states.json: Expecting value: line 1 column 1`

**Meaning:** File is empty or corrupted

**What happens:**
1. System logs the error (you see it!)
2. Attempts to restore from backup
3. If restore succeeds, continues normally
4. If restore fails, uses cached state
5. Next write creates new backup

**User action:** Usually none - system self-recovers

### `[WRITE ERROR] Failed to write train_states.json after 5 attempts`

**Meaning:** File locked by another process for > 1.5 seconds

**What happens:**
1. Error is logged (you see it!)
2. Data is NOT saved (but old data preserved)
3. Next update will retry

**User action:** 
- Check if file is open in editor
- Check if antivirus is scanning it
- If frequent, increase max_retries

### `[RESTORE] Restored train_states.json from backup`

**Meaning:** File was corrupted, backup was used

**What happens:**
1. System detected corruption
2. Restored last known good state
3. Continues normally

**User action:** None - this is good! The safety system worked.

### `[CACHE] Using cached state due to JSON error`

**Meaning:** Couldn't read file, using in-memory cache

**What happens:**
1. Read failed (file locked or corrupted)
2. Using last successfully read state
3. Will try to write on next save_state()

**User action:** None - temporary workaround, will self-correct

## Both Files Now Protected

### train_data.json (Train Model)
- ✅ Atomic writes with unique temp files
- ✅ 5 retries with exponential backoff
- ✅ Backup/restore system
- ✅ Error logging
- Location: `Train_Model/train_data.json`

### train_states.json (Train Controller)
- ✅ Atomic writes with unique temp files
- ✅ 5 retries with exponential backoff
- ✅ Backup/restore system
- ✅ Error logging
- ✅ Auto-restore on corruption
- Location: `train_controller/data/train_states.json`

## If Issues Persist

### For train_states.json Specifically:

1. **Enable DEBUG_MODE:**
   ```python
   # In train_controller/api/train_controller_api.py
   DEBUG_MODE = True  # Line 14
   ```

2. **Check backup exists:**
   ```bash
   Test-Path train_controller\data\train_states.json.backup
   ```

3. **Manually restore from backup:**
   ```bash
   Copy-Item train_controller\data\train_states.json.backup train_controller\data\train_states.json
   ```

4. **Check for file locks:**
   ```bash
   handle.exe train_states.json
   ```

5. **Increase retry count:**
   ```python
   # In _safe_write_json() function
   max_retries = 10  # Was 5
   ```

### For Both Files:

1. Close any editors that might have the files open
2. Disable antivirus real-time scanning for project folder
3. Use SSD instead of HDD if possible
4. Ensure you have write permissions to the directories
5. Check disk space (Windows needs temp space for atomic writes)

## Summary of Complete Fix

**Both Critical JSON Files Now Protected:**

| Feature | train_data.json | train_states.json |
|---------|----------------|-------------------|
| Atomic writes | ✅ | ✅ |
| Unique temp files | ✅ | ✅ |
| Exponential backoff | ✅ | ✅ |
| 5 retries | ✅ | ✅ |
| Backup creation | ✅ | ✅ |
| Auto-restore | ✅ | ✅ |
| Error logging | ✅ | ✅ |
| Cache fallback | ❌ | ✅ |

Your railway system should now be **much more resilient** to file locking issues! 🚂✅

## Related Documentation

- `TRAIN_DATA_JSON_FIX.md` - Original fix for train_data.json
- `MONITOR_FILE_LOCKS.md` - Monitoring and troubleshooting guide
- `QUICK_FIX_SUMMARY.txt` - Quick reference
- `FILE_LOCK_SOLUTION_DIAGRAM.txt` - Visual diagrams

