import json
import os

def write_outputs_to_other_modules(inputs, outputs):
    """
    Write only required fields to:
      - train_to_controller.json
      - train_to_trackmodel.json
    The output fields match the Train Controller’s required format.
    """

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # === 1️⃣ Write to Train Controller ===
    controller_path = os.path.join(base_dir, "train_to_controller.json")

    controller_data = {
        # 1. Commanded Speed (from Train Controller inputs)
        "commanded speed": inputs.get("commanded speed", 0.0),

        # 2. Commanded Authority
        "commanded authority": inputs.get("commanded authority", 0.0),

        # 3. Beacon Data
        "beacon data": inputs.get("beacon data", "None"),

        # 4. Failure Modes (3 subfields)
        "failure modes": {
            "engine failure": inputs.get("engine failure", False),
            "signal pickup failure": inputs.get("signal failure", False),
            "brake failure": inputs.get("brake failure", False)
        },

        # 5. Train Velocity (from Train Model calculation)
        "train velocity": outputs.get("velocity_mph", 0.0),

        # 6. Emergency Brake
        "emergency brake": False,  # replace later if model supports it

        # 7. Train Temperature
        "train temperature": 68  # static or dynamic
    }

    with open(controller_path, "w") as f:
        json.dump(controller_data, f, indent=4)

    # === 2️⃣ Write to Track Model ===
    track_path = os.path.join(base_dir, "train_to_trackmodel.json")

    # Example: only output passenger count
    num_disembarking = 11 if outputs.get("velocity_mph", 0) < 1 else 0
    track_data = {"number_of_passengers_disembarking": num_disembarking}

    with open(track_path, "w") as f:
        json.dump(track_data, f, indent=4)

