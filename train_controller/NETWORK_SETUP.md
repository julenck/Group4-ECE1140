# Train System Network Setup Guide

This guide explains how to set up the train system with a central server and Raspberry Pi clients. 

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│          Server Machine (Main Computer)         │
│  ┌──────────────────────────────────────────┐   │
│  │   REST API Server (Port 5000)            │   │
│  │   - Manages train_states.json            │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │   Train Manager UI                       │   │
│  │   - Add/Remove trains                    │   │
│  │   - Select controller type               │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │   Train Model Instances                  │   │
│  │   - Physics simulation for each train    │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
         ↑                    ↑
         │ HTTP REST API      │ HTTP REST API
         │                    │
┌────────┴────────┐   ┌──────┴──────────┐
│  Raspberry Pi 1 │   │  Raspberry Pi 2 │
│  ┌───────────┐  │   │  ┌───────────┐  │
│  │ HW Train  │  │   │  │ Track     │  │
│  │Controller │  │   │  │Controller │  │
│  │    UI     │  │   │  │    HW     │  │
│  └───────────┘  │   │  └───────────┘  │
│  - GPIO buttons │   │  - Track HW    │
│  - LEDs/ADC/LCD │   │  - Switches    │
└─────────────────┘   └─────────────────┘
```

---

## Prerequisites

### Server Machine (Main Computer)
```bash
pip install flask flask-cors
```

### Raspberry Pi
```bash
pip install requests gpiozero smbus2
```

---

## Step-by-Step Setup

### 1. Start the REST API Server (on Main Computer)

```bash
cd train_controller
python start_server.py
```

The server will display:
```
═════════════════════════════════════════
  TRAIN SYSTEM REST API SERVER
═════════════════════════════════════════

✓ Server starting on 0.0.0.0:5000
✓ Local IP address: 192.168.1.100

📡 Raspberry Pis should connect to: http://192.168.1.100:5000
```

**Note the IP address** - you'll need it for the Raspberry Pi!

### 2. Start the Train Manager (on Main Computer)

In a new terminal:
```bash
cd train_controller
python train_manager.py
```

### 3. Add a Train with Remote Hardware Controller

In the Train Manager UI:
1. Select **"📡 Hardware (Remote - Raspberry Pi)"**
2. Click **"➕ Add New Train"**
3. A popup will appear with instructions for the Raspberry Pi
4. The Train Model UI will open on the server
5. Note the train ID (e.g., Train 1)

### 4. Start Hardware Controller on Raspberry Pi

On the Raspberry Pi, run:
```bash
cd train_controller/ui
python train_controller_hw_ui.py --train-id 1 --server http://192.168.1.100:5000
```

Replace `192.168.1.100` with your server's IP address.
Replace `1` with the train ID from step 3.

The Raspberry Pi will display:
```
═════════════════════════════════════════
  HARDWARE TRAIN CONTROLLER UI
═════════════════════════════════════════
  Train ID: 1
  Mode: REMOTE (Raspberry Pi)
  Server: http://192.168.1.100:5000
═════════════════════════════════════════

[API Client] ✓ Connected to server: http://192.168.1.100:5000
[API Client] ✓ Managing Train 1
```

---

## Controller Type Options

### 💻 Software (UI Only)
- Controller runs on the server
- Uses local file-based API
- No GPIO hardware required
- Good for testing

### 🔧 Hardware (Local - this machine)
- Controller runs on the server
- Requires GPIO hardware on the server
- Uses local file-based API
- For testing with GPIO on server

### 📡 Hardware (Remote - Raspberry Pi)
- Controller runs on Raspberry Pi
- Train Model runs on server
- Uses REST API over network
- **This is the standard deployment mode**

---

## Network Configuration

### Finding Your Server IP

On Windows:
```powershell
ipconfig
```
Look for "IPv4 Address" under your network adapter.

On Linux/Mac:
```bash
ifconfig
# or
ip addr show
```

### Testing Connection

From Raspberry Pi, test the connection:
```bash
curl http://192.168.1.100:5000/api/health
```

Should return:
```json
{
  "status": "ok",
  "message": "Train API Server running",
  "timestamp": "2025-11-11T..."
}
```

---

## Troubleshooting

### Raspberry Pi Can't Connect to Server

1. **Check firewall**: Ensure port 5000 is open on the server
   - Windows: Add inbound rule for port 5000
   - Linux: `sudo ufw allow 5000`

2. **Check IP address**: Ensure you're using the correct server IP

3. **Ping test**: From Raspberry Pi:
   ```bash
   ping 192.168.1.100
   ```

4. **Check server is running**: On server, verify API server is running

### JSON File Conflicts

If multiple machines write to train_states.json:
- The REST API server handles all file writes with thread-safe locks
- Only the server should write to the file directly
- Raspberry Pis should only use the API client

### GPIO Errors on Raspberry Pi

If you see GPIO errors:
```bash
# Ensure gpiozero is installed
pip install gpiozero

# Check if running as root (may be needed for GPIO)
sudo python train_controller_hw_ui.py --train-id 1 --server http://...
```

---

## File Structure

```
train_controller/
├── api/
│   ├── train_controller_api.py          # Local file-based API (server only)
│   ├── train_controller_api_client.py   # REST API client (Raspberry Pi)
│   └── train_api_server.py              # REST API server
├── ui/
│   ├── train_controller_hw_ui.py        # Hardware UI (supports local & remote)
│   └── train_controller_sw_ui.py        # Software UI
├── data/
│   └── train_states.json                # Centralized state file (server only)
├── train_manager.py                     # Multi-train manager
└── start_server.py                      # API server startup script
```

---

## Example: Complete Setup Workflow

### Server (192.168.1.100)
```bash
# Terminal 1: Start API Server
python train_controller/start_server.py

# Terminal 2: Start Train Manager
python train_controller/train_manager.py
```

In Train Manager UI:
- Select "📡 Hardware (Remote - Raspberry Pi)"
- Click "Add New Train"
- Train 1 Model UI appears
- Note: "Start on Raspberry Pi with train-id 1"

### Raspberry Pi 1 (Train Controller)
```bash
python train_controller_hw_ui.py --train-id 1 --server http://192.168.1.100:5000
```

Hardware UI connects and controls Train 1!

### Raspberry Pi 2 (Track Controller)
```bash
# Similar setup for track controller (when implemented)
python track_controller_hw_ui.py --server http://192.168.1.100:5000
```

---

## API Endpoints

The REST API server provides these endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Server health check |
| GET | `/api/trains` | Get all train states |
| GET | `/api/train/<id>/state` | Get specific train state |
| POST | `/api/train/<id>/state` | Update train state |
| POST | `/api/train/<id>/reset` | Reset train to defaults |
| DELETE | `/api/train/<id>` | Delete train |

---

## Security Notes

⚠️ **This system is designed for local network use only!**

- No authentication implemented
- Do not expose port 5000 to the internet
- Use only on trusted local networks
- For production, add API keys or OAuth

---

## Support

For issues or questions:
- Check server logs in the terminal
- Check Raspberry Pi logs
- Verify network connectivity
- Ensure all dependencies are installed
