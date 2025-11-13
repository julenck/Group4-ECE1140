# Quick Reference Card - Train System Network Setup

## Installation

### Server (Main Computer)
```bash
pip install flask flask-cors
```

### Raspberry Pi
```bash
pip install requests gpiozero smbus2
```

---

## Startup Commands

### Server Machine
```bash
# Terminal 1: Start API Server
cd train_controller
python start_server.py

# Terminal 2: Start Train Manager
python train_manager.py
```

### Raspberry Pi (Hardware Train Controller)
```bash
cd train_controller/ui
python train_controller_hw_ui.py --train-id 1 --server http://<SERVER_IP>:5000
```

---

## Train Manager UI Options

### Controller Types:
1. **💻 Software (UI Only)**
   - Runs on server
   - No GPIO required
   - Good for testing

2. **🔧 Hardware (Local - this machine)**
   - Runs on server
   - Requires GPIO on server
   - For local testing

3. **📡 Hardware (Remote - Raspberry Pi)** ⭐ **USE THIS**
   - Controller on Raspberry Pi
   - Model on server
   - Standard deployment

---

## Testing

```bash
# Test server connection
python test_api_connection.py http://<SERVER_IP>:5000

# Test server health from Raspberry Pi
curl http://<SERVER_IP>:5000/api/health
```

---

## File Locations

```
train_controller/
├── start_server.py           # Run this to start API server
├── train_manager.py          # Run this to manage trains
├── test_api_connection.py    # Run this to test connection
├── api/
│   ├── train_api_server.py   # REST API server (auto-loaded)
│   ├── train_controller_api.py         # Local API (server)
│   └── train_controller_api_client.py  # Client API (Raspberry Pi)
└── ui/
    └── train_controller_hw_ui.py  # Hardware UI (supports remote)
```

---

## Common Issues

### Can't connect from Raspberry Pi
```bash
# On server: Open firewall
# Windows: Add inbound rule for port 5000
# Linux: sudo ufw allow 5000

# Find server IP
ipconfig          # Windows
ifconfig          # Linux/Mac
```

### Server already running on port 5000
```bash
# Use different port
python start_server.py --port 5001

# Update Raspberry Pi command
python train_controller_hw_ui.py --train-id 1 --server http://<IP>:5001
```

---

## API Endpoints Reference

```
GET  /api/health              Server status
GET  /api/trains              All trains
GET  /api/train/<id>/state    Get train state
POST /api/train/<id>/state    Update train state
POST /api/train/<id>/reset    Reset train
DELETE /api/train/<id>        Delete train
```

---

## Example Workflow

**1. On Server:**
```bash
python start_server.py
# Note the IP address (e.g., 192.168.1.100)
```

**2. On Server (new terminal):**
```bash
python train_manager.py
# Select "📡 Hardware (Remote - Raspberry Pi)"
# Click "Add New Train"
# Copy the command from popup
```

**3. On Raspberry Pi:**
```bash
python train_controller_hw_ui.py --train-id 1 --server http://192.168.1.100:5000
# Hardware UI connects!
# GPIO buttons now control the train
```

---

## Default Values

- **Server Port:** 5000
- **Server Host:** 0.0.0.0 (all interfaces)
- **Train ID:** 1 (default for hardware UI)
- **API Timeout:** 1 second
- **Update Interval:** 500ms

---

## Status Indicators

In Train Manager UI:
- `[SW]` - Software controller
- `[HW-Local]` - Hardware controller on server
- `[HW-Remote]` - Hardware controller on Raspberry Pi
- `✓ UIs` - All UIs created
- `⚠️ Start on RPi` - Need to start on Raspberry Pi

---

## Network Requirements

- Same local network (LAN)
- Port 5000 accessible
- Raspberry Pi can reach server IP
- No internet connection required

---

## Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" | Start API server first |
| "Train not found" | Add train in Train Manager |
| GPIO errors | Run with `sudo` on Raspberry Pi |
| Port already in use | Use `--port 5001` |
| Wrong IP | Check with `ipconfig`/`ifconfig` |

---

For detailed help, see: **NETWORK_SETUP.md**
