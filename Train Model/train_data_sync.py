import json
import os

# === File paths ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRAIN_DATA_FILE = os.path.join(BASE_DIR, "train_data.json")
TRAIN_STATES_FILE = os.path.join(BASE_DIR, "../train_controller/data/train_states.json")


def sync_train_data():
    """
    Synchronize input fields in train_data.json
    with values from train_controller/data/train_states.json.
    This keeps Train Model’s input data up to date.
    """
    try:
        # 1. Load train_data.json
        with open(TRAIN_DATA_FILE, "r") as f:
            train_data = json.load(f)

        # 2. Load train_states.json (from Train Controller)
        with open(TRAIN_STATES_FILE, "r") as f:
            states = json.load(f)

        # 3. Update only the "inputs" section in train_data.json
        train_data["inputs"].update({
            "commanded speed": states.get("commanded_speed", 0),
            "commanded authority": states.get("commanded_authority", 0),
            "speed limit": states.get("speed_limit", 30),
            "side_door": states.get("station_side", "Right"),
            "current station": states.get("next_stop", "Unknown"),
            "next station": states.get("next_stop", "Unknown"),
            "station name": states.get("next_stop", "Unknown")
        })

        # 4. Save the updated JSON
        with open(TRAIN_DATA_FILE, "w") as f:
            json.dump(train_data, f, indent=4)

        print("[SYNC SUCCESS] train_data.json updated from train_states.json ")

    except Exception as e:
        print(f"[SYNC ERROR] {e}")


if __name__ == "__main__":
    sync_train_data()

{
  "templates": [
    { "id": 1, "speed": 0, "mass": 40000, "...": "..." },
    { "id": 2, "speed": 0, "mass": 42000, "...": "..." },
    { "id": 3, "...": "..." }
  ],
  "beacons": [
    { "block": 12, "data": "..." },
    { "block": 13, "data": "..." }
  ],
  "trainStates": {
    "train1": { "templateId": 1, "speed": 0, "mass": 40000, "...": "..." },
    "train2": { "templateId": 2, "speed": 0, "mass": 42000, "...": "..." }
  }
}
