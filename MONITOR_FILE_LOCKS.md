# Monitoring File Lock Issues

## Quick Diagnostic Commands

### Check if train_data.json is being updated
```bash
# Windows PowerShell - Watch file modification time
while ($true) { 
    Get-Item Train_Model\train_data.json | Select-Object Name, LastWriteTime
    Start-Sleep -Seconds 1
}
```

### Check for temporary files (indicates write attempts)
```bash
# Windows PowerShell
Get-ChildItem Train_Model\*.tmp
```

### View recent console errors
```bash
# Run your system and grep for errors
python combine_ctc_wayside_test.py 2>&1 | Select-String "ERROR|WRITE|READ|BACKUP|RESTORE"
```

## What to Look For

### Good Signs ✅
- `train_data.json.backup` exists and is recent
- No `.tmp` files lingering (they should be cleaned up immediately)
- Console shows no `[WRITE ERROR]` messages
- Power commands in `train_data.json` are non-zero and changing

### Warning Signs ⚠️
- Multiple `.tmp` files exist
- `[WRITE ERROR]` appears occasionally (< 1% of writes)
- Backup file is old (> 5 minutes)

### Critical Issues ❌
- `[WRITE ERROR]` appears frequently (> 10% of writes)
- Power commands stuck at 0
- `train_data.json` not updating (LastWriteTime not changing)
- No backup file created

## Real-Time Monitoring Script

Save this as `monitor_train_data.py`:

```python
import os
import json
import time
from datetime import datetime

TRAIN_DATA_FILE = "Train_Model/train_data.json"

def monitor():
    print("Monitoring train_data.json for changes...")
    print("Press Ctrl+C to stop\n")
    
    last_mtime = 0
    last_power = None
    write_count = 0
    
    while True:
        try:
            if os.path.exists(TRAIN_DATA_FILE):
                mtime = os.path.getmtime(TRAIN_DATA_FILE)
                
                if mtime != last_mtime:
                    write_count += 1
                    last_mtime = mtime
                    
                    # Read current power command
                    with open(TRAIN_DATA_FILE, 'r') as f:
                        data = json.load(f)
                        power = data.get("train_1", {}).get("inputs", {}).get("commanded speed", 0)
                    
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    
                    if power != last_power:
                        print(f"[{timestamp}] Write #{write_count} - Power changed: {last_power} -> {power}")
                        last_power = power
                    else:
                        print(f"[{timestamp}] Write #{write_count} - Power unchanged: {power}")
                    
                    # Check for backup
                    backup_exists = os.path.exists(TRAIN_DATA_FILE + ".backup")
                    print(f"              Backup exists: {backup_exists}")
            
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            print(f"\n\nTotal writes detected: {write_count}")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    monitor()
```

Run it in a separate terminal while your system is running:
```bash
python monitor_train_data.py
```

## Windows-Specific: Find What's Locking the File

### Using PowerShell (built-in)
```powershell
# Get processes with open handles to the file
$file = "C:\Projects\Group4-ECE1140\Train_Model\train_data.json"
Get-Process | Where-Object {
    $_.Modules.FileName -contains $file
}
```

### Using Handle.exe (Sysinternals)
```bash
# Download from: https://docs.microsoft.com/en-us/sysinternals/downloads/handle
handle.exe train_data.json
```

### Using Process Explorer (GUI)
1. Download from: https://docs.microsoft.com/en-us/sysinternals/downloads/process-explorer
2. Run as Administrator
3. Press Ctrl+F and search for "train_data.json"
4. Shows which process has the file open

## Troubleshooting by Error Message

### `[WRITE ERROR] Failed to write train_data.json after 5 attempts`

**Cause:** File is locked by another process for > 1.5 seconds

**Solutions:**
1. Check if you have the file open in an editor - close it
2. Check if antivirus is scanning it - add exception
3. Increase retry count in `train_model_core.py`:
   ```python
   max_retries = 10  # Was 5
   ```

### `[READ ERROR] Failed to read train_data.json after 3 attempts`

**Cause:** File is being written while trying to read

**Solutions:**
1. This is usually OK - the code will retry
2. If frequent, reduce write frequency in `train_model_ui.py`

### `[RESTORE] Restored train_data.json from backup`

**Cause:** Main file was corrupted, backup was used

**Solutions:**
1. This is good - the backup system worked!
2. Check what caused corruption (crash? force quit?)
3. Ensure proper shutdown of all processes

### Power command stuck at 0

**Debugging steps:**
1. Check if Train Controller is running:
   ```python
   # In train_controller_api.py, set:
   DEBUG_MODE = True
   ```
2. Check `train_states.json` for power_command value
3. Verify wayside is sending commands (check `wayside_to_train.json`)
4. Add print statement in train controller:
   ```python
   power = self.calculate_power_command(state)
   print(f"[DEBUG] Calculated power: {power}")
   ```

## Performance Metrics

### Expected Write Frequency
- Train Model UI: ~2 writes/second (500ms interval)
- Wayside Sync: ~1 write/second when active
- Total: ~3-5 writes/second

### Expected Retry Rate
- < 1% of writes should need retries
- < 0.1% should fail after all retries

### File Size
- `train_data.json`: 5-15 KB (depending on number of trains)
- `train_data.json.backup`: Same size as main file

## Emergency Recovery

If `train_data.json` is completely corrupted:

```bash
# 1. Stop all processes
# 2. Restore from backup
copy Train_Model\train_data.json.backup Train_Model\train_data.json

# 3. If no backup, reset with fix_json_files.py
python fix_json_files.py

# 4. Restart system
python combine_ctc_wayside_test.py
```

## Contact/Support

If issues persist after trying all solutions:
1. Capture console output with errors
2. Share `train_data.json` and `train_data.json.backup`
3. Note which processes are running (CTC, Wayside, Train Controller, etc.)
4. Provide Windows version and Python version

