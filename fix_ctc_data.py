#!/usr/bin/env python3
"""
Quick fix script for ctc_data.json if it becomes malformed.
Run this if you see JSON errors related to extra closing braces.
"""

import json
import os

def fix_ctc_data():
    """Fix ctc_data.json by removing extra closing braces and validating structure."""
    file_path = 'ctc_data.json'
    
    print(f"Attempting to fix {file_path}...")
    
    # Read the file
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: {file_path} not found!")
        return False
    
    # Count braces
    open_braces = content.count('{')
    close_braces = content.count('}')
    print(f"Found {open_braces} opening braces and {close_braces} closing braces")
    
    # Try to parse as-is first
    try:
        data = json.loads(content)
        print("JSON is already valid!")
        return True
    except json.JSONDecodeError as e:
        print(f"JSON is malformed: {e}")
        print("Attempting to fix...")
    
    # Remove extra closing braces from the end
    content = content.rstrip()
    while close_braces > open_braces:
        if content.endswith('}'):
            content = content[:-1].rstrip()
            close_braces = content.count('}')
            print(f"Removed extra closing brace. Now have {content.count('}')} closing braces")
        else:
            break
    
    # Try to parse again
    try:
        data = json.loads(content)
        print("✓ Fixed! JSON is now valid")
        
        # Write the fixed version back
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"✓ Saved fixed version to {file_path}")
        return True
        
    except json.JSONDecodeError as e:
        print(f"✗ Could not fix automatically: {e}")
        print("\nCreating fresh default structure...")
        
        # Create default structure
        default_data = {
            "Dispatcher": {
                "Trains": {
                    f"Train {i}": {
                        "Line": "",
                        "Suggested Speed": "",
                        "Authority": "",
                        "Station Destination": "",
                        "Arrival Time": "",
                        "Position": 0,
                        "State": 0,
                        "Current Station": ""
                    }
                    for i in range(1, 6)
                }
            }
        }
        
        with open(file_path, 'w') as f:
            json.dump(default_data, f, indent=4)
        print(f"✓ Created fresh {file_path} with default structure")
        print("⚠ All train data has been reset!")
        return True

if __name__ == "__main__":
    fix_ctc_data()

