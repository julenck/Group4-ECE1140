import json
import os

def write_outputs_to_other_modules(outputs):
    """
    Write Train Model computed outputs to:
      1. train_to_controller.json
      2. train_to_trackmodel.json
    """

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # === 1️⃣ Write to Train Controller ===
    controller_path = os.path.join(base_dir, "train_to_controller.json")
    controller_data = {}

    controller_data.update({
        "train_velocity_mph": outputs.get("velocity_mph", 0.0),
        "train_temperature_F": 68,  # placeholder or from model if available
        "emergency_brake": False,   # you can later read actual state if implemented
        "engine_failure": False,
        "signal_pickup_failure": False,
        "brake_failure": False
    })

    with open(controller_path, "w") as f:
        json.dump(controller_data, f, indent=4)

    # === 2️⃣ Write to Track Model ===
    track_path = os.path.join(base_dir, "train_to_trackmodel.json")
    track_data = {}

    track_data.update({
        "number_of_passengers_disembarking": 11  # Example placeholder
    })

    with open(track_path, "w") as f:
        json.dump(track_data, f, indent=4)
