# Train Controller Automatic Dispatch Setup

## Overview
The CTC now automatically dispatches train controllers when you dispatch a train. No popup window required!

## How It Works

### Automatic Controller Selection
When you dispatch a train from the CTC:

1. **First Train** → Automatically uses **Hardware Controller** (`train_controller_hw_ui.py`)
   - Designed for Raspberry Pi with GPIO/I2C hardware
   - **Testing Mode**: UI opens locally on PC (no Raspberry Pi needed for testing)
   - For production: Can be configured to run on Raspberry Pi
   
2. **All Subsequent Trains** → Automatically use **Software Controller** (`train_controller_sw_ui.py`)
   - Pure software implementation with UI buttons
   - Runs entirely on the PC

### Usage Instructions

#### Running the System

1. **Start the integrated system:**
   ```bash
   python combine_ctc_wayside_test.py
   ```

2. **Dispatch trains from CTC:**
   - Go to CTC UI → Manual tab
   - Fill in train details (Train, Line, Destination, Arrival Time)
   - Click "Dispatch"
   - Train controller will automatically appear!

#### First Train (Hardware - Local Testing)

When you dispatch the **first train**, you'll see:
- Train Model UI appears on your PC
- **Hardware Controller UI appears on your PC** (local testing mode)
- Console shows: `"Train 1 controller is LOCAL (will open on PC)"`

Both UIs run on your PC for testing. The hardware controller will display "GPIOZERO/I2C NOT AVAILABLE" messages since you're not on a Raspberry Pi - this is normal for testing!

**For Production (Raspberry Pi):**
To run on actual Raspberry Pi hardware, change `is_remote = False` to `is_remote = True` in `train_manager.py` line 1217.

#### Subsequent Trains (Software)

When you dispatch **train 2, 3, 4, etc.**, you'll see:
- Train Model UI appears on your PC
- Train Controller UI appears on your PC (software version)
- Both run locally, no Raspberry Pi needed

### Technical Details

#### Modified Files

1. **`ctc/ctc_ui_temp.py`**
   - Removed Train Manager UI popup window
   - Added automatic call to `dispatch_train_from_ctc()`
   - Maintains persistent `TrainManager` instance to track train count

2. **`train_controller/train_manager.py`**
   - Function `dispatch_train_from_ctc()` handles automatic selection
   - First train: `use_hardware=True, is_remote=True`
   - Subsequent trains: `use_hardware=False, is_remote=False`
   - Cleaned up debug output

#### Train Manager Function

The `dispatch_train_from_ctc()` function in `train_manager.py` (lines 1192-1244):
```python
def dispatch_train_from_ctc(train_manager=None, server_url=None):
    # Get train count
    existing_train_count = train_manager.get_train_count()
    
    if existing_train_count == 0:
        # First train: Hardware controller (Raspberry Pi)
        controller_type = "hardware_remote"
        use_hardware = True
        is_remote = True
    else:
        # Subsequent trains: Software controller
        controller_type = "software"
        use_hardware = False
        is_remote = False
    
    # Create train with appropriate controller
    train_id = train_manager.add_train(
        create_uis=True,
        use_hardware=use_hardware,
        is_remote=is_remote,
        server_url=server_url
    )
    
    return (train_id, controller_type)
```

### Testing

To verify the setup works:

1. **Test automatic dispatch:**
   ```bash
   python combine_ctc_wayside_test.py
   ```
   
2. **Dispatch first train** - Should see hardware controller message
3. **Dispatch second train** - Should see software controller appear
4. **Verify console output:**
   ```
   [CTC] TrainManager initialized - ready to dispatch trains
   [CTC] First train will use HARDWARE controller (Raspberry Pi)
   [CTC] Subsequent trains will use SOFTWARE controllers
   ...
   [TrainManager] Using HARDWARE controller for train 1 (REMOTE - Raspberry Pi)
   [CTC] Successfully dispatched Train 1 with hardware_remote controller
   ...
   [TrainManager] Using SOFTWARE controller for train 2
   [CTC] Successfully dispatched Train 2 with software controller
   ```

### Troubleshooting

**Issue:** Train controller doesn't appear
- Check console for error messages
- Verify TrainManager initialized successfully at startup

**Issue:** Can't import hardware UI
- Ensure `train_controller_hardware.py` exists in `train_controller/` folder
- Check for any import errors in console

**Issue:** Raspberry Pi can't connect
- Verify server IP address is correct
- Check that port 5000 is not blocked by firewall
- Make sure both PC and Raspberry Pi are on same network

### Notes

- The Train Manager UI popup is no longer used for CTC dispatch
- You can still manually run Train Manager UI for testing: `python train_controller/train_manager.py`
- Train count persists during CTC session but resets when you restart the program
- Each train gets a unique Train ID (1, 2, 3, etc.)

## File Structure

```
Group4-ECE1140/
├── combine_ctc_wayside_test.py          # Main launcher
├── ctc/
│   └── ctc_ui_temp.py                   # CTC UI (modified)
├── train_controller/
│   ├── train_manager.py                 # Train management (modified)
│   └── ui/
│       ├── train_controller_hw_ui.py    # Hardware controller (Raspberry Pi)
│       └── train_controller_sw_ui.py    # Software controller (PC)
└── Train_Model/
    ├── train_model_core.py              # Train physics
    └── train_model_ui.py                # Train Model UI
```

