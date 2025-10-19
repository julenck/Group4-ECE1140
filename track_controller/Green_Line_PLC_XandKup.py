

#will be plc for Green line Sections A to L


def process_states_green_xkup(occupied):

    #block_authority = [0]*(75)#75 blocks, 0 - available, 1 - occupied
    switches = [0]*4 #4 switches, 0 - switch connects to lower numbered block of 2 branches, 1 - switch connects to higher numbered block of 2 branches
    signals = [0]*8*2 #8 lights, 4 states each 00 - supergreen, 01 - green, 10 - yellow, 11 - red
    crossing = [0]*1 #1 crossing 0 - closed, 1 - open


    #first set crossing state:
    if 1 in occupied[13:28]:
        crossing[0] = 0
    else:
        crossing[0] = 1

    #light states
    #light 0 (elements 0,1 in signal array) is light on section C
    if 1 not in occupied[0:11] and 1 not in occupied[28:74]:
        #set to supergreen
        signals[0] = 0
        signals[1] = 0
    elif 1 not in occupied[0:11] and 1 not in occupied[68:74]:
        #set to green
        signals[0] = 0
        signals[1] = 1
    elif 1 not in occupied[0:11] and 1 in occupied[68:74]:
        #set to yellow
        signals[0] = 1
        signals[1] = 0
    else:
        #set to red
        signals[0] = 1
        signals[1] = 1

    #light 1 (elements 2,3 in signal array) is light on section A
    if 1 not in occupied[12:74]:
        #set to supergreen
        signals[2] = 0
        signals[3] = 0
    elif 1 not in occupied[12:67]:
        #set to green
        signals[2] = 0
        signals[3] = 1
    elif 1 not in occupied[12:34]:
        #set to yellow
        signals[2] = 1
        signals[3] = 0
    else:
        #set to red
        signals[2] = 1
        signals[3] = 1
    
    #light 2 (elements 4,5 in signal array) is light on section G
    if 1 not in occupied[29:74]:
        #set to supergreen
        signals[4] = 0
        signals[5] = 0
    elif 1 not in occupied[29:67]:
        #set to green
        signals[4] = 0
        signals[5] = 1
    elif 1 not in occupied[29:45]:
        #set to yellow
        signals[4] = 1  
        signals[5] = 0
    else:
        #set to red
        signals[4] = 1
        signals[5] = 1

    #light 3 (elements 6,7 in signal array) is light on section Z
    if 1 not in occupied[0:68]:
        #set to supergreen
        signals[6] = 0
        signals[7] = 0
    elif 1 not in occupied[0:34]:
        #set to green
        signals[6] = 0
        signals[7] = 1
    elif 1 in occupied[0:12] and 1 not in occupied[13:34]:
        #set to yellow
        signals[6] = 1
        signals[7] = 0
    else:
        #set to red
        signals[6] = 1
        signals[7] = 1
    
    #light 4 (elements 8,9 in signal array) is light on section green to yard
    
    #this light always green
    signals[8] = 0
    signals[9] = 1

    #light 5 (elements 10,11 in signal array) is light on section J(beginning)
    if 1 not in occupied[57:67]:
        #set to green
        signals[10] = 0
        signals[11] = 1
    elif 1 not in occupied[57:60]:
        #set to yellow
        signals[10] = 1
        signals[11] = 0
    else:
        #set to red
        signals[10] = 1
        signals[11] = 1
    
    #light 6 (elements 12,13 in signal array) is light on section J(end)
    if 1 not in occupied[62:67]:
        #set to green
        signals[12] = 0
        signals[13] = 1
    elif 1 not in occupied[60:63]:
        #set to yellow
        signals[12] = 1
        signals[13] = 0
    else:
        #set to red
        signals[12] = 1
        signals[13] = 1
    
    #light 7 (elements 14,15 in signal array) is light on section yard to k
    if 1 not in occupied[0:74]:
        #set to supergreen
        signals[14] = 0
        signals[15] = 0
    elif 1 not in occupied[47:67]:
        #set to green
        signals[14] = 0
        signals[15] = 1
    elif 1 not in occupied[47:60]:
        #set to yellow
        signals[14] = 1
        signals[15] = 0
    else:
        #set to red
        signals[14] = 1
        signals[15] = 1




