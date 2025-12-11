import os, json, time, random

# Optional time controller integration
try:
    from time_controller import get_time_controller
except Exception:
    get_time_controller = None

# === FIXED ABSOLUTE PATHS (MATCHING TRACK MODEL FIX) ===

# Folder containing Train_Model/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Train_Model
PARENT_DIR = os.path.dirname(BASE_DIR)  # Group4-ECE1140

# Ensure train_controller folder exists
TRAIN_CONTROLLER_DIR = os.path.join(PARENT_DIR, "train_controller", "data")
os.makedirs(TRAIN_CONTROLLER_DIR, exist_ok=True)

# Train controller shared state
TRAIN_STATES_FILE = os.path.join(TRAIN_CONTROLLER_DIR, "train_states.json")

# Train Model JSONs (stay inside Train_Model)
TRAIN_DATA_FILE = os.path.join(BASE_DIR, "train_data.json")
TRACK_INPUT_FILE = os.path.join(PARENT_DIR, "track_model_Train_Model.json")

# Wayside to Train JSON (from track_controller)
WAYSIDE_TO_TRAIN_FILE = os.path.join(PARENT_DIR, "track_controller", "New_SW_Code", "wayside_to_train.json")


# === Safe IO ===
def safe_read_json(path):
    # Retry up to 3 times to handle race conditions
    for attempt in range(3):
        try:
            with open(path, "r") as f:
                data = json.load(f)
                return data if isinstance(data, (dict, list)) else None
        except json.JSONDecodeError:
            # Race condition - file was being written
            if attempt < 2:
                time.sleep(0.02)  # Wait 20ms before retry
                continue
            else:
                print(f"[WARNING] Failed to read {path} after 3 attempts (race condition)")
            #   return {}
                return data
        except FileNotFoundError:
            return {}
        except Exception as e:
            print(f"[WARNING] Unexpected error reading {path}: {e}")
            return {}


def safe_write_json(path, data):
    # Sort keys if writing to train_states.json to maintain consistent order (train_1, train_2, etc.)
    if "train_states.json" in path and isinstance(data, dict):
        data = {k: data[k] for k in sorted(data.keys())}
    
    payload = json.dumps(data, indent=4)
    out_dir = os.path.dirname(os.path.abspath(path))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    
    # For train_states.json, use direct write (Train Controller also uses direct write)
    # Atomic writes cause too many PermissionErrors on Windows with multiple processes
    if "train_states.json" in path:
        with open(path, "w") as f:
            f.write(payload)
        return
    
    # For other files (train_data.json, etc), use atomic write with fallback
    tmp = path + ".tmp"
    for attempt in range(3):
        try:
            with open(tmp, "w") as f:
                f.write(payload)
            os.replace(tmp, path)
            return
        except PermissionError:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
            time.sleep(0.1 * (attempt + 1))
        except Exception:
            break
    # Fallback to direct write
    with open(path, "w") as f:
        f.write(payload)


# === Train Data shape ===
DEFAULT_SPECS = {
    "length_ft": 66.0,
    "width_ft": 10.0,
    "height_ft": 11.5,
    "mass_lbs": 90100,
    "max_power_hp": 169,
    "max_accel_ftps2": 1.64,
    "service_brake_ftps2": -3.94,
    "emergency_brake_ftps2": -8.86,
    "capacity": 222,
    "crew_count": 2,
    "passengers_onboard": 53
}


def ensure_train_data(path):
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
        except Exception:
            data = {}
    specs = data.get("specs", {})
    for k, v in DEFAULT_SPECS.items():
        specs.setdefault(k, v)
    data["specs"] = specs
    data.setdefault("inputs", {})
    data.setdefault("outputs", {})
    safe_write_json(path, data)
    return data


# === Track input loader (multi-train aware, keys with spaces) ===
def read_track_input(train_index: int = 0):
    t = safe_read_json(TRACK_INPUT_FILE)
    if not isinstance(t, dict):
        return {}

    # Multi-train keyed format: *_train_#
    if any("_train_" in k for k in t.keys()):
        keys = sorted([k for k in t.keys() if "_train_" in k])
        if not keys:
            return {}
        idx = train_index if 0 <= train_index < len(keys) else 0
        entry = t.get(keys[idx], {})
        if not isinstance(entry, dict):
            return {}
        block = (
            entry.get("block", {}) if isinstance(entry.get("block", {}), dict) else {}
        )
        beacon = (
            entry.get("beacon", {}) if isinstance(entry.get("beacon", {}), dict) else {}
        )
        mapped = {
            "commanded speed": block.get("commanded speed"),
            "commanded authority": block.get("commanded authority"),
            "speed limit": beacon.get("speed limit"),
            "side_door": beacon.get("side_door"),
            "current station": beacon.get("current station"),
            "next station": beacon.get("next station"),
            "passengers_boarding": beacon.get("passengers_boarding"),
        }
        return {k: v for k, v in mapped.items() if v is not None}

    # Legacy flat fallback
    block = t.get("block", {}) if isinstance(t.get("block", {}), dict) else {}
    beacon = t.get("beacon", {}) if isinstance(t.get("beacon", {}), dict) else {}
    mapped = {
        "commanded speed": block.get("commanded_speed"),
        "commanded authority": block.get("commanded_authority"),
        "speed limit": beacon.get("speed_limit"),
        "side_door": beacon.get("station_side"),
        "current station": beacon.get("current_station"),
        "next station": beacon.get("next_stop"),
    }
    train = t.get("train", {}) if isinstance(t.get("train", {}), dict) else {}
    q = train.get("passengers_boarding_")
    if isinstance(q, list) and q:
        idx = train_index if 0 <= train_index < len(q) else 0
        mapped["passengers_boarding"] = int(q[idx])
    return {k: v for k, v in mapped.items() if v is not None}


# === Merge inputs ===
def merge_inputs(td_inputs: dict, track_in: dict, ctrl: dict, onboard_fallback: int):
    merged = dict(td_inputs) if isinstance(td_inputs, dict) else {}
    for k, v in (track_in or {}).items():
        if v is not None and not k.startswith("train_model_"):
            merged[k] = v
    # controller-provided fallbacks (train_states.json)
    merged.setdefault("next station", (ctrl or {}).get("next_stop", ""))
    merged.setdefault("side_door", (ctrl or {}).get("station_side", ""))
    merged.setdefault("passengers_boarding", 0)
    merged.setdefault("passengers_onboard", onboard_fallback)
    merged.setdefault("train_model_engine_failure", False)
    merged.setdefault("train_model_signal_failure", False)
    merged.setdefault("train_model_brake_failure", False)
    return merged


# === Track motion write-back ONLY (no passengers_disembarking) ===
def update_track_motion(
    train_index: int, acceleration_ftps2: float, velocity_mph: float
):
    """
    Update the current motion state inside track_model_Train_Model.json.

    Motion states:
        velocity <= 0.01 mph -> "stopped"
        acceleration < 0     -> "braking"
        else                  -> "moving"
    """
    motion_state = (
        "stopped"
        if velocity_mph <= 0.01
        else ("braking" if acceleration_ftps2 < 0 else "moving")
    )

    data = safe_read_json(TRACK_INPUT_FILE)
    if not isinstance(data, dict) or not data:
        # Legacy single structure (create if empty)
        if isinstance(data, dict):
            legacy = data
        else:
            legacy = {}
        legacy_motion = legacy.get("motion", {})
        if not isinstance(legacy_motion, dict):
            legacy_motion = {}
        legacy_motion["current motion"] = motion_state
        legacy["motion"] = legacy_motion
        safe_write_json(TRACK_INPUT_FILE, legacy)
        return

    # Multi-train: find sorted keys *_train_*
    keys = sorted([k for k in data.keys() if "_train_" in k])
    if not keys:
        # Fallback to legacy style
        legacy_motion = data.get("motion", {})
        if not isinstance(legacy_motion, dict):
            legacy_motion = {}
        legacy_motion["current motion"] = motion_state
        data["motion"] = legacy_motion
        safe_write_json(TRACK_INPUT_FILE, data)
        return

    idx = train_index if 0 <= train_index < len(keys) else 0
    entry_key = keys[idx]
    entry = data.get(entry_key, {})
    if not isinstance(entry, dict):
        entry = {}
    motion = entry.get("motion", {})
    if not isinstance(motion, dict):
        motion = {}
    motion["current motion"] = motion_state
    entry["motion"] = motion
    data[entry_key] = entry
    safe_write_json(TRACK_INPUT_FILE, data)


# === Core Train Model ===
class TrainModel:
    def __init__(self, specs):
        self.specs = specs
        self.crew_count = specs.get("crew_count", 2)
        self.max_accel_ftps2 = specs.get("max_accel_ftps2", 1.64)
        self.service_brake_ftps2 = specs.get("service_brake_ftps2", -3.94)
        self.emergency_brake_ftps2 = specs.get("emergency_brake_ftps2", -8.86)
        self.max_power_hp = specs.get("max_power_hp", 169)
        self.mass_lbs = specs.get("mass_lbs", 90100)
        self.velocity_mph = 0.0
        self.acceleration_ftps2 = 0.0
        self.position_yds = 0.0
        self.authority_yds = 0.0
        self.temperature_F = 68.0
        self.base_dt = 0.5  # Base time step
        self.dt = self.base_dt  # Effective time step (may be modified by time controller)

    def regulate_temperature(self, set_temperature):
        diff = set_temperature - self.temperature_F
        rate = 0.25
        if abs(diff) > 0.2:
            self.temperature_F += rate if diff > 0 else -rate
        return self.temperature_F

    def update(
        self,
        commanded_speed,
        commanded_authority,
        speed_limit,
        current_station,
        next_station,
        side_door,
        power_command=0,
        emergency_brake=False,
        service_brake=False,
        engine_failure=False,
        brake_failure=False,
        set_temperature=70.0,
        left_door=False,
        right_door=False,
        driver_velocity=0.0,
    ):
        # Update effective dt based on time controller
        self.dt = self.base_dt
        if get_time_controller:
            try:
                tc = get_time_controller()
                self.dt = tc.get_effective_dt()
            except Exception:
                pass  # Fall back to base_dt

        if emergency_brake:
            self.acceleration_ftps2 = self.emergency_brake_ftps2
        else:
            if service_brake and not brake_failure:
                self.acceleration_ftps2 = self.service_brake_ftps2
            else:
                mass_kg = self.mass_lbs * 0.453592
                velocity_ms = max(0.1, self.velocity_mph * 0.44704)
                force_N = power_command / velocity_ms if power_command > 0 else 0
                accel_ms2 = force_N / mass_kg if mass_kg > 0 else 0
                accel_ftps2 = accel_ms2 * 3.28084
                if engine_failure and accel_ftps2 > 0:
                    self.acceleration_ftps2 = 0.0
                else:
                    self.acceleration_ftps2 = max(
                        -self.max_accel_ftps2, min(self.max_accel_ftps2, accel_ftps2)
                    )
        self.velocity_mph = max(
            0.0, self.velocity_mph + self.acceleration_ftps2 * self.dt * 0.681818
        )
        self.position_yds += (self.velocity_mph / 0.681818) * self.dt / 3.0
        self.authority_yds = float(commanded_authority or 0.0)
        self.regulate_temperature(set_temperature)
        return {
            "velocity_mph": self.velocity_mph,
            "acceleration_ftps2": self.acceleration_ftps2,
            "position_yds": self.position_yds,
            "authority_yds": self.authority_yds,
            "station_name": current_station or "",
            "next_station": next_station or "",
            "left_door_open": bool(left_door),
            "right_door_open": bool(right_door),
            "speed_limit": float(speed_limit or 0.0),
            "temperature_F": self.temperature_F,
        }


def compute_passengers_disembarking(
    last_station_state: dict,
    station: str,
    velocity_mph: float,
    passengers_onboard: int,
    crew_count: int,
):
    prev_station = last_station_state.get("station")
    prev_count = last_station_state.get("count", 0)
    station = (station or "").strip()
    if not station or velocity_mph >= 0.5:
        return 0, {"station": prev_station, "count": prev_count}
    if prev_station != station:
        non_crew = max(0, int(passengers_onboard) - crew_count)
        max_out = min(30, int(non_crew * 0.4))
        count = random.randint(0, max_out) if max_out > 0 else 0
        return count, {"station": station, "count": count}
    return int(prev_count), {"station": prev_station, "count": prev_count}


def sync_wayside_to_train_data():
    """
    Reads wayside_to_train.json and updates corresponding train inputs in train_data.json.
    Maps: "Train 1" -> "train_1", "Train 2" -> "train_2", etc.
    Updates: commanded speed, commanded authority, current station, next station
    """
    if not os.path.exists(WAYSIDE_TO_TRAIN_FILE):
        return
    
    wayside_data = safe_read_json(WAYSIDE_TO_TRAIN_FILE)
    if not isinstance(wayside_data, dict):
        return
    
    train_data = safe_read_json(TRAIN_DATA_FILE)
    if not isinstance(train_data, dict):
        train_data = {}
    
    updated = False
    
    for wayside_key, wayside_info in wayside_data.items():
        # Parse "Train 1" -> train number 1
        if not wayside_key.startswith("Train "):
            continue
        try:
            train_num = int(wayside_key.split(" ")[1])
        except (IndexError, ValueError):
            continue
        
        train_key = f"train_{train_num}"
        
        # Ensure train section exists
        if train_key not in train_data:
            train_data[train_key] = {"specs": DEFAULT_SPECS, "inputs": {}, "outputs": {}}
        if "inputs" not in train_data[train_key]:
            train_data[train_key]["inputs"] = {}
        
        inputs = train_data[train_key]["inputs"]
        
        # Map wayside fields to train_data inputs
        if "Commanded Speed" in wayside_info:
            inputs["commanded speed"] = float(wayside_info["Commanded Speed"])
            updated = True
        
        if "Commanded Authority" in wayside_info:
            inputs["commanded authority"] = float(wayside_info["Commanded Authority"])
            updated = True
        
        if "Beacon" in wayside_info and isinstance(wayside_info["Beacon"], dict):
            beacon = wayside_info["Beacon"]
            if "Current Station" in beacon:
                inputs["current station"] = str(beacon["Current Station"])
                updated = True
            if "Next Station" in beacon:
                inputs["next station"] = str(beacon["Next Station"])
                updated = True
    
    if updated:
        safe_write_json(TRAIN_DATA_FILE, train_data)
