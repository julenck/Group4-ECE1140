"""
Test script to verify JSON file fixes are working correctly.
Run this to check if both train_data.json and train_states.json
are protected from access denied errors and corruption.
"""

import os
import json
import time
from datetime import datetime

def check_file_exists(path):
    """Check if file exists and is not empty."""
    if not os.path.exists(path):
        return False, "File does not exist"
    
    size = os.path.getsize(path)
    if size == 0:
        return False, "File is empty"
    
    return True, f"File exists ({size} bytes)"

def check_json_valid(path):
    """Check if file contains valid JSON."""
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return True, f"Valid JSON ({len(str(data))} chars)"
    except json.JSONDecodeError as e:
        return False, f"JSON decode error: {e}"
    except Exception as e:
        return False, f"Error reading: {e}"

def check_backup_exists(path):
    """Check if backup file exists."""
    backup_path = path + ".backup"
    if not os.path.exists(backup_path):
        return False, "No backup file"
    
    size = os.path.getsize(backup_path)
    if size == 0:
        return False, "Backup is empty"
    
    return True, f"Backup exists ({size} bytes)"

def check_power_command(path):
    """Check if train_data.json has non-zero power command."""
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        
        # Check train_1 section
        if "train_1" in data:
            inputs = data["train_1"].get("inputs", {})
            cmd_speed = inputs.get("commanded speed", 0)
            cmd_auth = inputs.get("commanded authority", 0)
            
            if cmd_speed != 0 or cmd_auth != 0:
                return True, f"Power detected: speed={cmd_speed:.2f}, auth={cmd_auth:.2f}"
            else:
                return False, "Power commands are 0"
        else:
            return None, "No train_1 section found (train may not be dispatched yet)"
    except Exception as e:
        return False, f"Error checking power: {e}"

def check_train_state(path):
    """Check if train_states.json has valid structure."""
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        
        if "train_1" in data:
            section = data["train_1"]
            has_inputs = "inputs" in section
            has_outputs = "outputs" in section
            
            if has_inputs and has_outputs:
                return True, f"Valid structure (inputs + outputs)"
            else:
                return False, f"Missing sections: inputs={has_inputs}, outputs={has_outputs}"
        else:
            return None, "No train_1 section (train may not be created yet)"
    except Exception as e:
        return False, f"Error checking state: {e}"

def print_result(test_name, status, message):
    """Print test result with color coding."""
    if status is True:
        symbol = "✅"
    elif status is False:
        symbol = "❌"
    else:
        symbol = "⚠️ "
    
    print(f"  {symbol} {test_name}: {message}")

def main():
    print("=" * 80)
    print("  JSON FILE FIX VERIFICATION TEST")
    print("=" * 80)
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Define file paths
    train_data_file = "Train_Model/train_data.json"
    train_states_file = "train_controller/data/train_states.json"
    
    # Test train_data.json
    print("Testing train_data.json:")
    print("-" * 80)
    
    status, msg = check_file_exists(train_data_file)
    print_result("File exists", status, msg)
    
    if status:
        status, msg = check_json_valid(train_data_file)
        print_result("Valid JSON", status, msg)
        
        status, msg = check_backup_exists(train_data_file)
        print_result("Backup exists", status, msg)
        
        status, msg = check_power_command(train_data_file)
        print_result("Power command", status, msg)
    
    print()
    
    # Test train_states.json
    print("Testing train_states.json:")
    print("-" * 80)
    
    status, msg = check_file_exists(train_states_file)
    print_result("File exists", status, msg)
    
    if status:
        status, msg = check_json_valid(train_states_file)
        print_result("Valid JSON", status, msg)
        
        status, msg = check_backup_exists(train_states_file)
        print_result("Backup exists", status, msg)
        
        status, msg = check_train_state(train_states_file)
        print_result("State structure", status, msg)
    
    print()
    
    # Check for temporary files (should be cleaned up)
    print("Checking for leftover temp files:")
    print("-" * 80)
    
    train_model_tmp = [f for f in os.listdir("Train_Model") if f.endswith(".tmp")]
    if train_model_tmp:
        print(f"  ⚠️  Found {len(train_model_tmp)} .tmp files in Train_Model/")
        for f in train_model_tmp[:5]:  # Show first 5
            print(f"     - {f}")
    else:
        print(f"  ✅ No .tmp files in Train_Model/ (good!)")
    
    if os.path.exists("train_controller/data"):
        train_controller_tmp = [f for f in os.listdir("train_controller/data") if f.endswith(".tmp")]
        if train_controller_tmp:
            print(f"  ⚠️  Found {len(train_controller_tmp)} .tmp files in train_controller/data/")
            for f in train_controller_tmp[:5]:
                print(f"     - {f}")
        else:
            print(f"  ✅ No .tmp files in train_controller/data/ (good!)")
    
    print()
    print("=" * 80)
    print("  TEST COMPLETE")
    print("=" * 80)
    print()
    print("Interpretation:")
    print("  ✅ = Test passed - everything looks good")
    print("  ⚠️  = Warning - may be normal if train not dispatched yet")
    print("  ❌ = Test failed - needs attention")
    print()
    print("If you see ❌ errors:")
    print("  1. Make sure system is running (python combine_ctc_wayside_test.py)")
    print("  2. Dispatch a train from the CTC UI")
    print("  3. Run this test again after 10-15 seconds")
    print()
    print("If errors persist:")
    print("  - Check console for [READ ERROR] or [WRITE ERROR] messages")
    print("  - See TRAIN_DATA_JSON_FIX.md and TRAIN_STATES_JSON_FIX.md")
    print("  - Try running: python fix_json_files.py")
    print()

if __name__ == "__main__":
    main()

