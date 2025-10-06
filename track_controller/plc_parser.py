


import json
# #test this with a sample plc file and block occupancies
# def main():
# 
#     plc_file_path = "test_plc.json"
#     block_occupancies = [3]  # Example occupied blocks
#     destination = 15  # Example destination block ID
# 
#     updated_states = parse_plc_data(plc_file_path, block_occupancies, destination)
#     print(updated_states)

def parse_plc_data(plc_file_path,block_occupancies,destination,sug_speed,sug_auth):

    """
    Update switch, light, and crossing states based on occupied blocks and destination.

    Parameters:
        occupied_blocks (list of int): List of currently occupied blocks.
        destination (int): Desired destination block ID.

    Returns:
        dict: Updated states for switches, lights, and crossings.
              Format:
              {
                  "switches": {block_id: "BASE" or "ALT"},
                  "lights": {block_id: "GREEN" or "RED"},
                  "crossings": {block_id: "OPEN" or "CLOSED"}
              }
    """

    with open(plc_file_path, 'r') as file:
        plc_data = json.load(file)

    updated_states = {
        "switches": {},
        "lights": {},
        "crossings": {},
        "commanded_speed": 0,
        "commanded_authority": 0
    }

    for section, infrastructure in plc_data["blue_line"].items():

        if "switch" in infrastructure:
            switch = infrastructure["switch"]
            switch_pos = "BASE"
            base = switch["state"]["base"]
            alt = switch["state"]["alt"]

        if destination in alt["destination"] or any(block in block_occupancies for block in base["occupied"]):
            switch_pos = "ALT"
        elif destination in base["destination"] or any(block in block_occupancies for block in alt["occupied"]):
            switch_pos = "BASE"
        elif any(block in block_occupancies for block in base["occupied"]):
            switch_pos = "BASE"
        else:# any(block in block_occupancies for block in alt["occupied"]):
            switch_pos = "ALT"

        updated_states["switches"][switch["block_id"]] = switch_pos
        
        if "light" in infrastructure:
            light = infrastructure["light"]
            if all(block not in block_occupancies for block in light["state"]["green_if_unoccupied"]):
                light_state = "GREEN"
            else:
                light_state = "RED"
            updated_states["lights"][light["block_id"]] = light_state

        if "railway_crossing" in infrastructure:
            crossing = infrastructure["railway_crossing"]
            if any(block in block_occupancies for block in crossing["state"]["closed_if_occupied"]):
                crossing_state = "CLOSED"
            else:
                crossing_state = "OPEN"
            updated_states["crossings"][crossing["block_id"]] = crossing_state

    updated_states["commanded_speed"] = sug_speed
    updated_states["commanded_authority"] = sug_auth

    return updated_states

