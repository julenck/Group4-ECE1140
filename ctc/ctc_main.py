import json, time, os
from datetime import datetime
from ctc_main_helper_functions import JSONFileWatcher
from watchdog.observers import Observer
from track.map import route_lookup_via_station, route_lookup_via_id

# define file variables (use absolute paths relative to this module to avoid cwd issues)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
data_file_ctc_data = os.path.join(BASE_DIR, 'ctc_data.json')
data_file_ui_inputs = os.path.join(os.path.dirname(__file__), 'ctc_ui_inputs.json')
data_file_track_cont = os.path.join(BASE_DIR, 'ctc_track_controller.json')

# define dwell time variable
dwell_time_s = 10

# ALWAYS reset both JSON files to default at start of dispatch
# This ensures clean state for each new dispatch operation
print("Resetting CTC JSON files to default state...")

# Reset ctc_data.json
default_ctc_data = {
    "Dispatcher": {
        "Trains": {}
    }
}
for i in range(1, 6):
    tname = f"Train {i}"
    default_ctc_data["Dispatcher"]["Trains"][tname] = {
        "Line": "",
        "Suggested Speed": "",
        "Authority": "",
        "Station Destination": "",
        "Arrival Time": "",
        "Position": "",
        "State": "",
        "Current Station": ""
    }
try:
    with open(data_file_ctc_data, 'w') as f:
        json.dump(default_ctc_data, f, indent=4)
    print("ctc_data.json reset complete")
except Exception as e:
    print(f"Warning: failed to reset ctc_data.json: {e}")

# Reset ctc_track_controller.json
default_track = {"Trains": {}}
for i in range(1, 6):
    tname = f"Train {i}"
    default_track["Trains"][tname] = {
        "Active": 0,
        "Suggested Speed": 0,
        "Suggested Authority": 0,
        "Train Position": 0,
        "Train State": 0
    }
try:
    with open(data_file_track_cont, 'w') as f:
        json.dump(default_track, f, indent=4)
    print("ctc_track_controller.json reset complete")
except Exception as e:
    print(f"Warning: failed to reset ctc_track_controller.json: {e}")

# read from ctc_ui_inputs.json 
with open(data_file_ui_inputs, "r") as f_inputs:
    inputs = json.load(f_inputs)

train = inputs.get("Train")
line = inputs.get("Line")
station = inputs.get("Station")
arrival_time_str = inputs.get("Arrival Time")

#find id of destination
dest_id = route_lookup_via_station[station]["id"]
print(f"dest id ={dest_id}") 

# find total distance to destination 
total_dist = 0
for i in range(dest_id+1): 
    total_dist = total_dist + route_lookup_via_id[i]["meters_to_next"]
print(f"dist to destination = {total_dist}")

# get suggested speed 
now = datetime.now()
print(now)
total_dwell_time_s = dwell_time_s * dest_id
print(total_dwell_time_s)

# convert arrival time to datetime 
arrival_time = datetime.strptime(arrival_time_str, "%H:%M")
arrival_time = arrival_time.replace(year=now.year, month=now.month, day = now.day)
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

# monitor ctc_track_controller.json for train position updates
train_pos = None
train_state = None

def track_update_handler(new_data): 
    global train_pos
    global train_state
    try: 
        # get data from ctc_track_controller.json
        train_pos = new_data["Trains"][train]["Train Position"]
        train_state = new_data["Trains"][train]["Train State"]

        print(f"train position{train_pos}")

        # update ctc_data.json
        with open(data_file_ctc_data, "r") as f_data: 
            data = json.load(f_data)
        
        data["Dispatcher"]["Trains"][train]["Position"] = train_pos
        data["Dispatcher"]["Trains"][train]["State"] = train_state

        with open(data_file_ctc_data,"w") as f_data: 
            json.dump(data,f_data, indent=4)
    except: 
        print("Train position data missing")

watcher = JSONFileWatcher(data_file_track_cont, track_update_handler)
observer = Observer()
observer.schedule(watcher,os.path.dirname(data_file_track_cont),recursive=False)
observer.start()

# find all the stations we will need to stop at on the way 
try: 
    for i in range(dest_id + 1): 

        # get next station 
        test = route_lookup_via_id[i]["name"]
        print(f"next station ={test}")

        # get distance to next station 
        authority_meters = route_lookup_via_id[i]["meters_to_next"]
        authority_yards = int(authority_meters * 1.094)
        print(f"authority in meters = {authority_meters}")

        # get location of next station 
        next_station_loc = route_lookup_via_id[i]["block"]
        print(f"next station loc = {next_station_loc}")

        # open ctc_data.json -- updates the UI 
        with open(data_file_ctc_data, "r") as f_data: 
            data = json.load(f_data)

        data["Dispatcher"]["Trains"][train]["Line"] = line
        data["Dispatcher"]["Trains"][train]["Authority"] = authority_yards
        data["Dispatcher"]["Trains"][train]["Suggested Speed"] = speed_mph
        data["Dispatcher"]["Trains"][train]["Station Destination"] = station
        data["Dispatcher"]["Trains"][train]["Arrival Time"] = arrival_time_str

        with open(data_file_ctc_data, "w") as f_data:
            json.dump(data, f_data, indent=4)
    
        # update ctc_track_controller.json with active=1, speed, authority 
        with open(data_file_track_cont, "r") as f_updates: 
            updates = json.load(f_updates)
        
        updates["Trains"][train]["Active"] = 1
        updates["Trains"][train]["Suggested Authority"] = authority_meters
        updates["Trains"][train]["Suggested Speed"] = speed_meters_s

        with open(data_file_track_cont,"w") as f_updates: 
            json.dump(updates, f_updates, indent=4)

        # seeing when train gets to station 
        while(train_pos != next_station_loc):
            time.sleep(0.5)
            print("here")
        
        # train is at station -- update ctc_data.json
        current_station = test
        with open(data_file_ctc_data, "r") as f_data:
            data = json.load(f_data)

        data["Dispatcher"]["Trains"][train]["Current Station"] = current_station
        data["Dispatcher"]["Trains"][train]["Authority"] = authority_yards
        data["Dispatcher"]["Trains"][train]["Suggested Speed"] = speed_mph

        with open(data_file_ctc_data, "w") as f_data:
            json.dump(data, f_data, indent=4)

        print(f"Train arrived at {test}")
        
        # Set Active = 0 so train stops at station
        with open(data_file_track_cont, "r") as f_updates: 
            updates = json.load(f_updates)
        updates["Trains"][train]["Active"] = 0
        with open(data_file_track_cont, "w") as f_updates: 
            json.dump(updates, f_updates, indent=4)

        # Wait for dwell time
        time.sleep(dwell_time_s)

        # Wait for wayside to finish writes 
        time.sleep(0.5)

        # Clear current station after dwell
        with open(data_file_ctc_data, "r") as f_data:
            data = json.load(f_data)
        data["Dispatcher"]["Trains"][train]["Current Station"] = "---"  
        with open(data_file_ctc_data, "w") as f_data:
            json.dump(data, f_data, indent=4)

        # If not at final destination, set Active = 1 with new authority for next leg
        if test != station: 
            with open(data_file_track_cont, "r") as f_updates: 
                updates = json.load(f_updates) 
            updates["Trains"][train]["Active"] = 1
            with open(data_file_track_cont, "w") as f_updates: 
                json.dump(updates, f_updates, indent=4)
        
        # iterate to go to next station
        #i = i+1

        if test == station: 
            print("train at destination")
            break 

except KeyboardInterrupt:
    print("stopping observer")

finally: 
    observer.stop()
    observer.join()  
