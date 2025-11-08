import json, time, os
from ctc_main_helper_functions import JSONFileWatcher
from watchdog.observers import Observer
from track.map import route_lookup_via_station, route_lookup_via_id

# read from ctc_ui_inputs.json 
data_file_ui_inputs = 'ctc_ui_inputs.json'
with open(data_file_ui_inputs, "r") as f_inputs:
    inputs = json.load(f_inputs)

train = inputs.get("Train")
line = inputs.get("Line")
station = inputs.get("Station")
arrival_time = inputs.get("Arrival Time")

#find id of destination
dest_id = route_lookup_via_station[station]["id"]
print(f"dest id ={dest_id}") 

# monitor ctc_track_controller.json for train position updates
data_file_track_cont = '../ctc_track_controller.json' 
train_pos = None

def track_update_handler(new_data): 
    global train_pos
    try: 
        train_pos = new_data["Trains"][train]["Train Position"]
        print(f"train position{train_pos}")
    except: 
        print("Train position data missing")
watcher = JSONFileWatcher(data_file_track_cont, track_update_handler)
observer = Observer()
observer.schedule(watcher,os.path.dirname(data_file_track_cont),recursive=False)
observer.start()

# find all the stations we will need to stop at on the way 
try: 
    for i in range(dest_id): 
        # get next station 
        test = route_lookup_via_id[i]["name"]
        print(f"next station ={test}")

        # get distance to next station 
        authority = route_lookup_via_id[i]["meters_to_next"]
        print(f"authority = {authority}")

        # get location of next station 
        next_station_loc = route_lookup_via_id[i]["block"]
        print(f"next station loc = {next_station_loc}")

        # update ctc_data.json -- updates the UI 
        data_file_ctc_data = 'ctc_data.json'
        with open(data_file_ctc_data, "r") as f_data: 
            data = json.load(f_data)

        data["Dispatcher"]["Trains"][train]["Line"] = line
        data["Dispatcher"]["Trains"][train]["Authority"] = authority  
        data["Dispatcher"]["Trains"][train]["Suggested Speed"] = 0
        data["Dispatcher"]["Trains"][train]["Station Destination"] = station
        data["Dispatcher"]["Trains"][train]["Arrival Time"] = 0

        with open(data_file_ctc_data, "w") as f_data:
            json.dump(data, f_data, indent=4)
    
        # update ctc_track_controller.json with active=1,speed, authority 
        with open(data_file_track_cont, "r") as f_updates: 
            updates = json.load(f_updates)
        
        updates["Trains"][train]["Active"] = 1
        updates["Trains"][train]["Suggested Authority"] = authority

        with open(data_file_track_cont,"w") as f_updates: 
            json.dump(updates, f_updates, indent=4)

        # seeing when train gets to station 
        while(train_pos != next_station_loc):
            time.sleep(0.5)
            print("here")

        print(f"Train arrived at {test}")

        # once train gets to station, wait for dwell time 
        dwell_time_seconds = 10
        time.sleep(dwell_time_seconds)

        # iterate to go to next station
        i = i+1

except KeyboardInterrupt:
    print("stopping observer")

finally: 
    observer.stop()
    observer.join() 
