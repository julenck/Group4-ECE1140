"""Test script to verify both UIs open when creating a train."""

import sys
import os

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(parent_dir)

import tkinter as tk
from train_manager import TrainManager

def main():
    """Test creating a train with both UIs."""
    print("Creating TrainManager...")
    manager = TrainManager()
    
    print("\nCreating Train 1 with UIs...")
    train_id = manager.add_train(create_uis=True)
    
    train = manager.get_train(train_id)
    print(f"\nTrain {train_id} created:")
    print(f"  Model: {train.model}")
    print(f"  Controller: {train.controller}")
    print(f"  Model UI: {train.model_ui}")
    print(f"  Controller UI: {train.controller_ui}")
    
    if train.model_ui:
        print(f"  Model UI title: '{train.model_ui.title()}'")
        print(f"  Model UI geometry: {train.model_ui.geometry()}")
    
    if train.controller_ui:
        print(f"  Controller UI title: '{train.controller_ui.title()}'")
        print(f"  Controller UI geometry: {train.controller_ui.geometry()}")
    
    print("\n✓ Both UIs should now be visible!")
    print("Close any window to exit...")
    
    # Run mainloop to keep windows open
    if train.model_ui:
        train.model_ui.mainloop()

if __name__ == "__main__":
    main()
