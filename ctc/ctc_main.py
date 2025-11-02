import json
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
print(dest_id) 

# find all the stations we will need to stop at on the way 
for i in range(dest_id): 
    # get next station 
    test = route_lookup_via_id[i]["name"]

    # get distance to next station 
    authority = route_lookup_via_id[i]["meters_to_next"]

    # get location of next station 
    next_station_loc = route_lookup_via_id[i]["block"]

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

    # get train position from ctc_track_controller.json 
    data_file_track_cont = 'ctc_track_controller.json'
    with open(data_file_track_cont,"r") as f_track: 
        track = json.load(f_track)
    train_pos = track.get(["Trains"][train]["Train Position"])

    # wait until train gets to station (train position == station block) and then iterate i 

    while(train_pos != next_station_loc):
        #keep getting train position 
        
        if(train_pos == next_station_loc){
            # wait for dwell time 
            i = i+1; 
            break; 
        }