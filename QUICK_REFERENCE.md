# Quick Reference - API Server Commands

## Starting the Server

### Main Computer (Required - Start FIRST!)

```bash
python start_unified_server.py
```

**Important**: Note the IP address shown (e.g., `192.168.1.100`)

## Running Components

### CTC (Main Computer)

```bash
# Local mode (testing, no server)
python ctc/ctc_ui_temp.py

# Remote mode (with server)
python ctc/ctc_ui_temp.py --server http://localhost:5000
```

### Track Controller Wayside #1 (Raspberry Pi or Main Computer)

```bash
# Local mode
cd track_controller/New_SW_Code
python sw_wayside_controller_ui.py

# Remote mode (Raspberry Pi)
python sw_wayside_controller_ui.py --server http://192.168.1.100:5000 --wayside-id 1
```

### Track Controller Wayside #2 (Raspberry Pi or Main Computer)

```bash
# Remote mode
python sw_wayside_controller_ui.py --server http://192.168.1.100:5000 --wayside-id 2
```

### Train Controller (Raspberry Pi - Already Working)

```bash
# Remote mode
python train_controller/ui/train_controller_hw_ui.py --train-id 1 --server http://192.168.1.100:5000
```

### Combined Test (Main Computer)

```bash
# After updating combine_ctc_wayside_test.py to use server
python combine_ctc_wayside_test.py
```

## Testing Commands

### Check Server Health

```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{
  "status": "ok",
  "message": "Unified Railway System API Server running"
}
```

### Get All Trains

```bash
curl http://localhost:5000/api/trains
```

### Get CTC State

```bash
curl http://localhost:5000/api/ctc/state
```

### Get Wayside State

```bash
curl http://localhost:5000/api/wayside/1/state
```

### Send Train Command (Example)

```bash
curl -X POST http://localhost:5000/api/train/1/state \
  -H "Content-Type: application/json" \
  -d '{"commanded_speed": 25.0, "commanded_authority": 500.0}'
```

## Troubleshooting

### Can't connect to server

```bash
# Check if server is running
curl http://localhost:5000/api/health

# Check firewall (Windows PowerShell as Admin)
netsh advfirewall firewall add rule name="Railway API Server" dir=in action=allow protocol=TCP localport=5000

# Check firewall (Linux)
sudo ufw allow 5000
```

### Port already in use

```bash
# Use different port
python start_unified_server.py --port 5001

# Then connect with
python sw_wayside_controller_ui.py --server http://localhost:5001
```

### Find your IP address

```bash
# Windows
ipconfig

# Linux/Mac
ifconfig
# or
ip addr show
```

Look for `192.168.x.x` or `10.0.x.x` address

### Test from Raspberry Pi

```bash
# Ping server
ping 192.168.1.100

# Test connection
curl http://192.168.1.100:5000/api/health
```

## File Locations

### Server Files
- `unified_api_server.py` - Main server code
- `start_unified_server.py` - Startup script

### API Clients
- `track_controller/api/wayside_api_client.py` - Wayside client
- `ctc/api/ctc_api_client.py` - CTC client
- `train_controller/api/train_controller_api_client.py` - Train client (already exists)

### JSON Files (Server manages these)
- `train_controller/data/train_states.json` - Train states
- `ctc_data.json` - CTC state
- `ctc_track_controller.json` - CTC → Wayside commands
- `track_controller/New_SW_Code/wayside_to_train.json` - Wayside → Train commands

## API Endpoints

### Train Controller
- `GET /api/trains` - All trains
- `GET /api/train/<id>/state` - Specific train
- `POST /api/train/<id>/state` - Update train

### Track Controller (Wayside)
- `GET /api/wayside/<id>/state` - Wayside state
- `POST /api/wayside/<id>/state` - Update wayside
- `GET /api/wayside/train_commands` - Commands to trains
- `POST /api/wayside/train_commands` - Update commands

### CTC
- `GET /api/ctc/state` - CTC state
- `POST /api/ctc/state` - Update CTC
- `GET /api/ctc/trains` - All trains
- `GET /api/ctc/trains/<name>` - Specific train
- `POST /api/ctc/trains/<name>` - Update train
- `GET /api/ctc/track_controller` - CTC → Wayside commands
- `POST /api/ctc/track_controller` - Update commands

### Track Model
- `GET /api/track_model/state` - Track state
- `POST /api/track_model/state` - Update track
- `GET /api/track_model/blocks` - Block data

### System
- `GET /api/health` - Server health check
- `GET /` - API documentation

## Deployment Checklist

### On Main Computer
- [ ] Install dependencies: `pip install flask flask-cors requests`
- [ ] Start server: `python start_unified_server.py`
- [ ] Note IP address (e.g., `192.168.1.100`)
- [ ] Test: `curl http://localhost:5000/api/health`
- [ ] Keep server running!

### On Each Raspberry Pi
- [ ] Install dependencies: `pip install requests`
- [ ] Copy track_controller or train_controller folder
- [ ] Test connection: `curl http://192.168.1.100:5000/api/health`
- [ ] Run with `--server` flag
- [ ] Verify "Remote Mode" in window title

### Verify Integration
- [ ] Server shows connection messages
- [ ] UI titles show "Remote Mode"
- [ ] Data updates appear in real-time
- [ ] Multiple clients can connect simultaneously
- [ ] No "file not found" errors

## Emergency Recovery

### If server crashes

```bash
# Restart server
python start_unified_server.py

# Check what's using the port (Windows)
netstat -ano | findstr :5000

# Kill process using port (Windows, as Admin)
taskkill /PID <process_id> /F

# Check what's using the port (Linux)
lsof -i :5000

# Kill process using port (Linux)
kill <process_id>
```

### If data is corrupted

```bash
# Backup and reset JSON files
cp ctc_data.json ctc_data.json.backup
echo "{}" > ctc_data.json

# Restart server
python start_unified_server.py
```

### Fall back to local mode

```bash
# Run without --server flag
python sw_wayside_controller_ui.py
# Uses local file I/O
```

## Performance Tips

- Server can handle 50+ clients simultaneously
- Polling interval: 500ms (adjustable)
- Network latency typical: < 10ms on local network
- JSON file size: Keep under 1MB for best performance

## Support

- Architecture diagram: `ARCHITECTURE_ANALYSIS.md`
- Full integration guide: `API_INTEGRATION_GUIDE.md`
- Implementation details: `train_controller/IMPLEMENTATION_SUMMARY.md`

