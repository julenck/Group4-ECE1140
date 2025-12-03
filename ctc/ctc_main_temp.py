
import json, time, os
import sys
from datetime import datetime
from .ctc_main_helper_functions import JSONFileWatcher
from watchdog.observers import Observer
from .track.map import route_lookup_via_station, route_lookup_via_id

# Add parent directory to path for API client import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ctc.api.ctc_api_client import CTCAPIClient

def track_update_handler(new_data, train, data_file_ctc_data):
    try:
        train_pos = new_data["Trains"][train]["Train Position"]
        train_state = new_data["Trains"][train]["Train State"]
        print(f"train position {train_pos}")
        with open(data_file_ctc_data, "r") as f_data:
            data = json.load(f_data)
        data["Dispatcher"]["Trains"][train]["Position"] = train_pos
        data["Dispatcher"]["Trains"][train]["State"] = train_state
        with open(data_file_ctc_data, "w") as f_data:
            json.dump(data, f_data, indent=4)
    except Exception as e:
        print(f"Train position data missing: {e}")

def dispatch_train(train, line, station, arrival_time_str,
                   data_file_ctc_data='ctc_data.json',
                   data_file_track_cont='../ctc_track_controller.json',
                   dwell_time_s=10,
                   server_url=None):
    # Initialize API client (remote mode) or use file paths (local mode)
    api_client = CTCAPIClient(server_url=server_url)
    is_remote = (server_url is not None)
    
    print(f"[CTC Dispatch] Mode: {'Remote' if is_remote else 'Local'}")
    if is_remote:
        print(f"[CTC Dispatch] Server: {server_url}")
        # Check server connection
        if not api_client.health_check():
            print(f"ERROR: Cannot connect to server at {server_url}")
            return
    else:
        # Resolve file paths relative to the ctc package base directory when not absolute
        BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if not os.path.isabs(data_file_ctc_data):
            data_file_ctc_data = os.path.join(BASE_DIR, os.path.basename(data_file_ctc_data))
        if not os.path.isabs(data_file_track_cont):
            data_file_track_cont = os.path.join(BASE_DIR, os.path.basename(data_file_track_cont))
        
        data_file_ctc_data = os.path.abspath(data_file_ctc_data)
        data_file_track_cont = os.path.abspath(data_file_track_cont)
        print(f"CTC data file -> {data_file_ctc_data}")
        print(f"Track controller file -> {data_file_track_cont}")

    # Ensure data structures exist (API or files)
    def _ensure_train_entries():
        trains = [f"Train {i}" for i in range(1, 6)]
        
        if is_remote:
            # Ensure entries via API
            ctc_data = api_client.get_state()
            if not ctc_data:
                ctc_data = {"Dispatcher": {"Trains": {}}}
            
            dispatcher_trains = ctc_data.setdefault("Dispatcher", {}).setdefault("Trains", {})
            for t in trains:
                dispatcher_trains.setdefault(t, {
                    "Line": "",
                    "Suggested Speed": "",
                    "Authority": "",
                    "Station Destination": "",
                    "Arrival Time": "",
                    "Position": "",
                    "State": "",
                    "Current Station": ""
                })
            api_client.update_state(ctc_data)
            
            # Ensure track controller entries
            track_updates = api_client.get_track_controller_commands()
            if not track_updates:
                track_updates = {"Trains": {}}
            
            trains_dict = track_updates.setdefault("Trains", {})
            for t in trains:
                trains_dict.setdefault(t, {
                    "Active": 0,
                    "Suggested Authority": 0,
                    "Suggested Speed": 0,
                    "Train Position": None,
                    "Train State": ""
                })
            
            api_client.send_track_controller_command(train, 0, 0, active=0)  # Initialize
            
        else:
            # Local file mode
            if not os.path.exists(data_file_track_cont):
                try:
                    with open(data_file_track_cont, 'w') as f:
                        json.dump({"Trains": {}}, f, indent=4)
                except Exception:
                    pass

            if not os.path.exists(data_file_ctc_data):
                try:
                    with open(data_file_ctc_data, 'w') as f:
                        json.dump({"Dispatcher": {"Trains": {}}}, f, indent=4)
                except Exception:
                    pass
            
            # ctc_data: ensure Dispatcher->Trains has entries
            try:
                with open(data_file_ctc_data, 'r') as f:
                    ctc_data = json.load(f)
            except Exception:
                ctc_data = {"Dispatcher": {"Trains": {}}}

            dispatcher_trains = ctc_data.setdefault("Dispatcher", {}).setdefault("Trains", {})
            for t in trains:
                dispatcher_trains.setdefault(t, {
                    "Line": "",
                    "Suggested Speed": "",
                    "Authority": "",
                    "Station Destination": "",
                    "Arrival Time": "",
                    "Position": "",
                    "State": "",
                    "Current Station": ""
                })

            try:
                with open(data_file_ctc_data, 'w') as f:
                    json.dump(ctc_data, f, indent=4)
            except Exception:
                pass

            # track controller file: ensure Trains has entries
            try:
                with open(data_file_track_cont, 'r') as f:
                    track_updates = json.load(f)
            except Exception:
                track_updates = {"Trains": {}}

            trains_dict = track_updates.setdefault("Trains", {})
            for t in trains:
                trains_dict.setdefault(t, {
                    "Active": 0,
                    "Suggested Authority": 0,
                    "Suggested Speed": 0,
                    "Train Position": None,
                    "Train State": ""
                })

            try:
                with open(data_file_track_cont, 'w') as f:
                    json.dump(track_updates, f, indent=4)
            except Exception:
                pass

    _ensure_train_entries()

    dest_id = route_lookup_via_station[station]["id"]
    print(f"dest id ={dest_id}")
    total_dist = 0
    for i in range(dest_id+1):
        total_dist += route_lookup_via_id[i]["meters_to_next"]
    print(f"dist to destination = {total_dist}")
    now = datetime.now()
    print(now)
    total_dwell_time_s = dwell_time_s * dest_id
    print(total_dwell_time_s)
    arrival_time = datetime.strptime(arrival_time_str, "%H:%M")
    arrival_time = arrival_time.replace(year=now.year, month=now.month, day=now.day)
    print(arrival_time)
    total_time = arrival_time - now
    total_time_s = total_time.total_seconds()
    print(total_time_s)
    time_to_drive_s = total_time_s - total_dwell_time_s
    print(time_to_drive_s)
    speed_meters_s = int(total_dist / time_to_drive_s)
    speed_mph = int(speed_meters_s * 2.237)
    print(f"speed in m/s = {speed_meters_s}")
    print(f"speed in mph = {speed_mph}")
    train_pos = None
    train_state = None

    def _track_update_handler(new_data):
        nonlocal train_pos, train_state
        try:
            train_pos = new_data["Trains"][train]["Train Position"]
            train_state = new_data["Trains"][train]["Train State"]
            print(f"train position {train_pos}")
            
            # Update CTC data via API or file
            if is_remote:
                api_client.update_train(train, {
                    "Position": train_pos,
                    "State": train_state
                })
            else:
                with open(data_file_ctc_data, "r") as f_data:
                    data = json.load(f_data)
                data["Dispatcher"]["Trains"][train]["Position"] = train_pos
                data["Dispatcher"]["Trains"][train]["State"] = train_state
                with open(data_file_ctc_data, "w") as f_data:
                    json.dump(data, f_data, indent=4)
        except Exception as e:
            print(f"Train position data missing: {e}")

    # File watcher only for local mode; polling for remote mode
    if not is_remote:
        watcher = JSONFileWatcher(data_file_track_cont, _track_update_handler)
        observer = Observer()
        observer.schedule(watcher, os.path.dirname(data_file_track_cont), recursive=False)
        observer.start()
    else:
        observer = None  # No file watcher needed in remote mode

    try:
        for i in range(dest_id + 1):
            test = route_lookup_via_id[i]["name"]
            print(f"next station ={test}")
            authority_meters = route_lookup_via_id[i]["meters_to_next"]
            authority_yards = int(authority_meters * 1.094)
            print(f"authority in meters = {authority_meters}")
            next_station_loc = route_lookup_via_id[i]["block"]
            print(f"next station loc = {next_station_loc}")
            # Update CTC data via API or file
            if is_remote:
                api_client.update_train(train, {
                    "Line": line,
                    "Authority": authority_yards,
                    "Suggested Speed": speed_mph,
                    "Station Destination": station,
                    "Arrival Time": arrival_time_str
                })
                api_client.send_track_controller_command(train, speed_meters_s, authority_meters, active=1)
            else:
                with open(data_file_ctc_data, "r") as f_data:
                    data = json.load(f_data)
                data["Dispatcher"]["Trains"][train]["Line"] = line
                data["Dispatcher"]["Trains"][train]["Authority"] = authority_yards
                data["Dispatcher"]["Trains"][train]["Suggested Speed"] = speed_mph
                data["Dispatcher"]["Trains"][train]["Station Destination"] = station
                data["Dispatcher"]["Trains"][train]["Arrival Time"] = arrival_time_str
                with open(data_file_ctc_data, "w") as f_data:
                    json.dump(data, f_data, indent=4)
                with open(data_file_track_cont, "r") as f_updates:
                    updates = json.load(f_updates)
                updates["Trains"][train]["Active"] = 1
                updates["Trains"][train]["Suggested Authority"] = authority_meters
                updates["Trains"][train]["Suggested Speed"] = speed_meters_s
                with open(data_file_track_cont, "w") as f_updates:
                    json.dump(updates, f_updates, indent=4)
            while(train_pos != next_station_loc):
                time.sleep(0.5)
                # In remote mode, poll for train position updates
                if is_remote:
                    track_data = api_client.get_track_controller_commands()
                    try:
                        train_pos = track_data["Trains"][train]["Train Position"]
                        train_state = track_data["Trains"][train]["Train State"]
                        # Update CTC with position
                        api_client.update_train(train, {
                            "Position": train_pos,
                            "State": train_state
                        })
                    except:
                        pass
                # Waiting for train to reach station (removed debug print)
            current_station = test
            # Update current station via API or file
            if is_remote:
                api_client.update_train(train, {
                    "Current Station": current_station,
                    "Authority": authority_yards,
                    "Suggested Speed": speed_mph
                })
            else:
                with open(data_file_ctc_data, "r") as f_data:
                    data = json.load(f_data)
                data["Dispatcher"]["Trains"][train]["Current Station"] = current_station
                data["Dispatcher"]["Trains"][train]["Authority"] = authority_yards
                data["Dispatcher"]["Trains"][train]["Suggested Speed"] = speed_mph
                with open(data_file_ctc_data, "w") as f_data:
                    json.dump(data, f_data, indent=4)
            print(f"Train arrived at {test}")
            time.sleep(dwell_time_s)
            time.sleep(0.5)
            # Clear current station via API or file
            if is_remote:
                api_client.update_train(train, {"Current Station": "---"})
                if test != station:
                    api_client.send_track_controller_command(train, speed_meters_s, authority_meters, active=1)
            else:
                with open(data_file_ctc_data, "r") as f_data:
                    data = json.load(f_data)
                data["Dispatcher"]["Trains"][train]["Current Station"] = "---"
                with open(data_file_ctc_data, "w") as f_data:
                    json.dump(data, f_data, indent=4)
                if test != station:
                    with open(data_file_track_cont, "r") as f_updates:
                        updates = json.load(f_updates)
                    updates["Trains"][train]["Active"] = 1
                    with open(data_file_track_cont, "w") as f_updates:
                        json.dump(updates, f_updates, indent=4)
            if test == station:
                print("train at destination")
                break
    except KeyboardInterrupt:
        print("stopping observer")
    finally:
        if observer:
            observer.stop()
            observer.join()

if __name__ == "__main__":
    # Example usage: read from ctc_ui_inputs.json and dispatch
    data_file_ui_inputs = 'ctc_ui_inputs.json'
    with open(data_file_ui_inputs, "r") as f_inputs:
        inputs = json.load(f_inputs)
    dispatch_train(
        train=inputs.get("Train"),
        line=inputs.get("Line"),
        station=inputs.get("Station"),
        arrival_time_str=inputs.get("Arrival Time")
    )

