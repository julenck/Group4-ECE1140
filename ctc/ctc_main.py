import json
from track.map import route_lookup

# read from ctc_ui_inputs.json 
data_file = 'ctc_ui_inputs.json'

with open(data_file, "r") as f:
    data = json.load(f)

train = data.get("Train")
line = data.get("Line")
station = data.get("Station")
arrival_time = data.get("Arrival Time")

# calculate suggested speed / authority 
# get final destination station -- dormont 
# figure out all stations that will be on the way -- glenbury, dormont (loop with id?)
# figure out distance to first station 
# figure out distance from first to second 

#find id of destination
id = route_lookup[station]["id"]
print(id)


# create new train 
# update ctc_data.json with new train 
