# Raspberry Pi Hardware Controller Setup Guide

## Overview
This guide shows you how to run the system with the Train Model on your laptop (server) and the Hardware Controller on your Raspberry Pi (client).

## Architecture

```
┌─────────────────────────────────────┐
│      YOUR LAPTOP (Server)           │
│                                     │
│  • CTC UI                           │
│  • Wayside Controllers              │
│  • Train Model UI(s)                │
│  • REST API Server (port 5000)     │
│                                     │
│  IP: 10.4.0.227 (example)          │
└─────────────────────────────────────┘
              │
              │ Network (WiFi/Ethernet)
              │ REST API Communication
              │
┌─────────────────────────────────────┐
│   RASPBERRY PI (Client)             │
│                                     │
│  • Hardware Controller UI           │
│  • GPIO buttons/LEDs                │
│  • I2C devices (LCD, ADC, etc.)     │
│                                     │
└─────────────────────────────────────┘
```

---

## Part 1: Setup on Your Laptop (Server)

### Step 1: Get Your Laptop's IP Address

**Windows (PowerShell):**
```powershell
ipconfig
```
Look for "IPv4 Address" under your active network adapter (WiFi or Ethernet).

Example output:
```
Wireless LAN adapter Wi-Fi:
   IPv4 Address. . . . . . . . . . . : 10.4.0.227
```

**Your laptop IP:** `10.4.0.227` (write this down!)

### Step 2: Start the REST API Server

The REST API server needs to be running for the Raspberry Pi to communicate with the Train Model.

**Open a NEW terminal/PowerShell window and run:**

```bash
cd C:\Projects\Group4-ECE1140\train_controller
python start_server.py
```

You should see:
```
================================================================================
  TRAIN SYSTEM REST API SERVER
================================================================================

✓ Server starting on 0.0.0.0:5000
✓ Local IP address: 10.4.0.227

📡 Raspberry Pis should connect to: http://10.4.0.227:5000

📋 Available Endpoints:
   http://10.4.0.227:5000/api/health
   http://10.4.0.227:5000/api/trains
   http://10.4.0.227:5000/api/train/<id>/state

🔧 To stop the server, press Ctrl+C
================================================================================
```

**Important:** Keep this terminal window open - the server must stay running!

### Step 3: Dispatch First Train from CTC

1. Open CTC UI (should already be open from `combine_ctc_wayside_test.py`)
2. Go to **Manual** tab
3. Fill in train details:
   - Train: Train 1
   - Line: Green
   - Destination: (pick a station)
   - Arrival Time: (pick a time)
4. Click **"Dispatch"**

You should see:
```
[CTC Dispatch] Dispatching FIRST train with Hardware Controller (REMOTE - Raspberry Pi)
[TrainManager] Using HARDWARE controller for train 1 (REMOTE - Raspberry Pi)
[TrainManager] Train 1 controller is REMOTE (Raspberry Pi)
[TrainManager] Start hardware UI on Raspberry Pi with:
  python train_controller_hw_ui.py --train-id 1 --server http://<server-ip>:5000
Train 1 UIs created (Model: Yes, Controller: Remote)
```

✅ **Train Model UI opens on your laptop**
❌ **No Controller UI on laptop** (it will run on Raspberry Pi)

---

## Part 2: Setup on Raspberry Pi (Client)

### Step 1: Ensure Network Connection

Make sure your Raspberry Pi is on the **same network** as your laptop.

**Test connectivity from Raspberry Pi:**
```bash
ping 10.4.0.227
```
(Replace with your laptop's IP)

You should see responses. Press `Ctrl+C` to stop.

### Step 2: Copy Project to Raspberry Pi

If you haven't already, copy the train controller code to your Raspberry Pi:

```bash
# On Raspberry Pi
cd ~
git clone <your-repo-url>
cd Group4-ECE1140
```

Or use `scp` to copy from your laptop:
```bash
# On your laptop
scp -r C:\Projects\Group4-ECE1140\train_controller pi@<raspberry-pi-ip>:~/
```

### Step 3: Install Dependencies on Raspberry Pi

```bash
# On Raspberry Pi
cd ~/Group4-ECE1140/train_controller

# Install Python packages
pip3 install gpiozero smbus2 requests

# If you have I2C devices, enable I2C:
sudo raspi-config
# Navigate to: Interface Options -> I2C -> Enable
```

### Step 4: Run Hardware Controller on Raspberry Pi

Using the command from Step 3 of laptop setup, run on Raspberry Pi:

```bash
cd ~/Group4-ECE1140/train_controller/ui
python3 train_controller_hw_ui.py --train-id 1 --server http://10.4.0.227:5000
```

**Replace `10.4.0.227` with YOUR laptop's IP address!**

### Step 5: Verify Connection

You should see the Hardware Controller UI window open on the Raspberry Pi display showing:

```
================================================================
  HARDWARE TRAIN CONTROLLER UI
================================================================
  Train ID: 1
  Mode: REMOTE (Raspberry Pi)
  Server: http://10.4.0.227:5000
  Timeout: 5.0s
================================================================

[HW UI] Using REMOTE API: http://10.4.0.227:5000 (timeout: 5.0s)
```

The UI should start updating with train data from the server!

---

## Part 3: Normal Operation Workflow

### For Each Session:

**On Your Laptop:**
1. **Terminal 1:** Start REST API Server
   ```bash
   cd C:\Projects\Group4-ECE1140\train_controller
   python start_server.py
   ```
   ⚠️ **Keep this terminal open!** Note your IP address from the output.

2. **Terminal 2:** Start the train system
   ```bash
   cd C:\Projects\Group4-ECE1140
   python combine_ctc_wayside_test.py
   ```

3. Dispatch trains from CTC as normal

**On Raspberry Pi (only for first train):**
1. Wait for first train dispatch confirmation on laptop
2. Run: `python3 train_controller_hw_ui.py --train-id 1 --server http://<laptop-ip>:5000`
3. The hardware UI will connect and control Train 1

**For trains 2, 3, 4...:**
- They automatically use software controllers on your laptop
- No Raspberry Pi setup needed!

---

## Troubleshooting

### Issue: "Connection refused" or "Cannot connect to server"

**Check:**
1. Server is running on laptop (check terminal for "Running on...")
2. Firewall allows port 5000 (Windows Firewall may block it)
3. Both devices on same network
4. IP address is correct

**Fix firewall (Windows):**
```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "Train Controller API" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

### Issue: "Module not found" errors on Raspberry Pi

**Install missing packages:**
```bash
pip3 install gpiozero smbus2 requests tkinter
```

### Issue: Hardware UI opens but shows all zeros

**Possible causes:**
1. API server not responding (check laptop terminal)
2. Network latency (increase timeout):
   ```bash
   python3 train_controller_hw_ui.py --train-id 1 --server http://10.4.0.227:5000 --timeout 10.0
   ```
3. Train not dispatched yet from CTC

### Issue: GPIO/I2C warnings

If you see warnings like:
```
GPIO pin X not available
I2C device not found at address 0x27
```

This is **NORMAL** if you don't have actual hardware connected. The UI will still work for testing, just without physical buttons/displays.

---

## Testing Without Hardware

To test the hardware UI on Raspberry Pi without actual GPIO/I2C devices:

1. The UI will display warnings but continue running
2. All controls will be visible in the UI window
3. You can still control the train using the UI buttons
4. Physical hardware is optional for software testing

---

## Advanced: Running Multiple Trains

**First Train (Hardware - Raspberry Pi):**
```bash
# On Raspberry Pi
python3 train_controller_hw_ui.py --train-id 1 --server http://10.4.0.227:5000
```

**Second Train (Software - Laptop):**
- Automatically opens on laptop when dispatched from CTC
- No additional setup needed!

**Third Train (Software - Laptop):**
- Automatically opens on laptop when dispatched from CTC
- No additional setup needed!

And so on...

---

## Quick Reference Commands

### On Laptop (Server):
```bash
# Terminal 1: Start REST API Server (MUST RUN FIRST)
cd C:\Projects\Group4-ECE1140\train_controller
python start_server.py

# Terminal 2: Start CTC/Wayside/Train System
cd C:\Projects\Group4-ECE1140
python combine_ctc_wayside_test.py

# Check your IP address
ipconfig
```

### On Raspberry Pi (Client):
```bash
# Test connectivity
ping <laptop-ip>

# Run hardware controller for Train 1
cd ~/Group4-ECE1140/train_controller/ui
python3 train_controller_hw_ui.py --train-id 1 --server http://<laptop-ip>:5000

# Check if I2C devices detected
i2cdetect -y 1
```

---

## Network Configuration Tips

### Same WiFi Network
- Connect both laptop and Raspberry Pi to same WiFi
- Most reliable for testing

### Ethernet Connection
- Connect Raspberry Pi to laptop via Ethernet cable
- May need to enable Internet Connection Sharing on laptop
- Configure static IPs for stability

### Hotspot Mode
- Create WiFi hotspot on laptop
- Connect Raspberry Pi to laptop's hotspot
- Check laptop's hotspot IP (usually `192.168.137.1`)

---

## Summary

✅ **Laptop runs**: CTC, Wayside, Train Models, API Server
✅ **Raspberry Pi runs**: Hardware Controller for Train 1
✅ **Network**: Both on same network, communicate via REST API
✅ **Port**: 5000 (make sure it's not blocked)
✅ **Command**: `python3 train_controller_hw_ui.py --train-id 1 --server http://<laptop-ip>:5000`

That's it! The hardware controller will communicate with the Train Model over the network. 🚂

