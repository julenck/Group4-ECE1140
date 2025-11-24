"""Test script to verify multi-train JSON section reading/writing. """

import sys
import os
import json
import time

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(parent_dir)

from api.train_controller_api import train_controller_api

def print_json_state():
    """Print current JSON file state"""
    with open('data/train_states.json', 'r') as f:
        data = json.load(f)
    
    print("\n=== Current JSON Structure ===")
    for key in data.keys():
        # Only look for train_1, train_2, etc (with underscore followed by digit)
        if key.startswith('train_') and len(key) > 6 and key[6:].isdigit():
            print(f"\n{key}:")
            train_data = data[key]
            if isinstance(train_data, dict):
                print(f"  train_id: {train_data.get('train_id', 'N/A')}")
                print(f"  driver_velocity: {train_data.get('driver_velocity', 'N/A')}")
                print(f"  train_velocity: {train_data.get('train_velocity', 'N/A')}")
                print(f"  set_temperature: {train_data.get('set_temperature', 'N/A')}")
    print("=" * 50)

def main():
    print("Testing multi-train JSON sections...")
    
    # Create APIs for 3 different trains
    api1 = train_controller_api(train_id=1)
    api2 = train_controller_api(train_id=2)
    api3 = train_controller_api(train_id=3)
    
    print("\n1. Setting different values for each train...")
    
    # Set different values for each train
    api1.update_state({'driver_velocity': 10.0, 'set_temperature': 72.0})
    api2.update_state({'driver_velocity': 20.0, 'set_temperature': 68.0})
    api3.update_state({'driver_velocity': 30.0, 'set_temperature': 75.0})
    
    print_json_state()
    
    print("\n2. Reading back values to verify isolation...")
    
    state1 = api1.get_state()
    state2 = api2.get_state()
    state3 = api3.get_state()
    
    print(f"\nTrain 1 - driver_velocity: {state1['driver_velocity']}, set_temp: {state1['set_temperature']}")
    print(f"Train 2 - driver_velocity: {state2['driver_velocity']}, set_temp: {state2['set_temperature']}")
    print(f"Train 3 - driver_velocity: {state3['driver_velocity']}, set_temp: {state3['set_temperature']}")
    
    # Verify isolation
    success = True
    if state1['driver_velocity'] != 10.0 or state1['set_temperature'] != 72.0:
        print("❌ Train 1 values incorrect!")
        success = False
    
    if state2['driver_velocity'] != 20.0 or state2['set_temperature'] != 68.0:
        print("❌ Train 2 values incorrect!")
        success = False
    
    if state3['driver_velocity'] != 30.0 or state3['set_temperature'] != 75.0:
        print("❌ Train 3 values incorrect!")
        success = False
    
    if success:
        print("\n✅ SUCCESS! Each train is reading/writing to its own JSON section!")
    else:
        print("\n❌ FAILED! Trains are interfering with each other!")
    
    print("\n3. Testing update isolation...")
    
    # Update only train 2
    api2.update_state({'driver_velocity': 25.0})
    
    state1_after = api1.get_state()
    state2_after = api2.get_state()
    state3_after = api3.get_state()
    
    if state1_after['driver_velocity'] == 10.0 and state2_after['driver_velocity'] == 25.0 and state3_after['driver_velocity'] == 30.0:
        print("✅ Update isolation verified! Only train 2 was updated.")
    else:
        print("❌ Update isolation failed!")
        print(f"Train 1: {state1_after['driver_velocity']} (expected 10.0)")
        print(f"Train 2: {state2_after['driver_velocity']} (expected 25.0)")
        print(f"Train 3: {state3_after['driver_velocity']} (expected 30.0)")
    
    print_json_state()

if __name__ == "__main__":
    main()
