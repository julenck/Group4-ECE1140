# Hardware Wayside Controller - Raspberry Pi Setup Guide

## 🎯 Overview

This guide helps you run the **Hardware Wayside Controller** on a Raspberry Pi in **server mode**, connecting to the REST API server running on your PC.

---

## 📋 Prerequisites

### On Your PC:
- REST API server running (`train_controller/api/train_api_server.py`)
- PC and Raspberry Pi on the same network
- Know your PC's IP address (e.g., `10.5.127.125`)

### On Raspberry Pi:
- Python 3.7+
- Tkinter installed (`sudo apt install python3-tk`)
- Project code synced to Pi (via git or scp)

---

## 🚀 Quick Start

### Step 1: Start REST API Server on PC

```bash
# On your PC - Terminal 1
cd C:\Users\julen\Documents\ECE1140\Group4-ECE1140
cd train_controller\api
python train_api_server.py
```

**Wait for:**
```
* Running on http://0.0.0.0:5000
```

### Step 2: Find Your PC's IP Address

**On Windows PC:**
```bash
ipconfig
```

Look for `IPv4 Address` under your active network adapter (e.g., `10.5.127.125`)

### Step 3: Set Server URL on Raspberry Pi

```bash
# On Raspberry Pi
export SERVER_URL=http://10.5.127.125:5000  # Replace with your PC's IP
```

### Step 4: Run Hardware Wayside on Raspberry Pi

**Option A: Use the test script (recommended)**
```bash
cd ~/projects/Group4-ECE1140
python test_hw_wayside_rpi.py
```

**Option B: Use the integrated launcher**
```bash
cd ~/projects/Group4-ECE1140
python combine_ctc_wayside_test.py
```

**Option C: Manual Python command**
```bash
cd ~/projects/Group4-ECE1140
python -c "
from track_controller.hw_wayside.hw_wayside_controller import HW_Wayside_Controller
from track_controller.hw_wayside.hw_wayside_controller_ui import HW_Wayside_Controller_UI
import tkinter as tk
import os

server_url = os.environ.get('SERVER_URL', 'http://10.5.127.125:5000')
controller = HW_Wayside_Controller('B', list(range(70, 144)), server_url=server_url)
root = tk.Tk()
ui = HW_Wayside_Controller_UI(root, controller, 'HW Wayside B [SERVER MODE]')
ui.pack(fill=tk.BOTH, expand=True)
root.mainloop()
"
```

---

## ✅ Expected Output

### On Raspberry Pi Terminal:
```
✅ Successfully imported hardware wayside components
🌐 Server URL: http://10.5.127.125:5000
🚂 Creating Hardware Wayside Controller B (blocks 70-143)...
[Wayside B] Using REST API: http://10.5.127.125:5000
✅ Controller created successfully
🖥️  Creating UI...
✅ UI created successfully
🚀 Starting UI mainloop...
```

### On PC Server Terminal:
```
[Server] GET /api/wayside/B/ctc_commands - 200 OK
[Server] GET /api/wayside/B/train_speeds - 200 OK
[Server] POST /api/wayside/B/train_commands - 200 OK
```

---

## 🐛 Troubleshooting

### Error: `ModuleNotFoundError: No module named 'hw_vital_check'`

**Solution:** Make sure you're running from the project root:
```bash
cd ~/projects/Group4-ECE1140
# NOT: cd track_controller/hw_wayside
```

### Error: `Connection refused` or `Timeout`

**Possible causes:**
1. **Server not running on PC** - Start `train_api_server.py` first
2. **Wrong IP address** - Double-check PC's IP with `ipconfig`
3. **Firewall blocking** - Allow Python through Windows Firewall
4. **Different networks** - PC and Pi must be on same network

**Test connection:**
```bash
# On Raspberry Pi
curl http://10.5.127.125:5000/api/health
```

Expected response:
```json
{"status": "healthy", "message": "Train API Server is running"}
```

### Error: `No display named :0`

**Solution:** If running over SSH without X11 forwarding:
```bash
# On Raspberry Pi
export DISPLAY=:0  # Use the local display
# OR
ssh -X pi@raspberrypi  # Enable X11 forwarding when connecting
```

### Warning: `Failed to initialize API client`

**Solution:** API client will fall back to file I/O. Check:
1. Server URL is correct
2. Server is reachable
3. Network is stable

---

## 🔧 Advanced Configuration

### Custom Server URL

```bash
# Use a different server URL
export SERVER_URL=http://192.168.1.100:5000
python test_hw_wayside_rpi.py
```

### Custom Timeout

Edit `test_hw_wayside_rpi.py`:
```python
controller = HW_Wayside_Controller(
    wayside_id="B",
    block_ids=blocks_70_143,
    server_url=server_url,
    timeout=10.0  # Increase timeout for slow networks
)
```

### Different Wayside Configuration

**For Wayside A (blocks 0-73, 144-150):**
```python
blocks = list(range(0, 74)) + list(range(144, 151))
controller = HW_Wayside_Controller('A', blocks, server_url=server_url)
```

---

## 📝 File I/O Fallback

If the server is unreachable, the hardware wayside will automatically fall back to file-based I/O:

```
[Wayside B] API load_inputs_ctc failed: Connection refused, falling back to file I/O
[Wayside B] Using file-based I/O for this cycle
```

This ensures the system continues working even if network connectivity is lost.

---

## 🧪 Testing the Integration

### Test 1: Verify Server Connection
```bash
# On Raspberry Pi
python -c "
from track_controller.api.wayside_api_client import WaysideAPIClient
api = WaysideAPIClient(wayside_id='B', server_url='http://10.5.127.125:5000', timeout=5.0)
print('✅ Server is reachable!')
"
```

### Test 2: Dispatch a Train from CTC

1. Start server on PC
2. Start `combine_ctc_wayside_test.py` on PC (launches CTC)
3. Start hardware wayside on Raspberry Pi
4. Dispatch a train from CTC UI
5. Observe train commands flowing from CTC → Server → Raspberry Pi Wayside

---

## 📚 Related Documentation

- `RASPBERRY_PI_SETUP.md` - General Raspberry Pi setup for train controller
- `PHASE_3_TESTING_GUIDE.md` - Comprehensive testing procedures
- `combine_ctc_wayside_test.py` - Integrated system launcher

---

## ✅ System Architecture

```
┌─────────────────────┐
│    PC (Windows)     │
│                     │
│  ┌───────────────┐  │
│  │ CTC UI        │  │
│  └───────┬───────┘  │
│          │          │
│  ┌───────▼───────┐  │
│  │ REST API      │  │◄─────┐
│  │ Server        │  │      │
│  │ :5000         │  │      │
│  └───────────────┘  │      │
│                     │      │
│  ┌───────────────┐  │      │
│  │ SW Wayside A  │  │      │ Network
│  │ (Blocks 0-73) │  │      │ (WiFi/Ethernet)
│  └───────────────┘  │      │
└─────────────────────┘      │
                             │
┌─────────────────────┐      │
│ Raspberry Pi        │      │
│                     │      │
│  ┌───────────────┐  │      │
│  │ HW Wayside B  │──┼──────┘
│  │ (Blocks 70-143│  │
│  │ [SERVER MODE])│  │
│  └───────────────┘  │
└─────────────────────┘
```

---

**Status:** ✅ **Ready for Testing!**

Run `test_hw_wayside_rpi.py` on your Raspberry Pi to get started.

