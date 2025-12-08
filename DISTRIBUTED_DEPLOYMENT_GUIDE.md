# Distributed System Deployment Guide

## 🎯 **Overview**

This guide shows how to run the train control system in a **distributed architecture** across multiple devices:

- **PC (Windows):** CTC Dispatcher + Software Wayside 1
- **Raspberry Pi 1:** Hardware Wayside 2 (Blocks 70-143)
- **Raspberry Pi 2:** Hardware Train Controller(s)

---

## 🏗️ **System Architecture**

```
┌─────────────────────────────────────┐
│           PC (Windows)              │
│                                     │
│  ┌──────────────┐  ┌─────────────┐  │
│  │   CTC UI     │  │ SW Wayside  │  │
│  │ Dispatcher   │  │ Controller 1 │  │
│  │              │  │ Blocks 0-73  │  │
│  │              │  │ 144-150      │  │
│  └──────────────┘  └─────────────┘  │
│                                     │
│  ┌─────────────────────────────────┐ │
│  │    REST API Server :5000       │ │
│  └─────────────────────────────────┘ │
└───────────────────┬─────────────────┘
                    │ Network
                    │ (WiFi/Ethernet)
┌───────────────────┼─────────────────┐
│ Raspberry Pi 1    │ Raspberry Pi 2  │
│                   │                 │
│ ┌─────────────┐   │ ┌─────────────┐ │
│ │ HW Wayside │   │ │ HW Train    │ │
│ │ Controller │   │ │ Controller │ │
│ │ Blocks     │   │ │ Train 1     │ │
│ │ 70-143     │   │ │             │ │
│ └─────────────┘   │ └─────────────┘ │
└───────────────────┼─────────────────┘
```

---

## 🚀 **Deployment Steps**

### **Step 1: Start REST API Server on PC**

```bash
# On PC - Terminal 1
cd C:\Users\julen\Documents\ECE1140\Group4-ECE1140
cd train_controller\api
python train_api_server.py
```

**Expected:** `* Running on http://0.0.0.0:5000`

---

### **Step 2: Start CTC + SW Wayside 1 on PC**

```bash
# On PC - Terminal 2
cd C:\Users\julen\Documents\ECE1140\Group4-ECE1140
python combine_ctc_wayside_test.py
```

**Expected:**
- CTC Dispatcher UI opens
- SW Wayside Controller 1 UI opens (Blocks 0-73, 144-150)
- Status window shows: "Wayside Controller 2 [HW] (Blocks 70-143) - Run on Raspberry Pi"

---

### **Step 3: Start HW Wayside 2 on Raspberry Pi 1**

```bash
# On Raspberry Pi 1
cd ~/projects/Group4-ECE1140

# Set server URL (use YOUR PC's IP)
export SERVER_URL=http://10.5.127.125:5000

# Launch hardware wayside
python launch_hw_wayside_only.py
```

**Expected:**
```
🚂 Launching Hardware Wayside Controller B (Blocks 70-143)
🌐 Server URL: http://10.5.127.125:5000
✅ Hardware wayside components loaded
🏗️  Creating wayside controller...
✅ Controller created successfully
🖥️  Creating UI...
✅ UI created successfully
🚀 Starting Hardware Wayside Controller B...
```

---

### **Step 4: Start HW Train Controller on Raspberry Pi 2**

```bash
# On Raspberry Pi 2
cd ~/projects/Group4-ECE1140

# Set server URL (use YOUR PC's IP)
export SERVER_URL=http://10.5.127.125:5000

# Launch hardware train controller (already working)
python -m train_controller.ui.train_controller_hw_ui
```

---

## 📊 **Expected Server Logs (On PC)**

Once all components are running, you should see these API calls in the PC server terminal:

```
[Server] GET /api/health - 200 OK
[Server] POST /api/ctc/dispatch - 200 OK
[Server] GET /api/wayside/ctc_commands - 200 OK
[Server] GET /api/wayside/train_physics - 200 OK
[Server] POST /api/wayside/train_commands - 200 OK
[Server] GET /api/train/1/state - 200 OK
[Server] POST /api/train/1/state - 200 OK
```

---

## 🔧 **Troubleshooting**

### **Issue: Hardware Wayside Not Connecting**

**Check:**
1. **SERVER_URL is set:** `echo $SERVER_URL`
2. **PC IP is correct:** Test with `ping 10.5.127.125`
3. **Server is running:** Check PC terminal for `* Running on http://0.0.0.0:5000`

**Fix:**
```bash
# On Raspberry Pi
export SERVER_URL=http://YOUR_PC_IP:5000
python launch_hw_wayside_only.py
```

### **Issue: Train Not Handing Off**

**Check:**
1. **Train position:** Should move from blocks 0-73 → 74+
2. **Wayside 1 logs:** Should show "Train leaving section"
3. **Wayside 2 logs:** Should show "Picking up Train X (handoff detected)"

### **Issue: No Server Logs**

**Check:**
1. **All components are running**
2. **SERVER_URL is set on Pis**
3. **Network connectivity**

---

## 📁 **Files Used**

| Component | Device | Script |
|-----------|--------|--------|
| REST API Server | PC | `train_controller/api/train_api_server.py` |
| CTC + SW Wayside 1 | PC | `combine_ctc_wayside_test.py` |
| HW Wayside 2 | RPi 1 | `launch_hw_wayside_only.py` |
| HW Train Controller | RPi 2 | `train_controller/ui/train_controller_hw_ui.py` |

---

## 🎯 **Quick Start Commands**

### **PC:**
```bash
# Terminal 1: Server
cd train_controller\api
python train_api_server.py

# Terminal 2: CTC + SW Wayside
python combine_ctc_wayside_test.py
```

### **Raspberry Pi 1 (Wayside):**
```bash
export SERVER_URL=http://YOUR_PC_IP:5000
python launch_hw_wayside_only.py
```

### **Raspberry Pi 2 (Train Controller):**
```bash
export SERVER_URL=http://YOUR_PC_IP:5000
python -m train_controller.ui.train_controller_hw_ui
```

---

## ✅ **System Ready**

Your distributed train control system is now ready for testing! Each component communicates via the REST API server running on your PC.

**Next:** Dispatch a train from CTC and watch it hand off from Wayside 1 (PC) to Wayside 2 (RPi) seamlessly. 🚂
