import json, time, os
from datetime import datetime
from ctc_main_helper_functions import JSONFileWatcher
from watchdog.observers import Observer
from track.map import route_lookup_via_station, route_lookup_via_id

# define file variables
data_file_ctc_data = 'ctc_data.json'
data_file_ui_inputs = 'ctc_ui_inputs.json'
data_file_track_cont = '../ctc_track_controller.json' 

# define dwell time variable
dwell_time_s = 10

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

        # train is at station -- update ctc_track_controller.json with speed = 0, authority = 0 
        authority_at_station = 0
        speed_at_station = 0
    
        with open(data_file_track_cont, "r") as f_updates: 
            updates = json.load(f_updates)

        #updates["Trains"][train]["Suggested Authority"] = authority_at_station 
        #updates["Trains"][train]["Suggested Speed"] = speed_at_station
       
        with open(data_file_track_cont,"w") as f_updates: 
            json.dump(updates, f_updates, indent=4)
        
        # train is at station -- update ctc_data.json
        current_station = test
        with open(data_file_ctc_data, "r") as f_data:
            data = json.load(f_data)

        data["Dispatcher"]["Trains"][train]["Current Station"] = current_station
        data["Dispatcher"]["Trains"][train]["Authority"] = authority_at_station
        data["Dispatcher"]["Trains"][train]["Suggested Speed"] = speed_at_station

        with open(data_file_ctc_data, "w") as f_data:
            json.dump(data, f_data, indent=4)

        print(f"Train arrived at {test}")

        # once train gets to station, wait for dwell time 
        time.sleep(dwell_time_s)

        # train is moving now, clear current station
        with open(data_file_ctc_data, "r") as f_data:
            data = json.load(f_data)

        data["Dispatcher"]["Trains"][train]["Current Station"] = "---"  

        with open(data_file_ctc_data, "w") as f_data:
            json.dump(data, f_data, indent=4)

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
