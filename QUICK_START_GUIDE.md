# Quick Start Guide - Phase 3 System

## Running the System

### Step 1: Start the System
```bash
# From project root
cd C:\Users\julen\Documents\ECE1140\Group4-ECE1140
python combine_ctc_wayside_test.py
```

**What Opens:**
- ✅ CTC UI (Centralized Traffic Control)
- ✅ Wayside Controller UI (Track Controller)

---

## Dispatching Trains

### Step 2: Go to CTC Manual Tab

Click the **"Manual"** button in the CTC UI

### Step 3: Fill in Train Details

The Manual tab now looks like this:

```
╔═══════════════════════════════════════════════════════════════╗
║                     MANUAL DISPATCH                           ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Select a Train to Dispatch     Select a Line                ║
║  ┌─────────────────┐            ┌──────────┐                 ║
║  │ Train 1       ▼ │            │ Green  ▼ │                 ║
║  └─────────────────┘            └──────────┘                 ║
║                                                               ║
║  Select a Destination Station   Enter Arrival Time           ║
║  ┌─────────────────┐            ┌──────────┐                 ║
║  │ Mt. Lebanon   ▼ │            │ 17:30    │                 ║
║  └─────────────────┘            └──────────┘                 ║
║                                                               ║
║  Controller Type:                                            ║
║  ┌──────────────────────────────────────┐                    ║
║  │ Software (PC)                      ▼ │  ← Choose Here!    ║
║  └──────────────────────────────────────┘                    ║
║                                                               ║
║                    ┌──────────────┐                          ║
║                    │   DISPATCH   │                          ║
║                    └──────────────┘                          ║
╚═══════════════════════════════════════════════════════════════╝
```

### Step 4: Choose Controller Type

**Click the "Controller Type" dropdown:**

```
┌──────────────────────────────────────┐
│ Software (PC)                        │  ← Default (runs on your PC)
│ Hardware (Raspberry Pi)              │  ← Physical buttons on Raspberry Pi
└──────────────────────────────────────┘
```

### Step 5: Click DISPATCH

---

## Controller Type Options

### Option 1: Software (PC) ✅ Recommended for Testing

**What Happens:**
1. Train Model UI opens on your PC
2. Train Controller UI opens on your PC (virtual buttons)
3. Both UIs appear immediately - ready to use!

**Use When:**
- Testing the system
- Running multiple trains on one PC
- No Raspberry Pi available
- Developing/debugging

**Example:**
```
Train 1: Software (PC)
Train 2: Software (PC)
Train 3: Software (PC)
```
All 3 trains run on your PC!

---

### Option 2: Hardware (Raspberry Pi) ✅ For Production

**What Happens:**
1. Train Model UI opens on your PC
2. **Popup appears** with Raspberry Pi setup instructions
3. You run a command on Raspberry Pi to start the hardware controller

**Popup Message:**
```
╔══════════════════════════════════════════════════╗
║ Train 1 - Remote Hardware Setup                 ║
╠══════════════════════════════════════════════════╣
║ Train 1 Model created on this server!           ║
║                                                  ║
║ Hardware Controller must run on Raspberry Pi.   ║
║                                                  ║
║ ══════════════════════════════════════════       ║
║ On Raspberry Pi, run:                            ║
║                                                  ║
║ cd train_controller/ui                           ║
║ python train_controller_hw_ui.py \               ║
║   --train-id 1 \                                 ║
║   --server http://192.168.1.100:5000             ║
║ ══════════════════════════════════════════       ║
╚══════════════════════════════════════════════════╝
```

**Use When:**
- Production deployment
- Testing with physical hardware
- Distributed system (PC + Raspberry Pis)
- Demonstrating the system

---

## Complete Examples

### Example 1: Testing Mode (All Software)
```
1. Start system: python combine_ctc_wayside_test.py
2. CTC → Manual tab
3. Dispatch Train 1:
   - Train: "Train 1"
   - Line: "Green"
   - Destination: "Mt. Lebanon"
   - Arrival Time: "17:30"
   - Controller Type: "Software (PC)" ✓
   - Click DISPATCH
4. Dispatch Train 2:
   - Train: "Train 2"
   - Controller Type: "Software (PC)" ✓
   - Click DISPATCH
```

**Result:** Both trains run on your PC with virtual controllers!

---

### Example 2: Production Mode (Hardware Controllers)
```
1. Start system: python combine_ctc_wayside_test.py
2. CTC → Manual tab
3. Dispatch Train 1:
   - Controller Type: "Hardware (Raspberry Pi)" ✓
   - Click DISPATCH
   - Copy command from popup
4. On Raspberry Pi #1:
   - Paste and run the command
5. Dispatch Train 2:
   - Controller Type: "Hardware (Raspberry Pi)" ✓
   - Click DISPATCH
6. On Raspberry Pi #2:
   - Run command for Train 2
```

**Result:** Both trains have physical hardware controllers on Raspberry Pis!

---

### Example 3: Mixed Mode
```
Train 1: "Hardware (Raspberry Pi)" - Physical controller on Raspberry Pi
Train 2: "Software (PC)" - Virtual controller on PC
Train 3: "Software (PC)" - Virtual controller on PC
Train 4: "Hardware (Raspberry Pi)" - Physical controller on another Raspberry Pi
```

**Use Case:** 
- Main line uses hardware controllers (realistic)
- Test trains use software controllers (convenient)

---

## Troubleshooting

### Issue: Dropdown is empty or not showing
**Fix:** Make sure you're using the latest code:
```bash
git pull origin phase3
python combine_ctc_wayside_test.py
```

### Issue: Hardware controller doesn't connect
**Check:**
1. Did you copy the EXACT command from the popup?
2. Is the server IP correct?
3. Is the Raspberry Pi on the same network?
4. Is port 5000 accessible? (Check firewall)

### Issue: Can't select controller type
**Check:** 
- Make sure dropdown shows both options
- Default should be "Software (PC)"
- Click dropdown to change

---

## Tips

### For Development/Testing:
- ✅ Use **"Software (PC)"** for all trains
- ✅ Test on one computer
- ✅ No Raspberry Pi needed

### For Demos/Production:
- ✅ Use **"Hardware (Raspberry Pi)"** for realistic operation
- ✅ Mix software and hardware as needed
- ✅ Follow popup instructions for each hardware controller

### For Flexibility:
- ✅ You can change your mind - just select different option for each train
- ✅ No need to restart system to switch controller types
- ✅ Each train can have a different controller type

---

## What's Different from Before?

### Before (Automatic):
- ❌ First train was always Hardware
- ❌ All other trains were always Software
- ❌ No user choice

### After (Manual Selection):
- ✅ **You choose** for each train
- ✅ Can have all software, all hardware, or mixed
- ✅ Dropdown makes it clear and easy

---

## System Status

**Phase 3: COMPLETE** ✅

**Features:**
- ✅ REST API integration (all 4 components)
- ✅ Graceful fallback to file I/O
- ✅ Manual controller type selection
- ✅ 6 critical bugs fixed
- ✅ Comprehensive documentation
- ✅ Ready for testing and deployment

**Next:** Test with Raspberry Pi! 🚀

---

## Quick Reference Commands

### Start System
```bash
python combine_ctc_wayside_test.py
```

### Start Server (Optional - for REST API mode)
```bash
cd train_controller/api
python train_api_server.py
```

### On Raspberry Pi (when Hardware selected)
```bash
# Use exact command from popup!
cd ~/Group4-ECE1140/train_controller/ui
python train_controller_hw_ui.py --train-id <X> --server http://<PC-IP>:5000
```

---

**That's it! You're ready to dispatch trains with full control!** 🚂✨


