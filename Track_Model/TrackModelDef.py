# Track Object - A entire track network

import numpy as np

class Track:
    def __init__(self):
        self.lines: list[Line] = []

        # ----- Initializing with preload data -----
        # Create red line
        self.red_line = Line()
        self.red_line.lineColor = 0

        # Red line block information
        red_line_default_blocks = [2,3,4,5,6,8,11,12,13,14,18,19,20,22,23,24,26,29,30,31,34,36,37,40,41,42,46,49,50,54,55,56,57,58,59,61,62,63,64,65,68,69,70,73,74,75]
        self.red_line_station_blocks = [7,17,21,25,35,45,48,60]
        self.red_line_station_names = ["Shadyside", "Herron Ave", "Swissville", "Penn Station", "Steel Plaza", "First Ave", "Station Square", "South Hills Junction"]
        red_line_crossing_blocks = [47]
        red_line_junction_blocks = [9,0,10,16,1,15,27,28,76,33,72,32,38,39,71,44,67,43,52,53,66]
        self.red_line_device_blocks_ws1 = [9,16]
        self.red_line_device_blocks_ws2 = [27,33,38,44,47,52]
        self.red_line_sections = [[0],[1,2,3,4,5,6,7,8,9],[15,14,13,12,11,10],[27,26,25,24,23,22,21,20,19,18,17,16],[32,31,30,29,28],[38,37,36,35,34,33],[43,42,41,40,39],[52,51,50,49,48,47,46,45,44],[66,65,64,63,62,61,60,59,58,57,56,55,54,53],[67,68,69,70,71],[72,73,74,75,76]]
        self.red_line.path = np.array([0,9,8,7,6,5,4,3,2,1,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,52,51,50,49,48,47,46,45,44,67,68,69,70,71,38,37,36,35,34,33,72,73,74,75,76,27,26,25,24,23,22,21,20,19,18,17,16,1,2,3,4,5,6,7,8,9,0])
        self.red_line_speed_limit = [10, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 34, 43, 43, 43, 34, 34, 34, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 37, 37, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34]
        self.red_line.graph = {
            0:[9],
            1:[16,2],
            2:[1,3],
            3:[2,4],
            4:[3,5],
            5:[4,6],
            6:[5,7],
            7:[6,8],
            8:[7,9],
            9:[8,0,10],
            10:[9,11],
            11:[10,12],
            12:[11,13],
            13:[12,14],
            14:[13,15],
            15:[14,16],
            16:[1,15,17],
            17:[16,18],
            18:[17,19],
            19:[18,20],
            20:[19,21],
            21:[20,22],
            22:[21,23],
            23:[22,24],
            24:[23,25],
            25:[24,26],
            26:[25,27],
            27:[26,76,28],
            28:[27,29],
            29:[28,30],
            30:[29,31],
            31:[30,32],
            32:[31,33],
            33:[32,72,34],
            34:[33,35],
            35:[34,36],
            36:[35,37],
            37:[36,38],
            38:[37,71,39],
            39:[38,40],
            40:[39,41],
            41:[40,42],
            42:[41,43],
            43:[42,44],
            44:[43,67,45],
            45:[44,46],
            46:[45,47],
            47:[46,48],
            48:[47,49],
            49:[48,50],
            50:[49,51],
            51:[50,52],
            52:[51,53,66],
            53:[52,54],
            54:[53,55],
            55:[54,56],
            56:[55,57],
            57:[56,58],
            58:[57,59],
            59:[58,60],
            60:[59,61],
            61:[60,62],
            62:[61,63],
            63:[62,64],
            64:[63,65],
            65:[64,66],
            66:[65,52],
            67:[44,68],
            68:[67,69],
            69:[68,70],
            70:[69,71],
            71:[70,38],
            72:[33,72],
            73:[72,74],
            74:[73,75],
            75:[74,76],
            76:[75,27]
        }

        self.red_line_block_lengths = [0, 50, 50, 50, 50, 50, 50, 75, 75, 75, 75, 75, 75, 70, 60, 60, 50, 200, 400, 400, 200, 100, 100, 100, 50, 50, 50, 50, 50, 60, 60, 50, 50, 50, 50, 50, 50, 50, 50, 50, 60, 60, 50, 50, 50, 50, 75, 75, 75, 50, 50, 50, 43, 50, 75, 75, 75, 75, 75, 75, 75, 75, 75, 75, 75, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50]
        
        # Fill red Line
        for i in range(77):
            blk = Block()
            blk.block_number = i
            if(i in red_line_default_blocks):
                blk.block_type = 0
            elif(i in self.red_line_station_blocks):
                blk.block_type = 2
                blk.station_name = self.red_line_station_names[self.red_line_station_blocks.index(i)]
            elif(i in red_line_junction_blocks):
                blk.block_type = 1
                blk.switch_direction = 0
                blk.traffic_light_color = 0
            elif(i in red_line_crossing_blocks):
                blk.block_type = 3
            self.red_line.blocks.append(blk)
            
        # Create green line
        self.green_line = Line()
        self.green_line.line_color = 1
        
        # Green line block information
        green_line_default_blocks = [3,4,5,6,7,8,10,11,14,15,17,18,20,21,23,24,25,26,27,30,32,33,34,35,36,37,38,40,41,42,43,44,45,46,47,49,50,51,52,53,54,55,59,60,61,64,66,67,68,69,70,71,72,74,75,79,80,81,82,83,84,86,87,89,90,91,92,93,94,95,97,98,99,102,103,104,106,107,108,109,110,111,112,113,115,116,117,118,119,120,121,122,124,125,126,127,128,129,130,131,133,134,135,136,137,138,139,140,142,143,144,145,146,147,148,149]
        self.green_line_station_blocks = [2,9,16,22,31,39,48,56,65,73,78,88,96,105,114,123,132,141]
        self.green_line_station_names = ["Pioneer", "Edgebrook", "Jalappa", "Whited", "South Bank", "Central (1)", "Inglewood (1)", "Overbrook (1)", "Glenbury (1)", "Dormont (1)", "Mt Lebanon", "Poplar", "Castle Shannon", "Dormont (2)", "Glenbury (2)", "Overbrook (2)", "Inglewood (2)", "Central (2)"]
        self.green_line_station_names_ordered = ["Glenbury (1)", "Dormont (1)", "Mt Lebanon", "Poplar", "Castle Shannon", "Dormont (2)", "Glenbury (2)", "Overbrook (2)", "Inglewood (2)", "Central (2)", "Whited", "Jalappa", "Edgebrook", "Pioneer", "South Bank", "Central (1)", "Inglewood (1)", "Overbrook (1)"]
        green_line_crossing_blocks = [19]
        green_line_junction_blocks = [13,12,1,28,29,150,57,0,58,63,62,0,77,101,76,85,86,100]
        self.green_line_device_blocks_ws1 = [13,19,28,57,63]
        self.green_line_device_blocks_ws2 = [77,85]
        self.green_line_sections = [[12,11,10,9,8,7,6,5,4,3,2,1],[28,27,26,25,24,23,22,21,20,19,18,17,16,15,14,13],[57,56,55,54,53,52,51,50,49,48,47,46,45,44,43,42,41,40,39,38,37,36,35,34,33,32,31,30,29],[0],[62,61,60,59,58],[76,75,74,73,72,71,70,69,68,67,66,65,64,63],[85,84,83,82,81,80,79,78,77],[86,87,88,89,90,91,92,93,94,95,96,97,98,99,100],[101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150]]
        self.green_line.path = np.array([0,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,85,84,83,82,81,80,79,78,77,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,28,27,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,0])
        self.green_line_speed_limit = [10, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 43, 43, 43, 43, 37, 37, 37, 37, 43, 43, 43, 43, 43, 43, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 19, 43, 43, 43, 43, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 43, 43, 43, 43, 43, 43, 43, 43, 43, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 17, 17, 17, 17, 17, 17, 17, 17, 19, 19, 19, 19, 19, 19, 19, 9, 9, 9, 9, 9, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12]
        self.green_line.graph = {
            0:[63],
            1:[13],
            2:[1],
            3:[2],
            4:[3],
            5:[4],
            6:[5],
            7:[6],
            8:[7],
            9:[8],
            10:[9],
            11:[10],
            12:[11],
            13:[12],
            14:[13,15],
            15:[14,16],
            16:[15,17],
            17:[16,18],
            18:[17,19],
            19:[18,20],
            20:[19,21],
            21:[20,22],
            22:[21,23],
            23:[22,24],
            24:[23,25],
            25:[24,26],
            26:[25,27],
            27:[26,28],
            28:[29],
            29:[30],
            30:[31],
            31:[32],
            32:[33],
            33:[34],
            34:[35],
            35:[36],
            36:[37],
            37:[38],
            38:[39],
            39:[40],
            40:[41],
            41:[42],
            42:[43],
            43:[44],
            44:[45],
            45:[46],
            46:[47],
            47:[48],
            48:[49],
            49:[50],
            50:[51],
            51:[52],
            52:[53],
            53:[54],
            54:[55],
            55:[56],
            56:[57],
            57:[0,58],
            58:[59],
            59:[60],
            60:[61],
            61:[62],
            62:[63],
            63:[64],
            64:[65],
            65:[66],
            66:[67],
            67:[68],
            68:[69],
            69:[70],
            70:[71],
            71:[72],
            72:[73],
            73:[74],
            74:[75],
            75:[76],
            76:[77],
            77:[78,101],
            78:[77,79],
            79:[78,80],
            80:[79,81],
            81:[80,82],
            82:[81,83],
            83:[82,84],
            84:[83,85],
            85:[86],
            86:[87],
            87:[88],
            88:[89],
            89:[90],
            90:[91],
            91:[92],
            92:[93],
            93:[94],
            94:[95],
            95:[96],
            96:[97],
            97:[98],
            98:[99],
            99:[100],
            100:[85],
            101:[102],
            102:[103],
            103:[104],
            104:[105],
            105:[106],
            106:[107],
            107:[108],
            108:[109],
            109:[110],
            110:[111],
            111:[112],
            112:[113],
            113:[114],
            114:[115],
            115:[116],
            116:[117],
            117:[118],
            118:[119],
            119:[120],
            120:[121],
            121:[122],
            122:[123],
            123:[124],
            124:[125],
            125:[126],
            126:[127],
            127:[128],
            128:[129],
            129:[130],
            130:[131],
            131:[132],
            132:[133],
            133:[134],
            134:[135],
            135:[136],
            136:[137],
            137:[138],
            138:[139],
            139:[140],
            140:[141],
            141:[142],
            142:[143],
            143:[144],
            144:[145],
            145:[146],
            146:[147],
            147:[148],
            148:[149],
            149:[150],
            150:[28]
        }

        self.green_line_block_lengths = [0,100,100,100,100,100,100,100,100,100,100,100,100,150,150,150,150,150,150,150,150,300,300,300,300,200,100,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,100,100,200,200,100,100,100,100,100,100,100,100,100,100,300,300,300,300,300,300,300,300,300,100,90,100,75,75,75,75,75,75,75,75,75,75,75,75,35,100,100,80,100
,100,90,100,100,100,100,100,100,162,100,100,50,50,40,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,184,40,35]
        # Fill green line
        for i in range(151):
            blk = Block()
            blk.block_number = i
            # Set block types and specific information
            if(i in green_line_default_blocks):
                blk.block_type = 0
            elif(i in self.green_line_station_blocks):
                blk.block_type = 2
                blk.station_name = self.green_line_station_names[self.green_line_station_blocks.index(i)]
            elif(i in green_line_junction_blocks):
                blk.block_type = 1
                blk.switch_direction = 0
                blk.traffic_light_color = 0
            elif(i in green_line_crossing_blocks):
                blk.block_type = 3
            self.green_line.blocks.append(blk)

        # Store lines in track
        self.lines.insert(0, self.red_line)
        self.lines.insert(1, self.green_line)

    #Function to swap between station names and block number
    def red_line_station_to_block (self, swap_stations):
        #loop through stations to get swapped
        for i in range(len(swap_stations)):
            for j in range(len(self.red_line_station_names)):
                if swap_stations[i] == self.red_line_station_names[j]:
                    swap_stations[i] = self.red_line_station_blocks[j]
        
        #return the block numbers
        return swap_stations

    def red_line_block_to_station (self, swap_blocks):
        #check if the variable is just 'int'
        if type(swap_blocks) is int:
            for j in range(len(self.red_line_station_blocks)):
                if swap_blocks == self.red_line_station_blocks[j]:
                    return self.red_line_station_names[j]

        #otherwise loop through blocks to get swapped
        ##TODO - Allow stops to be duplicated in the loop around
        for i in range(len(swap_blocks)):
            for j in range(len(self.red_line_station_blocks)):
                if swap_blocks[i] == self.red_line_station_blocks[j]:
                    swap_blocks[i] = self.red_line_station_names[j]

        #return the station names
        return swap_blocks

    #Function to swap between station names and block number
    def green_line_station_to_block (self, swap_stations):
        #loop through stations to get swapped
        for i in range(len(swap_stations)):
            for j in range(len(self.green_line_station_names)):
                if swap_stations[i] == self.green_line_station_names[j]:
                    swap_stations[i] = self.green_line_station_blocks[j]
        
        #return the block numbers
        return swap_stations
    
    def green_line_block_to_station (self, swap_blocks):
        #check if the variable is just 'int'
        if type(swap_blocks) is int:
            for j in range(len(self.green_line_station_blocks)):
                if swap_blocks == self.green_line_station_blocks[j]:
                    return self.green_line_station_names[j]

        #otherwise loop through blocks to get swapped
        for i in range(len(swap_blocks)):
            for j in range(len(self.green_line_station_blocks)):
                if swap_blocks[i] == self.green_line_station_blocks[j]:
                    swap_blocks[i] = self.green_line_station_names[j]

        #return the station names
        return swap_blocks

# Line Object - A single line from the entire track network
class Line:
    def __init__(self):
        self.line_color = ""
        self.blocks: list[Block] = []
        self.graph: dict[int, list[int]] = {}
        self.path = []

    #Function to find shortest route between two blocks
    def get_shortest_path(self, start, end, path =[]):
        path = path + [start]
        if start == end:
            return path
        shortest = None
        for node in self.graph[start]:
            #print("current node is " + str(node))
            if node not in path:
                newpath = self.get_shortest_path(node, end, path)
                if newpath:
                    if not shortest or len(newpath) < len(shortest):
                        shortest = newpath
        return shortest
    
    def get_left_path(self, start, end):
        #get indicies of start and end
        #TODO - currently only the first stop on the route
        start_ind = np.where(self.path == start)[0]
        end_ind = np.where(self.path == end)[0]
        left_path = []
        len_path = len(self.path)

        #start and end cases
        if 0 in start_ind:
            start_ind = [0]
        if 0 in end_ind:
            end_ind = [len_path-1]

        #build path
        for block in range(start_ind[0]+1, end_ind[0]+1):
            left_path.append(self.path[block])
        
        return left_path
              
    #Function to get time between two blocks
    def get_time_between(self, start, end):
        #get shortest path first
        path = self.get_left_path(start, end)

        #multiply each block by time
        return len(path)*15

# Block Object - A single block linked to a single Track
class Block:
    def __init__(self):
        self.block_number = 0
        self.block_type = 0
        self.block_occupancy = False
        self.track_fault_status = False
        self.maintenance_status = False
        self.switch_direction = False
        self.traffic_light_color = False
        self.station_name = ""
        self.crossing_status = False
            
    # Get block number string
    def get_block_number_string(self):
        return str(self.block_number)
    
    # Get block type string
    def get_block_type_string(self):
        if(self.block_type == 0):
            return "Default"
        elif(self.block_type == 1):
            return "Junction"
        elif(self.block_type == 2):
            return "Station"
        elif(self.block_type == 3):
            return "Crossing"
        
    # Get block occupancy string
    def get_block_occupancy_string(self):
        return "Occupied" if(self.block_occupancy) else "Unoccupied"
    
    # Get track fault status string
    def get_track_fault_status_string(self):
        return "Detected" if(self.track_fault_status) else "Undetected"
    
    # Get maintenance status string
    def get_maintenance_status_string(self):
        return "Active" if(self.maintenance_status) else "Inactive"
    
    # Get switch direction string
    def get_switch_direction_string(self, line_int):
        if(self.block_type == 1):
            red_line_junction_switch_ends = [9,16,27,33,38,44,52]
            red_line_junction_receiver_ends = [[0,10],[1,15],[28,76],[72,32],[39,71],[67,43],[53,66]]
            red_line_junction_receiver_ends_left = [0,1,28,72,39,67,53]
            red_line_junction_receiver_ends_right = [10,15,76,32,71,43,66]
            green_line_junction_switch_ends = [13,28,57,63,77,85]
            green_line_junction_receiver_ends = [[12,1],[29,150],[0,58],[62,0],[101,76],[86,100]]
            green_line_junction_receiver_ends_left = [12,29,0,62,101,86]
            green_line_junction_receiver_ends_right = [1,150,58,0,76,100]
            if(line_int == 0):
                list_pos = 0
                if(self.block_number in red_line_junction_receiver_ends_left):
                    list_pos = red_line_junction_receiver_ends_left.index(self.block_number)
                elif(self.block_number in red_line_junction_receiver_ends_right):
                    list_pos = red_line_junction_receiver_ends_right.index(self.block_number)
                elif(self.block_number in red_line_junction_switch_ends):
                    list_pos = red_line_junction_switch_ends.index(self.block_number)
                return str(red_line_junction_switch_ends[list_pos]) + "-" + str(red_line_junction_receiver_ends[list_pos][0]) if(not self.switch_direction) else str(red_line_junction_switch_ends[list_pos]) + "-" + str(red_line_junction_receiver_ends[list_pos][1])
            elif(line_int == 1):
                list_pos = 0
                if(self.block_number in green_line_junction_receiver_ends_left):
                    list_pos = green_line_junction_receiver_ends_left.index(self.block_number)
                elif(self.block_number in green_line_junction_receiver_ends_right):
                    list_pos = green_line_junction_receiver_ends_right.index(self.block_number)
                elif(self.block_number in green_line_junction_switch_ends):
                    list_pos = green_line_junction_switch_ends.index(self.block_number)
                return str(green_line_junction_switch_ends[list_pos]) + "-" + str(green_line_junction_receiver_ends[list_pos][0]) if(not self.switch_direction) else str(green_line_junction_switch_ends[list_pos]) + "-" + str(green_line_junction_receiver_ends[list_pos][1])
        else:
            return ""
        
    # Get switch direction string list
    def get_switch_direction_string_list(self, line_int):
        red_line_junction_switch_ends = [9,16,27,33,38,44,52]
        red_line_junction_receiver_ends = [[0,10],[1,15],[28,76],[72,32],[39,71],[67,43],[53,66]]
        red_line_junction_receiver_ends_left = [0,1,28,72,39,67,53]
        red_line_junction_receiver_ends_right = [10,15,76,32,71,43,66]
        green_line_junction_switch_ends = [13,28,57,63,77,85]
        green_line_junction_receiver_ends = [[12,1],[29,150],[0,58],[62,0],[101,76],[86,100]]
        green_line_junction_receiver_ends_left = [12,29,0,62,101,86]
        green_line_junction_receiver_ends_right = [1,150,58,0,76,100]
        if(line_int == 0):
            list_pos = 0
            if(self.block_number in red_line_junction_receiver_ends_left):
                list_pos = red_line_junction_receiver_ends_left.index(self.block_number)
            elif(self.block_number in red_line_junction_receiver_ends_right):
                list_pos = red_line_junction_receiver_ends_right.index(self.block_number)
            elif(self.block_number in red_line_junction_switch_ends):
                list_pos = red_line_junction_switch_ends.index(self.block_number)
            if(self.switch_direction == 0):
                return [str(red_line_junction_switch_ends[list_pos]) + "-" + str(red_line_junction_receiver_ends[list_pos][0]), str(red_line_junction_switch_ends[list_pos]) + "-" + str(red_line_junction_receiver_ends[list_pos][1])]
            else:
                return [str(red_line_junction_switch_ends[list_pos]) + "-" + str(red_line_junction_receiver_ends[list_pos][1]), str(red_line_junction_switch_ends[list_pos]) + "-" + str(red_line_junction_receiver_ends[list_pos][0])]
        elif(line_int == 1):
            list_pos = 0
            if(self.block_number in green_line_junction_receiver_ends_left):
                list_pos = green_line_junction_receiver_ends_left.index(self.block_number)
            elif(self.block_number in green_line_junction_receiver_ends_right):
                list_pos = green_line_junction_receiver_ends_right.index(self.block_number)
            elif(self.block_number in green_line_junction_switch_ends):
                list_pos = green_line_junction_switch_ends.index(self.block_number)
            if(self.switch_direction == 0):
                return [str(green_line_junction_switch_ends[list_pos]) + "-" + str(green_line_junction_receiver_ends[list_pos][0]), str(green_line_junction_switch_ends[list_pos]) + "-" + str(green_line_junction_receiver_ends[list_pos][1])]
            else:
                return [str(green_line_junction_switch_ends[list_pos]) + "-" + str(green_line_junction_receiver_ends[list_pos][1]), str(green_line_junction_switch_ends[list_pos]) + "-" + str(green_line_junction_receiver_ends[list_pos][0])]
    
    # Get list of 3 blocks in a junction
    def get_tri_junction_blocks(self, line_int):
        red_line_junction_switch_ends = [9,16,27,33,38,44,52]
        red_line_junction_receiver_ends = [[0,10],[1,15],[28,76],[72,32],[39,71],[67,43],[53,66]]
        green_line_junction_switch_ends = [13,28,57,63,77,85]
        green_line_junction_receiver_ends = [[12,1],[29,150],[0,58],[62,0],[101,76],[86,100]]
        if(line_int == 0):
            list_pos = red_line_junction_switch_ends.index(self.block_number)
            return red_line_junction_switch_ends[list_pos],red_line_junction_receiver_ends[list_pos][0],red_line_junction_receiver_ends[list_pos][1]
        elif(line_int == 1):
            list_pos = green_line_junction_switch_ends.index(self.block_number)
            return green_line_junction_switch_ends[list_pos],green_line_junction_receiver_ends[list_pos][0],green_line_junction_receiver_ends[list_pos][1]

    # Get switch direction boolean
    def get_switch_direction_bool(self, direction, line_int):
        if(direction == ""):
           return False
        red_line_junction_switch_ends = [9,16,27,33,38,44,52]
        red_line_junction_receiver_ends = [[0,10],[1,15],[28,76],[72,32],[39,71],[67,43],[53,66]]
        green_line_junction_switch_ends = [13,28,57,63,77,85]
        green_line_junction_receiver_ends = [[12,1],[29,150],[0,58],[62,0],[101,76],[86,100]]
        string_split = direction.split("-")
        first_num = int(string_split[0])
        second_num = int(string_split[1])
        if(line_int == 0):
            list_pos_switch = red_line_junction_switch_ends.index(first_num)
            return False if(second_num == red_line_junction_receiver_ends[list_pos_switch][0]) else True
        elif(line_int == 1):
            list_pos_switch = green_line_junction_switch_ends.index(first_num)
            return False if(second_num == green_line_junction_receiver_ends[list_pos_switch][0]) else True

    # Gets index of 3 blocks in junction
    def get_all_junction_block_indexes(self, line_int, block_int, direction):
        red_line_junction_switch_ends = [9,16,27,33,38,44,52]
        red_line_junction_receiver_ends = [[0,10],[1,15],[28,76],[72,32],[39,71],[67,43],[53,66]]
        red_line_junction_receiver_ends_left = [0,1,28,72,39,67,53]
        red_line_junction_receiver_ends_right = [10,15,76,32,71,43,66]
        green_line_junction_switch_ends = [13,28,57,63,77,85]
        green_line_junction_receiver_ends = [[12,1],[29,150],[0,58],[62,0],[101,76],[86,100]]
        green_line_junction_receiver_ends_left = [12,29,0,62,101,86]
        green_line_junction_receiver_ends_right = [1,150,58,0,76,100]
        if(line_int == 0):
            list_pos = 0
            if(block_int in red_line_junction_receiver_ends_left):
                list_pos = red_line_junction_receiver_ends_left.index(block_int)
            elif(block_int in red_line_junction_receiver_ends_right):
                list_pos = red_line_junction_receiver_ends_right.index(block_int)
            elif(block_int in red_line_junction_switch_ends):
                list_pos = red_line_junction_switch_ends.index(block_int)
            return [red_line_junction_switch_ends[list_pos], red_line_junction_receiver_ends_left[list_pos], red_line_junction_receiver_ends_right[list_pos]]
        elif(line_int == 1):
            list_pos = 0
            if(block_int in green_line_junction_receiver_ends_left):
                list_pos = green_line_junction_receiver_ends_left.index(block_int)
            elif(block_int in green_line_junction_receiver_ends_right):
                list_pos = green_line_junction_receiver_ends_right.index(block_int)
            elif(block_int in green_line_junction_switch_ends):
                list_pos = green_line_junction_switch_ends.index(block_int)
            return [green_line_junction_switch_ends[list_pos], green_line_junction_receiver_ends_left[list_pos], green_line_junction_receiver_ends_right[list_pos]]

    # Get traffic light color string 
    def get_traffic_light_color_string(self):
        if(self.block_type == 1):
            return "Green" if(self.traffic_light_color) else "Red"
        else:
            return ""
        
    # Get traffic light color boolean
    def get_traffic_light_color_bool(self, color):
        return True if(color == "Green") else False
    
    # Gets crossing status boolean
    def get_crossing_status_bool(self, status):
        return True if(status == "Active") else False
        
    # Gets crossing status string
    def get_crossing_status_string(self):
        if(self.block_type == 3):
            return "Active" if(self.crossing_status == True) else "Inactive"
        else:
            return ""