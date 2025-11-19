# Quick Start Guide - Hardware Train Controller

## 🚀 Quick Start (3 Steps)

### Step 1: Start Server (on PC)
```bash
cd train_controller
python start_server.py
```
**Note the IP address** shown (e.g., `192.168.1.100`)

### Step 2: Start Test UI (on PC)
```bash
cd "Train Model"
python train_model_test_ui.py --train-id 1 --server http://192.168.1.100:5000
```
**Replace IP with your server's IP**

### Step 3: Start Hardware Controller (on Raspberry Pi)
```bash
cd train_controller/ui
python train_controller_hw_ui.py --train-id 1 --server http://192.168.1.100:5000
```
**Use same IP as Step 2**

---

## 🔍 Quick Test

1. In Test UI, change "Commanded Speed" to **50**
2. Click "Step Simulation"
3. Hardware Controller should show **50** within 1 second

---

## 🐛 Quick Debug

### If Hardware Controller shows "Connection timeout":
```bash
# Test from Raspberry Pi:
curl http://192.168.1.100:5000/api/health
```

If this fails:
- Check server is running
- Check firewall (allow port 5000)
- Verify IP address

### If Test UI changes don't reach Hardware Controller:

**Check you started Test UI with --server flag!**

Without `--server`: Only writes locally ❌
With `--server`: Sends to server ✅

### Run diagnostic:
```bash
python diagnostic_tool.py http://192.168.1.100:5000 1
```

---

## 📝 Command Summary

| Component | Command |
|-----------|---------|
| Server | `python train_controller/start_server.py` |
| Test UI | `python train_model_test_ui.py --train-id 1 --server http://IP:5000` |
| HW Controller | `python train_controller_hw_ui.py --train-id 1 --server http://IP:5000` |
| Diagnostic | `python diagnostic_tool.py http://IP:5000 1` |

---

## ✅ What to Look For

### Server Terminal:
```
[Server] Train data sync thread started (500ms interval)
[Server] Train 1 state updated: ['commanded_speed', ...]
```

### Test UI Terminal:
```
(No errors is good!)
```

### Hardware Controller Terminal:
```
[Hardware Controller] State fetched from server
[Hardware Controller] Commanded speed: 50.0
```

---

## 🔥 Troubleshooting One-Liners

**Server not reachable:**
```bash
ping 192.168.1.100  # From Pi
```

**Check train state:**
```bash
curl http://192.168.1.100:5000/api/train/1/state
```

**Watch state file:**
```bash
watch -n 1 cat train_controller/data/train_states.json
```

**Allow firewall (Windows PC):**
```bash
netsh advfirewall firewall add rule name="Flask5000" dir=in action=allow protocol=TCP localport=5000
```

---

## 📚 Full Documentation

See `HARDWARE_CONTROLLER_TEST_GUIDE.md` for detailed troubleshooting.
