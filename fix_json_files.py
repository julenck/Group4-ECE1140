"""Fix and initialize JSON files for the railway system.

This script creates missing JSON files and fixes corrupted ones.
Run this before starting the system if you encounter file errors.
"""

import json
import os

def create_file_if_missing(filepath, default_data):
    """Create a JSON file with default data if it doesn't exist or is corrupted."""
    try:
        # Check if file exists and is valid
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                json.load(f)  # Try to parse
            print(f"✓ {filepath} - OK")
            return
    except (json.JSONDecodeError, IOError):
        print(f"✗ {filepath} - Corrupted, recreating...")
    except Exception as e:
        print(f"✗ {filepath} - Error: {e}, recreating...")
    
    # Create or recreate the file
    try:
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(default_data, f, indent=4)
        print(f"✓ {filepath} - Created/Fixed")
    except Exception as e:
        print(f"✗ {filepath} - Failed to create: {e}")

def main():
    print("=" * 80)
    print("  RAILWAY SYSTEM JSON FILE FIXER")
    print("=" * 80)
    print()
    
    # CTC Data File
    ctc_data = {
        "Dispatcher": {
            "Trains": {
                "Train 1": {
                    "Line": "",
                    "Suggested Speed": "",
                    "Authority": "",
                    "Station Destination": "",
                    "Arrival Time": "",
                    "Position": "",
                    "State": "",
                    "Current Station": ""
                },
                "Train 2": {
                    "Line": "",
                    "Suggested Speed": "",
                    "Authority": "",
                    "Station Destination": "",
                    "Arrival Time": "",
                    "Position": "",
                    "State": "",
                    "Current Station": ""
                },
                "Train 3": {
                    "Line": "",
                    "Suggested Speed": "",
                    "Authority": "",
                    "Station Destination": "",
                    "Arrival Time": "",
                    "Position": "",
                    "State": "",
                    "Current Station": ""
                },
                "Train 4": {
                    "Line": "",
                    "Suggested Speed": "",
                    "Authority": "",
                    "Station Destination": "",
                    "Arrival Time": "",
                    "Position": "",
                    "State": "",
                    "Current Station": ""
                },
                "Train 5": {
                    "Line": "",
                    "Suggested Speed": "",
                    "Authority": "",
                    "Station Destination": "",
                    "Arrival Time": "",
                    "Position": "",
                    "State": "",
                    "Current Station": ""
                }
            }
        }
    }
    
    # CTC to Track Controller File
    ctc_track_controller = {
        "Trains": {
            "Train 1": {
                "Active": 0,
                "Suggested Authority": 0,
                "Suggested Speed": 0,
                "Train Position": None,
                "Train State": ""
            },
            "Train 2": {
                "Active": 0,
                "Suggested Authority": 0,
                "Suggested Speed": 0,
                "Train Position": None,
                "Train State": ""
            },
            "Train 3": {
                "Active": 0,
                "Suggested Authority": 0,
                "Suggested Speed": 0,
                "Train Position": None,
                "Train State": ""
            },
            "Train 4": {
                "Active": 0,
                "Suggested Authority": 0,
                "Suggested Speed": 0,
                "Train Position": None,
                "Train State": ""
            },
            "Train 5": {
                "Active": 0,
                "Suggested Authority": 0,
                "Suggested Speed": 0,
                "Train Position": None,
                "Train State": ""
            }
        },
        "Block Closure": [],
        "Switch Suggestion": [0, 0, 0, 0, 0, 0]
    }
    
    # Train States File
    train_states = {}
    
    # Wayside to Train File
    wayside_to_train = {
        "Train 1": {
            "Commanded Speed": 0,
            "Commanded Authority": 0,
            "Beacon": {
                "Current Station": "",
                "Next Station": ""
            },
            "Train Speed": 0
        },
        "Train 2": {
            "Commanded Speed": 0,
            "Commanded Authority": 0,
            "Beacon": {
                "Current Station": "",
                "Next Station": ""
            },
            "Train Speed": 0
        },
        "Train 3": {
            "Commanded Speed": 0,
            "Commanded Authority": 0,
            "Beacon": {
                "Current Station": "",
                "Next Station": ""
            },
            "Train Speed": 0
        },
        "Train 4": {
            "Commanded Speed": 0,
            "Commanded Authority": 0,
            "Beacon": {
                "Current Station": "",
                "Next Station": ""
            },
            "Train Speed": 0
        },
        "Train 5": {
            "Commanded Speed": 0,
            "Commanded Authority": 0,
            "Beacon": {
                "Current Station": "",
                "Next Station": ""
            },
            "Train Speed": 0
        }
    }
    
    # Create/fix files
    print("Checking and fixing files:")
    print()
    
    create_file_if_missing("ctc_data.json", ctc_data)
    create_file_if_missing("ctc_track_controller.json", ctc_track_controller)
    create_file_if_missing("train_controller/data/train_states.json", train_states)
    create_file_if_missing("track_controller/New_SW_Code/wayside_to_train.json", wayside_to_train)
    
    print()
    print("=" * 80)
    print("  DONE! All JSON files have been checked and fixed.")
    print("=" * 80)
    print()
    print("You can now run: python combine_ctc_wayside_test.py")

if __name__ == "__main__":
    main()

