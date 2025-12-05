
#occ index 0-76
def process_states_green_xldown(occupied):


    switches = [0,0]
    signals = [0]*4*2
    crossing = [0]


    #set crossing 
    crossing[0] = 0 if 1 in occupied[33:42] else 1

    #light states

    #light 6 on sec m76
    if 1 not in occupied[7:76]:
        #set to supergreen
        signals[0] = 0
        signals[1] = 0
    elif 1 not in occupied[7:30]:
        #set to green
        signals[0] = 0
        signals[1] = 1
    elif 1 not in occupied[7:15]:
        #set to yellow
        signals[0] = 1
        signals[1] = 0
    else:
        #set to red
        signals[0] = 1
        signals[1] = 1


    #light 7 on sec o86
    if 1 not in occupied[16:76]:
        #set to supergreen
        signals[2] = 0
        signals[3] = 0
    elif 1 not in occupied[16:45]:
        #set to green
        signals[2] = 0
        signals[3] = 1
    elif 1 not in occupied[16:25]:
        #set to yellow
        signals[2] = 1
        signals[3] = 0

    else:
        #set to red
        signals[2] = 1
        signals[3] = 1

    
    #light 8 on sec q100
    if 1 not in occupied[0:15] and 1 not in occupied[31:76]:
        #set to supergreen
        signals[4] = 0
        signals[5] = 0
    elif 1 not in occupied[0:15] and 1 not in occupied[31:60]:
        #set to green
        signals[4] = 0
        signals[5] = 1
    elif 1 not in occupied[0:15]:
        #set to yellow
        signals[4] = 1
        signals[5] = 0
    else:
        #set to red
        signals[4] = 1
        signals[5] = 1

#light 9 on sec r101    

    if 1 not in occupied[31:76]:
        #set to supergreen
        signals[6] = 0
        signals[7] = 0
    elif 1 not in occupied[31:60]:
        #set to green
        signals[6] = 0
        signals[7] = 1
    elif 1 not in occupied[31:45]:
        #set to yellow
        signals[6] = 1
        signals[7] = 0
    else:
        #set to red
        signals[6] = 1
        signals[7] = 1

    #switches 4 and 5 elements 4 and 5 in switch array
    if 1 in occupied[7:15]:
        switches[0] = 1
        switches[1] = 0
    else:
        switches[0] = 0
        switches[1] = 1

    return signals, switches, crossing