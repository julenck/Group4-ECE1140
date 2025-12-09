# CTC Controller Type Selector Feature

## Overview
The CTC UI now includes a **Controller Type** dropdown that lets you manually choose whether to dispatch trains with Software (PC) or Hardware (Raspberry Pi) controllers.

---

## How to Use

### In the CTC UI - Manual Tab

When dispatching a train, you'll now see a new dropdown:

```
┌─────────────────────────────────────────────────┐
│ Select a Train to Dispatch   │ Train 1         │
│ Select a Line                │ Green           │
│ Select a Destination Station │ Mt. Lebanon     │
│ Enter Arrival Time           │ 17:30           │
│ Controller Type:             │ Software (PC) ▼ │  ← NEW!
│                                                 │
│              [DISPATCH]                         │
└─────────────────────────────────────────────────┘
```

### Controller Type Options

**1. Software (PC)** [Default]
- Runs entirely on your main computer
- Virtual buttons in UI
- No Raspberry Pi needed
- Good for testing and multi-train scenarios

**2. Hardware (Raspberry Pi)**
- Runs on Raspberry Pi with physical buttons
- Requires Raspberry Pi setup
- Real GPIO/I2C hardware interface
- Production deployment mode

---

## Usage Examples

### Example 1: All Software Controllers (Testing)
```
Dispatch Train 1: Controller Type = "Software (PC)"
Dispatch Train 2: Controller Type = "Software (PC)"
Dispatch Train 3: Controller Type = "Software (PC)"
```
**Result:** All 3 trains run on your PC with software UIs

---

### Example 2: All Hardware Controllers (Production)
```
Dispatch Train 1: Controller Type = "Hardware (Raspberry Pi)"
Dispatch Train 2: Controller Type = "Hardware (Raspberry Pi)"
```
**Result:** 
- Train 1 Train Model on PC, Controller on Raspberry Pi #1
- Train 2 Train Model on PC, Controller on Raspberry Pi #2

**Note:** You'll need to manually start each hardware controller on its respective Raspberry Pi using the command shown in the popup.

---

### Example 3: Mixed Controllers
```
Dispatch Train 1: Controller Type = "Hardware (Raspberry Pi)"
Dispatch Train 2: Controller Type = "Software (PC)"
Dispatch Train 3: Controller Type = "Hardware (Raspberry Pi)"
```
**Result:** 
- Train 1: Hardware controller (Raspberry Pi #1)
- Train 2: Software controller (PC)
- Train 3: Hardware controller (Raspberry Pi #2)

---

## What Happens When You Dispatch

### Software Controller Selected:
1. Train Model UI appears on your PC
2. Train Controller UI appears on your PC (software version)
3. Both run locally - ready to use immediately!

### Hardware Controller Selected:
1. Train Model UI appears on your PC
2. Popup message appears with Raspberry Pi setup instructions
3. You need to run the command on Raspberry Pi to start the hardware controller

**Popup Example:**
```
╔════════════════════════════════════════════╗
║ Train 1 - Remote Hardware Setup           ║
╠════════════════════════════════════════════╣
║ Train 1 Model created on this server!     ║
║                                            ║
║ Hardware Controller must run on            ║
║ Raspberry Pi.                              ║
║                                            ║
║ ═══════════════════════════════════════    ║
║ On Raspberry Pi, run:                      ║
║                                            ║
║ cd train_controller/ui                     ║
║ python train_controller_hw_ui.py \         ║
║   --train-id 1 \                           ║
║   --server http://192.168.1.100:5000       ║
║                                            ║
║ ═══════════════════════════════════════    ║
╚════════════════════════════════════════════╝
```

---

## Technical Details

### CTC UI Changes

**File:** `ctc/ctc_ui_temp.py`

**Added:**
- Controller type dropdown in Manual tab (row 2)
- Values: "Software (PC)" or "Hardware (Raspberry Pi)"
- Default: "Software (PC)"
- State: Read-only (prevents typos)

**Modified:**
- Dispatch button moved from row 2 → row 3
- Dispatch logic reads dropdown value and converts to controller type
- Passes controller_type to `dispatch_train_from_ctc()`

### Train Manager Changes

**File:** `train_controller/train_manager.py`

**Modified Function:** `dispatch_train_from_ctc()`

**New Parameter:**
```python
controller_type: "software" or "hardware_remote" (if None, auto-selects)
```

**Behavior:**
- If `controller_type=None`: Auto-selects (first=hardware, rest=software) - legacy behavior
- If `controller_type="software"`: Uses software controller
- If `controller_type="hardware_remote"`: Uses hardware controller

**Backward Compatible:** Existing calls without the parameter still work!

---

## Testing

### Test 1: Dispatch with Software Controller
1. Start system: `python combine_ctc_wayside_test.py`
2. In CTC → Manual tab
3. Select "Software (PC)" in Controller Type dropdown
4. Fill in train details and click DISPATCH
5. **Expected:** Software controller UI opens on PC

### Test 2: Dispatch with Hardware Controller
1. Start system: `python combine_ctc_wayside_test.py`
2. In CTC → Manual tab
3. Select "Hardware (Raspberry Pi)" in Controller Type dropdown
4. Fill in train details and click DISPATCH
5. **Expected:** Popup with Raspberry Pi instructions appears

### Test 3: Mixed Controllers
1. Dispatch Train 1 with "Software (PC)"
2. Dispatch Train 2 with "Hardware (Raspberry Pi)"
3. Dispatch Train 3 with "Software (PC)"
4. **Expected:** Mixed controller types work correctly

---

## Benefits

### For Testing
- ✅ Deploy all trains as software controllers on one PC
- ✅ No need for Raspberry Pi during development
- ✅ Easy to test multi-train scenarios

### For Production
- ✅ Choose which trains use physical hardware
- ✅ Mix software and hardware as needed
- ✅ Flexibility for different deployment scenarios

### For Development
- ✅ Test hardware integration without changing code
- ✅ Quick switch between controller types
- ✅ Better control over system configuration

---

## Troubleshooting

### Issue: Dropdown not appearing
**Check:** Make sure you're on the "Manual" tab in the CTC UI

### Issue: Hardware controller doesn't connect
**Check:** 
1. Did you run the command on the Raspberry Pi?
2. Is the server IP address correct?
3. Is port 5000 accessible from the Raspberry Pi?

### Issue: Software controller doesn't appear
**Check:** Console for error messages about TrainManager initialization

---

## Future Enhancements

Possible future improvements:
- Save default controller type preference
- Auto-detect available Raspberry Pis and assign automatically
- Show status of which Raspberry Pis are connected
- Add "Local Hardware" option for testing GPIO on PC

---

## Git Commit

```
Commit: a449d77
Branch: phase3
Message: Add manual controller type selection to CTC UI
```

---

**Status:** ✅ **COMPLETE** - CTC now has manual controller type selection!

You can now choose Software or Hardware controllers for each train dispatch! 🎉


