

def process_states_green_xldown(occupied):


    switches = [0,0]
    signals = [0]*4*2
    crossing = [0]


    #set crossing 
    crossing[0] = 0 if 1 in occupied