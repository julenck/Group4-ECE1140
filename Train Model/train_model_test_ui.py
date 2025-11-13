import tkinter as tk
from tkinter import ttk
import json, os, random
import requests
import sys

TRAIN_DATA_FILE = "train_data.json"
TRAIN_STATES_FILE = "../train_controller/data/train_states.json"
TRACK_OUTPUT_FILE = "../Track_Model/train_model_to_track_model.json"

os.chdir(os.path.dirname(os.path.abspath(__file__)))

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
    "crew_count": 2
}

class TrainModel:
    def __init__(self, specs):
        self.max_accel_ftps2 = specs["max_accel_ftps2"]
        self.service_brake_ftps2 = specs["service_brake_ftps2"]
        self.emergency_brake_ftps2 = specs["emergency_brake_ftps2"]
        self.capacity = specs["capacity"]
        self.crew_count = specs["crew_count"]
        self.velocity_mph = 0.0
        self.acceleration_ftps2 = 0.0
        self.position_yds = 0.0
        self.authority_yds = 0.0
        self.temperature_F = 68.0
        self.dt = 0.5
        self.left_door_open = False
        self.right_door_open = False
        self.current_station = ""
        self.next_station = ""

    def regulate_temperature(self, set_temp):
        err = set_temp - self.temperature_F
        max_rate = 0.025
        if abs(err) > 0.25:
            self.temperature_F += max_rate if err > 0 else -max_rate

    def update(self, commanded_speed, commanded_authority, speed_limit,
               current_station, next_station, side_door,
               emergency_brake, service_brake,
               engine_failure, brake_failure,
               set_temperature, left_door, right_door):
        if emergency_brake:
            self.acceleration_ftps2 = self.emergency_brake_ftps2
        else:
            if service_brake and not brake_failure:
                self.acceleration_ftps2 = self.service_brake_ftps2
            else:
                target_mph = min(commanded_speed, speed_limit if speed_limit > 0 else commanded_speed)
                target_ftps = target_mph / 0.681818
                cur_ftps = self.velocity_mph / 0.681818
                diff = target_ftps - cur_ftps
                raw = max(-self.max_accel_ftps2, min(self.max_accel_ftps2, diff / self.dt))
                if engine_failure and raw > 0:
                    raw = 0.0
                self.acceleration_ftps2 = raw
        delta_v_ftps = self.acceleration_ftps2 * self.dt
        self.velocity_mph = max(self.velocity_mph + delta_v_ftps * 0.681818, 0.0)
        delta_x_ft = (self.velocity_mph / 0.681818) * self.dt
        self.position_yds += delta_x_ft / 3.0
        self.authority_yds = commanded_authority
        self.left_door_open = left_door
        self.right_door_open = right_door
        self.regulate_temperature(set_temperature)
        self.current_station = current_station
        self.next_station = next_station
        return {
            "velocity_mph": self.velocity_mph,
            "acceleration_ftps2": self.acceleration_ftps2,
            "position_yds": self.position_yds,
            "authority_yds": self.authority_yds,
            "station_name": self.current_station,
            "next_station": self.next_station,
            "left_door_open": self.left_door_open,
            "right_door_open": self.right_door_open,
            "temperature_F": self.temperature_F
        }

class TrainModelTestUI(tk.Tk):
    def __init__(self, train_id=1, server_url=None):
        super().__init__()
        self.train_id = train_id
        self.server_url = server_url  # None = local mode, URL = remote mode
        title = f"Train {train_id} Model Test UI"
        if server_url:
            title += " (Remote Mode)"
        self.title(title)
        self.geometry("1100x700")
        self.specs = self.load_specs()
        self.model = TrainModel(self.specs)
        self.passengers_onboard = self.specs["crew_count"]
        self.last_disembark_station = None
        self.last_disembarking = 0
        self.boarding_last_cycle = 0
        
        # Create main container with two columns
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left column
        left_column = ttk.Frame(main_container)
        left_column.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Right column
        right_column = ttk.Frame(main_container)
        right_column.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        self.build_inputs(left_column)
        self.build_failure_panel(left_column)
        self.build_buttons(right_column)
        self.build_passenger_panel(right_column)
        self.build_outputs(right_column)
        self.update_loop()

    def load_specs(self):
        if os.path.exists(TRAIN_DATA_FILE):
            try:
                with open(TRAIN_DATA_FILE, "r") as f:
                    data = json.load(f)
                    specs = data.get("specs", {})
                    for k,v in DEFAULT_SPECS.items():
                        specs.setdefault(k,v)
                    return specs
            except:
                pass
        return DEFAULT_SPECS

    def build_inputs(self, parent):
        frm = ttk.LabelFrame(parent, text="Inputs")
        frm.pack(fill="x", pady=5)
        self.entries = {}
        fields = [
            ("Commanded Speed (mph)", "40"),
            ("Commanded Authority (yds)", "0"),
            ("Speed Limit (mph)", "30"),
            ("Current Station", "Central Station"),
            ("Next Station", "Park Street"),
            ("Side Door (Left/Right)", "Right"),
            ("Set Temperature (°F)", "70"),
            ("Passengers Boarding", "15")
        ]
        for label, default in fields:
            row = ttk.Frame(frm)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=label, width=24).pack(side="left")
            e = ttk.Entry(row, width=18)
            e.insert(0, default)
            e.pack(side="left")
            self.entries[label] = e
        # Doors
        door_row = ttk.Frame(frm); door_row.pack(fill="x", pady=2)
        ttk.Label(door_row, text="Left Door Open", width=24).pack(side="left")
        self.var_left_door = tk.BooleanVar(value=False)
        ttk.Checkbutton(door_row, variable=self.var_left_door).pack(side="left")
        door_row2 = ttk.Frame(frm); door_row2.pack(fill="x", pady=2)
        ttk.Label(door_row2, text="Right Door Open", width=24).pack(side="left")
        self.var_right_door = tk.BooleanVar(value=False)
        ttk.Checkbutton(door_row2, variable=self.var_right_door).pack(side="left")

    def build_failure_panel(self, parent):
        frm = ttk.LabelFrame(parent, text="Failures / Safety")
        frm.pack(fill="x", pady=5)
        self.var_engine = tk.BooleanVar(value=False)
        self.var_signal = tk.BooleanVar(value=False)
        self.var_brake = tk.BooleanVar(value=False)
        self.var_emergency = tk.BooleanVar(value=False)
        self.var_service = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="Engine Failure", variable=self.var_engine).pack(anchor="w")
        ttk.Checkbutton(frm, text="Signal Pickup Failure", variable=self.var_signal).pack(anchor="w")
        ttk.Checkbutton(frm, text="Brake Failure", variable=self.var_brake).pack(anchor="w")
        ttk.Checkbutton(frm, text="Service Brake", variable=self.var_service).pack(anchor="w")
        ttk.Checkbutton(frm, text="Emergency Brake", variable=self.var_emergency).pack(anchor="w")
        self.lbl_status = ttk.Label(frm, text="Status: OK")
        self.lbl_status.pack(anchor="w")

    def build_passenger_panel(self, parent):
        frm = ttk.LabelFrame(parent, text="Passengers")
        frm.pack(fill="x", pady=5)
        self.lbl_onboard = ttk.Label(frm, text=f"Onboard: {self.passengers_onboard}")
        self.lbl_onboard.pack(anchor="w")
        self.lbl_boarding = ttk.Label(frm, text="Boarding: 0")
        self.lbl_boarding.pack(anchor="w")
        self.lbl_disembark = ttk.Label(frm, text="Disembarking: 0")
        self.lbl_disembark.pack(anchor="w")
        ttk.Label(frm, text=f"Capacity: {self.specs['capacity']} (Crew {self.specs['crew_count']})").pack(anchor="w")

    def build_outputs(self, parent):
        frm = ttk.LabelFrame(parent, text="Outputs")
        frm.pack(fill="both", expand=True, pady=5)
        self.txt_out = tk.Text(frm, height=18)
        self.txt_out.pack(fill="both", expand=True)

    def build_buttons(self, parent):
        bar = ttk.LabelFrame(parent, text="Controls")
        bar.pack(fill="x", pady=5)
        ttk.Button(bar, text="Step Simulation", command=self.step_once).pack(fill="x", padx=10, pady=5)
        ttk.Button(bar, text="Write train_data.json", command=self.write_train_data_only).pack(fill="x", padx=10, pady=5)

    def parse_inputs(self):
        def f(name, cast=str):
            return cast(self.entries[name].get())
        try:
            commanded_speed = float(self.entries["Commanded Speed (mph)"].get())
            commanded_authority = float(self.entries["Commanded Authority (yds)"].get())
            speed_limit = float(self.entries["Speed Limit (mph)"].get())
            current_station = f("Current Station")
            next_station = f("Next Station")
            side_door = f("Side Door (Left/Right)")
            set_temp = float(self.entries["Set Temperature (°F)"].get())
            passengers_boarding = int(self.entries["Passengers Boarding"].get())
        except ValueError:
            return None
        return {
            "commanded_speed": commanded_speed,
            "commanded_authority": commanded_authority,
            "speed_limit": speed_limit,
            "current_station": current_station,
            "next_station": next_station,
            "side_door": side_door,
            "set_temperature": set_temp,
            "passengers_boarding": passengers_boarding,
            "left_door": self.var_left_door.get(),
            "right_door": self.var_right_door.get(),
            "engine_failure": self.var_engine.get(),
            "signal_failure": self.var_signal.get(),
            "brake_failure": self.var_brake.get(),
            "emergency_brake": self.var_emergency.get(),
            "service_brake": self.var_service.get()
        }

    def compute_disembark(self, station, velocity):
        if not station:
            return 0
        stopped = velocity < 0.5
        if stopped and station != self.last_disembark_station:
            non_crew = max(0, self.passengers_onboard - self.specs["crew_count"])
            max_out = min(30, int(non_crew * 0.4))
            count = random.randint(0, max_out) if max_out > 0 else 0
            self.last_disembark_station = station
            self.last_disembarking = count
            return count
        if stopped:
            return self.last_disembarking
        return 0

    def step_once(self):
        inp = self.parse_inputs()
        if not inp:
            return
        out = self.model.update(
            commanded_speed=inp["commanded_speed"],
            commanded_authority=inp["commanded_authority"],
            speed_limit=inp["speed_limit"],
            current_station=inp["current_station"],
            next_station=inp["next_station"],
            side_door=inp["side_door"],
            emergency_brake=inp["emergency_brake"],
            service_brake=inp["service_brake"],
            engine_failure=inp["engine_failure"],
            brake_failure=inp["brake_failure"],
            set_temperature=inp["set_temperature"],
            left_door=inp["left_door"],
            right_door=inp["right_door"]
        )
        passengers_out = self.compute_disembark(inp["current_station"], out["velocity_mph"])
        stopped = out["velocity_mph"] < 0.5 and inp["current_station"]
        if stopped:
            # apply disembark
            self.passengers_onboard = max(self.specs["crew_count"], self.passengers_onboard - passengers_out)
            # boarding
            avail = self.specs["capacity"] - self.passengers_onboard
            actual_board = min(avail, max(0, inp["passengers_boarding"]))
            self.passengers_onboard += actual_board
            self.boarding_last_cycle = actual_board
        else:
            self.boarding_last_cycle = 0
        self.write_jsons(inp, out, passengers_out)
        self.render(out, inp, passengers_out)
        self.update_passenger_labels(passengers_out)
        self.update_status()

    def write_jsons(self, inp, out, passengers_out):
        # Read existing train_data to preserve all sections
        existing_data = {}
        if os.path.exists(TRAIN_DATA_FILE):
            try:
                with open(TRAIN_DATA_FILE, "r") as f:
                    existing_data = json.load(f)
            except:
                pass
        
        # Prepare inputs and outputs
        inputs_dict = {
            "commanded speed": inp["commanded_speed"],
            "commanded authority": inp["commanded_authority"],
            "speed limit": inp["speed_limit"],
            "current station": inp["current_station"],
            "next station": inp["next_station"],
            "side_door": inp["side_door"],
            "passengers_boarding": inp["passengers_boarding"],
            "passengers_onboard": self.passengers_onboard,
            "train_model_engine_failure": inp["engine_failure"],
            "train_model_signal_failure": inp["signal_failure"],
            "train_model_brake_failure": inp["brake_failure"],
            "emergency_brake": inp["emergency_brake"]
        }
        
        # Start with existing data to preserve all trains
        train_data = existing_data if existing_data else {}
        
        # Ensure root level has specs
        if "specs" not in train_data:
            train_data["specs"] = self.specs
        
        # Preserve train_model_* failure flags from current file state (Train Model UI controls these)
        existing_root_inputs = train_data.get("inputs", {})
        for flag in ["train_model_engine_failure", "train_model_signal_failure", "train_model_brake_failure"]:
            if flag in existing_root_inputs:
                inputs_dict[flag] = existing_root_inputs[flag]
        
        # Update root level inputs ONLY (Train Model will generate outputs)
        train_data["inputs"] = inputs_dict
        
        # Update train_1 section (for multi-train mode)
        if "train_1" not in train_data:
            train_data["train_1"] = {"specs": self.specs}
        elif not isinstance(train_data["train_1"], dict):
            train_data["train_1"] = {"specs": self.specs}
        
        # Prepare inputs for train_1, preserving failure flags from current state
        train_1_inputs = dict(inputs_dict)
        existing_train_1_inputs = train_data.get("train_1", {}).get("inputs", {})
        for flag in ["train_model_engine_failure", "train_model_signal_failure", "train_model_brake_failure"]:
            if flag in existing_train_1_inputs:
                train_1_inputs[flag] = existing_train_1_inputs[flag]
        
        # Always update inputs for train_1 (Train Model generates outputs)
        train_data["train_1"]["inputs"] = train_1_inputs
        
        try:
            # Write atomically to avoid corruption
            temp_file = TRAIN_DATA_FILE + ".tmp"
            with open(temp_file, "w") as f:
                json.dump(train_data, f, indent=4)
            os.replace(temp_file, TRAIN_DATA_FILE)
        except Exception as e:
            print("train_data write error:", e)
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        
        # If in remote mode, also send to server
        if self.server_url:
            try:
                # Send ONLY inputs to server
                # train_velocity and train_temperature come from train_data.json via server sync thread
                # Do NOT send outputs here to avoid race condition with sync thread
                server_updates = {
                    "commanded_speed": inp["commanded_speed"],
                    "commanded_authority": inp["commanded_authority"],
                    "speed_limit": inp["speed_limit"],
                    "current_station": inp["current_station"],
                    "next_stop": inp["next_station"],
                    "station_side": inp["side_door"],
                    "train_model_engine_failure": inp["engine_failure"],
                    "train_model_signal_failure": inp["signal_failure"],
                    "train_model_brake_failure": inp["brake_failure"]
                }
                response = requests.post(
                    f"{self.server_url}/api/train/{self.train_id}/state",
                    json=server_updates,
                    timeout=1.0
                )
                if response.status_code != 200:
                    print(f"[Test UI] Server update returned {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"[Test UI] Error sending to server: {e}")
        
        track_out = {"passengers_disembarking": passengers_out}
        try:
            with open(TRACK_OUTPUT_FILE, "w") as f:
                json.dump(track_out, f, indent=4)
        except Exception as e:
            print("track output write error:", e)
        
        # NOTE: We DO NOT write to train_states.json anymore!
        # The Train Controller owns that file and updates it based on train_data.json.
        # Writing here was causing race conditions and resetting power_command.

    def render(self, out, inp, passengers_out):
        self.txt_out.delete("1.0", "end")
        lines = {
            "Velocity (mph)": f"{out['velocity_mph']:.2f}",
            "Acceleration (ft/s²)": f"{out['acceleration_ftps2']:.2f}",
            "Position (yds)": f"{out['position_yds']:.1f}",
            "Authority (yds)": f"{out['authority_yds']:.1f}",
            "Temperature (°F)": f"{out['temperature_F']:.1f}",
            "Current Station": out["station_name"],
            "Next Station": out["next_station"],
            "Side Door": inp["side_door"],
            "Left Door Open": out["left_door_open"],
            "Right Door Open": out["right_door_open"],
            "Passengers Onboard": self.passengers_onboard,
            "Passengers Boarding": self.boarding_last_cycle,
            "Passengers Disembarking": passengers_out,
            "Engine Failure": inp["engine_failure"],
            "Signal Failure": inp["signal_failure"],
            "Brake Failure": inp["brake_failure"],
            "Emergency Brake": inp["emergency_brake"],
            "Service Brake": inp["service_brake"]
        }
        for k,v in lines.items():
            self.txt_out.insert("end", f"{k}: {v}\n")

    def update_passenger_labels(self, disembark):
        self.lbl_onboard.config(text=f"Onboard: {self.passengers_onboard}")
        self.lbl_boarding.config(text=f"Boarding: {self.boarding_last_cycle}")
        self.lbl_disembark.config(text=f"Disembarking: {disembark}")

    def update_status(self):
        active = []
        if self.var_engine.get(): active.append("Engine")
        if self.var_signal.get(): active.append("Signal")
        if self.var_brake.get(): active.append("Brake")
        status = " / ".join(active) if active else "OK"
        if self.var_emergency.get():
            status += " | EMERGENCY"
        self.lbl_status.config(text=f"Status: {status}")

    def write_train_data_only(self):
        # Single manual write without advancing physics
        self.step_once()

    def update_loop(self):
        # Auto step each second
        self.step_once()
        self.after(int(self.model.dt * 1000), self.update_loop)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train Model Test UI")
    parser.add_argument("--train-id", type=int, default=1,
                        help="Train ID for multi-train mode (default: 1)")
    parser.add_argument("--server", type=str, default=None,
                        help="Server URL for remote mode (e.g., http://192.168.1.100:5000)")
    args = parser.parse_args()
    
    app = TrainModelTestUI(train_id=args.train_id, server_url=args.server)
    app.mainloop()
