import tkinter as tk
from tkinter import ttk
import json, os, random

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
    def __init__(self):
        super().__init__()
        self.title("Train Model Test UI (Full Feature)")
        self.geometry("900x700")
        self.specs = self.load_specs()
        self.model = TrainModel(self.specs)
        self.passengers_onboard = self.specs["crew_count"]
        self.last_disembark_station = None
        self.last_disembarking = 0
        self.boarding_last_cycle = 0
        self.build_inputs()
        self.build_outputs()
        self.build_passenger_panel()
        self.build_failure_panel()
        self.build_buttons()
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

    def build_inputs(self):
        frm = ttk.LabelFrame(self, text="Inputs")
        frm.pack(fill="x", padx=10, pady=5)
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

    def build_failure_panel(self):
        frm = ttk.LabelFrame(self, text="Failures / Safety")
        frm.pack(fill="x", padx=10, pady=5)
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

    def build_passenger_panel(self):
        frm = ttk.LabelFrame(self, text="Passengers")
        frm.pack(fill="x", padx=10, pady=5)
        self.lbl_onboard = ttk.Label(frm, text=f"Onboard: {self.passengers_onboard}")
        self.lbl_onboard.pack(anchor="w")
        self.lbl_boarding = ttk.Label(frm, text="Boarding: 0")
        self.lbl_boarding.pack(anchor="w")
        self.lbl_disembark = ttk.Label(frm, text="Disembarking: 0")
        self.lbl_disembark.pack(anchor="w")
        ttk.Label(frm, text=f"Capacity: {self.specs['capacity']} (Crew {self.specs['crew_count']})").pack(anchor="w")

    def build_outputs(self):
        frm = ttk.LabelFrame(self, text="Outputs")
        frm.pack(fill="both", expand=True, padx=10, pady=5)
        self.txt_out = tk.Text(frm, height=18)
        self.txt_out.pack(fill="both", expand=True)

    def build_buttons(self):
        bar = ttk.Frame(self); bar.pack(fill="x", padx=10, pady=5)
        ttk.Button(bar, text="Step Simulation", command=self.step_once).pack(side="left", padx=5)
        ttk.Button(bar, text="Write train_data.json", command=self.write_train_data_only).pack(side="left", padx=5)

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
        train_data = {
            "specs": self.specs,
            "inputs": {
                "commanded speed": inp["commanded_speed"],
                "commanded authority": inp["commanded_authority"],
                "speed limit": inp["speed_limit"],
                "current station": inp["current_station"],
                "next station": inp["next_station"],
                "side_door": inp["side_door"],
                "passengers_boarding": inp["passengers_boarding"],
                "engine_failure": inp["engine_failure"],
                "signal_failure": inp["signal_failure"],
                "brake_failure": inp["brake_failure"],
                "emergency_brake": inp["emergency_brake"]
            },
            "outputs": {
                "velocity_mph": out["velocity_mph"],
                "acceleration_ftps2": out["acceleration_ftps2"],
                "position_yds": out["position_yds"],
                "authority_yds": out["authority_yds"],
                "station_name": out["station_name"],
                "next_station": out["next_station"],
                "left_door_open": out["left_door_open"],
                "right_door_open": out["right_door_open"],
                "temperature_F": out["temperature_F"],
                "door_side": inp["side_door"],
                "passengers_onboard": self.passengers_onboard,
                "passengers_boarding": self.boarding_last_cycle,
                "passengers_disembarking": passengers_out
            }
        }
        try:
            with open(TRAIN_DATA_FILE, "w") as f:
                json.dump(train_data, f, indent=4)
        except Exception as e:
            print("train_data write error:", e)
        track_out = {"passengers_disembarking": passengers_out}
        try:
            with open(TRACK_OUTPUT_FILE, "w") as f:
                json.dump(track_out, f, indent=4)
        except Exception as e:
            print("track output write error:", e)
        # controller state (minimal)
        try:
            state = {}
            if os.path.exists(TRAIN_STATES_FILE):
                with open(TRAIN_STATES_FILE, "r") as f:
                    state = json.load(f)
            state.update({
                "train_velocity": out["velocity_mph"],
                "train_temperature": out["temperature_F"],
                "next_stop": inp["next_station"],
                "station_side": inp["side_door"],
                "engine_failure": inp["engine_failure"],
                "signal_failure": inp["signal_failure"],
                "brake_failure": inp["brake_failure"],
                "emergency_brake": inp["emergency_brake"]
            })
            with open(TRAIN_STATES_FILE, "w") as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            print("train_states write error:", e)

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
    app = TrainModelTestUI()
    app.mainloop()
