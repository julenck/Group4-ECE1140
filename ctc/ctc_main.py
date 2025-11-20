import json, time, os, sys, threading
from datetime import datetime
from ctc_main_helper_functions import JSONFileWatcher
from watchdog.observers import Observer
from track.map import route_lookup_via_station, route_lookup_via_id

# Import time controller for synchronized timing
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from time_controller import get_time_controller

# define file variables
data_file_ctc_data = os.path.join(os.path.dirname(__file__), 'ctc_data.json')
data_file_ui_inputs = os.path.join(os.path.dirname(__file__), 'ctc_ui_inputs.json')
data_file_track_cont = os.path.join(os.path.dirname(__file__), '..', 'ctc_track_controller.json')
data_file_track_static = os.path.join(os.path.dirname(__file__), '..', 'Track_Model', 'track_model_static.json')

# File lock to prevent concurrent writes to ctc_data.json
ctc_data_lock = threading.Lock()

def safe_update_ctc_data(update_function):
    """Safely update ctc_data.json with file locking to prevent overwrites."""
    with ctc_data_lock:
        try:
            with open(data_file_ctc_data, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"Dispatcher": {"Trains": {}}}
        
        # Call the update function to modify the data
        update_function(data)
        
        with open(data_file_ctc_data, "w") as f:
            json.dump(data, f, indent=4)

def get_min_speed_limit_for_route(line, block_numbers):
    """Get the minimum speed limit for a route based on block numbers."""
    try:
        with open(data_file_track_static, 'r') as f:
            track_data = json.load(f)
        
        line_data = track_data.get('static_data', {}).get(line, [])
        
        min_speed_kmh = float('inf')
        for block_num in block_numbers:
            for block in line_data:
                if block.get('Block Number') == block_num:
                    speed_limit_kmh = block.get('Speed Limit (Km/Hr)', 40.0)
                    min_speed_kmh = min(min_speed_kmh, speed_limit_kmh)
                    break
        
        # Convert km/h to mph (1 km/h = 0.621371 mph)
        if min_speed_kmh == float('inf'):
            return 70  # Default if no speed limits found
        
        min_speed_mph = min_speed_kmh * 0.621371
        return int(min_speed_mph)
    except Exception as e:
        print(f"[CTC] Error reading speed limits: {e}")
        return 70  # Default fallback 

# define dwell time variable
dwell_time_s = 10

# read from ctc_ui_inputs.json 
try:
    with open(data_file_ui_inputs, "r") as f_inputs:
        inputs = json.load(f_inputs)
except (FileNotFoundError, json.JSONDecodeError):
    # If file doesn't exist or is empty, use defaults
    inputs = {}

train = inputs.get("Train")
line = inputs.get("Line")
station = inputs.get("Station")
arrival_time_str = inputs.get("Arrival Time")

# Validate inputs before proceeding
if not all([train, line, station, arrival_time_str]):
    print(f"[CTC Main] Error: Missing required inputs - Train: {train}, Line: {line}, Station: {station}, Arrival: {arrival_time_str}")
    exit(1)

#find id of destination
try:
    dest_id = route_lookup_via_station[station]["id"]
    print(f"dest id ={dest_id}")
except KeyError:
    print(f"[CTC Main] Error: Station '{station}' not found in route lookup")
    exit(1) 

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
train_pos = 63 if line == "Green" else 1  # Initialize to yard exit position
train_state = "Moving"

def track_update_handler(new_data): 
    global train_pos
    global train_state
    try: 
        # get data from ctc_track_controller.json
        train_pos = new_data["Trains"][train]["Train Position"]
        train_state = new_data["Trains"][train]["Train State"]

        # print(f"[CTC] Train position updated to: {train_pos}")

        # update ctc_data.json using safe locking mechanism
        def update_pos_state(data):
            # Ensure the train exists in the data structure
            if "Dispatcher" not in data:
                data["Dispatcher"] = {"Trains": {}}
            if "Trains" not in data["Dispatcher"]:
                data["Dispatcher"]["Trains"] = {}
            if train not in data["Dispatcher"]["Trains"]:
                data["Dispatcher"]["Trains"][train] = {}
            
            data["Dispatcher"]["Trains"][train]["Position"] = train_pos
            data["Dispatcher"]["Trains"][train]["State"] = train_state
        
        safe_update_ctc_data(update_pos_state)
    except KeyError as e: 
        print(f"Train position data error - missing key: {e}")
    except Exception as e: 
        print(f"Train position data error: {e}")

watcher = JSONFileWatcher(data_file_track_cont, track_update_handler)
observer = Observer()
observer.schedule(watcher,os.path.dirname(data_file_track_cont),recursive=False)
observer.start()

# Set initial train position to yard (block 63 for Green, block 1 for Red)
initial_position = 63 if line == "Green" else 1  # Green trains exit yard at block 63

def set_initial_position(data):
    if "Dispatcher" not in data:
        data["Dispatcher"] = {"Trains": {}}
    if "Trains" not in data["Dispatcher"]:
        data["Dispatcher"]["Trains"] = {}
    if train not in data["Dispatcher"]["Trains"]:
        data["Dispatcher"]["Trains"][train] = {}
    
    data["Dispatcher"]["Trains"][train]["Position"] = initial_position
    data["Dispatcher"]["Trains"][train]["State"] = "Moving"
    data["Dispatcher"]["Trains"][train]["Line"] = line  # Add line info so track model knows which line

safe_update_ctc_data(set_initial_position)

# Also set initial position in ctc_track_controller.json for wayside
with open(data_file_track_cont, "r") as f_updates:
    updates = json.load(f_updates)

updates["Trains"][train]["Train Position"] = initial_position
updates["Trains"][train]["Train State"] = 0  # 0 = Moving

with open(data_file_track_cont, "w") as f_updates:
    json.dump(updates, f_updates, indent=4)

print(f"[CTC] Train {train} starting from yard at block {initial_position}")

# find all the stations we will need to stop at on the way 
try: 
    # Get all blocks along the route for speed limit calculation
    route_blocks = [route_lookup_via_id[i]["block"] for i in range(dest_id + 1)]
    max_speed_mph = get_min_speed_limit_for_route(line, route_blocks)
    print(f"[CTC] Maximum allowed speed for route: {max_speed_mph} mph (based on track speed limits)")
    
    for i in range(dest_id + 1): 

        # get next station 
        test = route_lookup_via_id[i]["name"]
        print(f"next station ={test}")

        # Recalculate speed based on remaining distance and time
        remaining_dist = 0
        for j in range(i, dest_id + 1):
            remaining_dist += route_lookup_via_id[j]["meters_to_next"]
        
        remaining_stations = dest_id - i
        remaining_dwell_time_s = dwell_time_s * remaining_stations
        
        current_time = datetime.now()
        remaining_time_s = (arrival_time - current_time).total_seconds()
        time_to_drive_remaining_s = remaining_time_s - remaining_dwell_time_s
        
        if time_to_drive_remaining_s > 0:
            speed_meters_s = int(remaining_dist / time_to_drive_remaining_s)
            speed_mph = int(speed_meters_s * 2.237)
        else:
            # Use original speed if time calculation fails
            speed_meters_s = int(total_dist / time_to_drive_s)
            speed_mph = int(speed_meters_s * 2.237)
        
        # Cap speed at track's maximum allowed speed
        if speed_mph > max_speed_mph:
            print(f"[CTC] Calculated speed {speed_mph} mph exceeds track limit. Capping at {max_speed_mph} mph")
            speed_mph = max_speed_mph
            speed_meters_s = int(speed_mph / 2.237)
        
        print(f"Updated speed in m/s = {speed_meters_s}")
        print(f"Updated speed in mph = {speed_mph}")

        # get distance to next station 
        authority_meters = route_lookup_via_id[i]["meters_to_next"]
        authority_yards = int(authority_meters * 1.094)
        print(f"authority in meters = {authority_meters}")

        # get location of next station 
        next_station_loc = route_lookup_via_id[i]["block"]
        print(f"next station loc = {next_station_loc}")

        # open ctc_data.json -- updates the UI
        def update_route_info(data):
            data["Dispatcher"]["Trains"][train]["Line"] = line
            data["Dispatcher"]["Trains"][train]["Authority"] = authority_yards
            data["Dispatcher"]["Trains"][train]["Suggested Speed"] = speed_mph
            data["Dispatcher"]["Trains"][train]["Station Destination"] = station
            data["Dispatcher"]["Trains"][train]["Arrival Time"] = arrival_time_str
        
        safe_update_ctc_data(update_route_info)
    
        # update ctc_track_controller.json with active=1, speed, authority 
        with open(data_file_track_cont, "r") as f_updates: 
            updates = json.load(f_updates)
        
        updates["Trains"][train]["Active"] = 1
        updates["Trains"][train]["Suggested Authority"] = authority_meters
        updates["Trains"][train]["Suggested Speed"] = speed_meters_s

        with open(data_file_track_cont,"w") as f_updates: 
            json.dump(updates, f_updates, indent=4)

        # seeing when train gets to station
        print(f"[CTC] Waiting for train to reach block {next_station_loc} (currently at block {train_pos})...")
        time_controller = get_time_controller()
        last_printed_pos = train_pos
        while(train_pos != next_station_loc):
            actual_sleep = 0.5 / time_controller.speed_multiplier
            time.sleep(actual_sleep)
            # Print when position changes
            if train_pos != last_printed_pos:
                print(f"[CTC Loop] Train now at block {train_pos}, waiting for {next_station_loc}")
                last_printed_pos = train_pos
        
        print(f"[CTC] Train arrived at {test} (block {next_station_loc})")
        
        # train is at station -- update ctc_data.json
        current_station = test
        
        def update_at_station(data):
            data["Dispatcher"]["Trains"][train]["Current Station"] = current_station
            data["Dispatcher"]["Trains"][train]["Authority"] = authority_yards
            data["Dispatcher"]["Trains"][train]["Suggested Speed"] = speed_mph
        
        safe_update_ctc_data(update_at_station)

        print(f"Train arrived at {test}")

        # once train gets to station, wait for dwell time (scaled by speed multiplier)
        time_controller = get_time_controller()
        actual_dwell = dwell_time_s / time_controller.speed_multiplier
        time.sleep(actual_dwell)

        # wait for wayside to finish writes (scaled by speed multiplier)
        actual_wait = 0.5 / time_controller.speed_multiplier
        time.sleep(actual_wait)

        # train is moving now, clear current station
        def clear_station(data):
            if "Dispatcher" not in data:
                data["Dispatcher"] = {"Trains": {}}
            if "Trains" not in data["Dispatcher"]:
                data["Dispatcher"]["Trains"] = {}
            if train not in data["Dispatcher"]["Trains"]:
                data["Dispatcher"]["Trains"][train] = {}
            data["Dispatcher"]["Trains"][train]["Current Station"] = "---"
        
        safe_update_ctc_data(clear_station)

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
