import json
import os

def write_outputs_to_other_modules(inputs, outputs):
    """
    Write real Train Model computation results to:
      1. train_to_controller.json (for Train Controller)
      2. train_to_trackmodel.json (for Track Model)
    Combines both current inputs (from train_data.json)
    and calculated outputs (from train_model_ui).
    """

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # === 1️⃣ Write to Train Controller ===
    controller_path = os.path.join(base_dir, "train_to_controller.json")

    controller_data = {
        # ---- From Train Model simulation results ----
        "train_velocity_mph": outputs.get("velocity_mph", 0.0),
        "train_acceleration_ftps2": outputs.get("acceleration_ftps2", 0.0),
        "train_position_yds": outputs.get("position_yds", 0.0),
        "authority_remaining_yds": outputs.get("authority_yds", 0.0),
        "current_station": outputs.get("station_name", "Unknown"),
        "next_station": outputs.get("next_station", "Unknown"),
        "left_door_open": outputs.get("left_door_open", False),
        "right_door_open": outputs.get("right_door_open", False),
        "speed_limit_mph": outputs.get("speed_limit", 0.0),

        # ---- From Train Controller commands ----
        "commanded_speed_mph": inputs.get("commanded speed", 0.0),
        "commanded_authority_yds": inputs.get("commanded authority", 0.0),
        "beacon_data": inputs.get("beacon data", "None"),

        # ---- System status ----
        "train_temperature_F": 68,     # Replace with actual model variable if available
        "emergency_brake": False,      # Replace if your model has a flag for this
        "failure_modes": {
            "engine_failure": inputs.get("engine failure", False),
            "signal_pickup_failure": inputs.get("signal failure", False),
            "brake_failure": inputs.get("brake failure", False)
        }
    }

    with open(controller_path, "w") as f:
        json.dump(controller_data, f, indent=4)

    # === 2️⃣ Write to Track Model ===
    track_path = os.path.join(base_dir, "train_to_trackmodel.json")

    # Example: passengers disembark only when train stops
    num_disembarking = 11 if outputs.get("velocity_mph", 0) < 1 else 0

    track_data = {
        "number_of_passengers_disembarking": num_disembarking
    }

    with open(track_path, "w") as f:
        json.dump(track_data, f, indent=4)

