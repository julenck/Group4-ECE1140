


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

def parse_plc_data(plc_file_path,block_occupancies,destination,sug_speed,sug_auth,fail_sig):

    """
    Update switch, light, and crossing states based on occupied blocks and destination.

    Parameters:
        occupied_blocks (list of int): List of currently occupied blocks.
        destination (int): Desired destination block ID.

    Returns:
        dict: Updated states for switches, lights, and crossings.
              Format:
              {
                  "switches": {block_id: "STRAIGHT" or "DIVERGING"},
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
        "commanded_authority": 0,
        "failure_signal": 0
    }

    train_on_A = any(block in block_occupancies for block in plc_data["blue_line"]["A"]["block_nums"])
    train_on_B = any(block in block_occupancies for block in plc_data["blue_line"]["B"]["block_nums"])
    train_on_C = any(block in block_occupancies for block in plc_data["blue_line"]["C"]["block_nums"])

    for section, infrastructure in plc_data["blue_line"].items():
        if fail_sig ==0:
            if "switch" in infrastructure:
                switch = infrastructure["switch"]
                switch_pos = "STRAIGHT"
                straight = switch["state"]["straight"]
                diverging = switch["state"]["diverging"]

            if train_on_A and (destination in diverging["destination"] and destination not in straight["destination"]):
                switch_pos = "DIVERGING"
            elif train_on_A and (destination in straight["destination"] and destination not in diverging["destination"]):
                switch_pos = "STRAIGHT"
            elif train_on_B:
                switch_pos = "STRAIGHT"
            elif train_on_C:
                switch_pos = "DIVERGING"
            else:
                switch_pos = "STRAIGHT"
            
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

            if sug_speed <0:
                sug_speed = 0
            elif sug_speed >31:
                sug_speed = 31
            if sug_auth <0:
                sug_auth = 0
            elif sug_auth >500:
                sug_auth = 500
            updated_states["commanded_speed"] = sug_speed
            updated_states["commanded_authority"] = sug_auth
        else:
            if "switch" in infrastructure:
                switch = infrastructure["switch"]
                switch_pos = "STRAIGHT"
                updated_states["switches"][switch["block_id"]] = switch_pos
            if "light" in infrastructure:
                light = infrastructure["light"]
                light_state = "RED"
                updated_states["lights"][light["block_id"]] = light_state
            if "railway_crossing" in infrastructure:
                crossing = infrastructure["railway_crossing"]
                crossing_state = "CLOSED"
                updated_states["crossings"][crossing["block_id"]] = crossing_state
            updated_states["commanded_speed"] = 0
            updated_states["commanded_authority"] = 0
        updated_states["failure_signal"] = fail_sig

    return updated_states

