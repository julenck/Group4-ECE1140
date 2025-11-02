route_info = {
    "ID": [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21],
    "Block": [0,65,73,77,88,96,105,114,123,132,141,22,16,9,2,16,22,31,39,48,57,0],
    "Name": ["Yard",
            "Glenbury",
             "Dormont", 
             "Mt. Lebanon",
             "Poplar",
             "Castle Shannon",
             "Dormont1",
             "Glenbury1",
             "Overbrook",
             "Inglewood",
             "Central",
             "Whited",
             "?",
             "Edgebrook",
             "Pioneer",
             "?1",
             "Whited1",
             "South Bank",
             "Central1",
             "Inglewood1",
             "Overbrook1",
             "Yard"
    ],

    # inlcudes length of next station block but not current station block
    "Meters to next": [100,900,600,2686.6,600,715,952,540,450,450,1859,1050,850,700,800,1200,1150,400,396,450,100,0]
}

route_lookup_via_station = {}
for i in range(len(route_info["ID"])):
    name = route_info["Name"][i]
    route_lookup_via_station[name] = {
        "id": route_info["ID"][i],
        "meters_to_next": route_info["Meters to next"][i]
    }

route_lookup_via_id = {}
for i in range(len(route_info["ID"])):
    id = route_info["ID"][i]
    route_lookup_via_id[id] = {
        "name": route_info["Name"][i],
        "meters_to_next": route_info["Meters to next"][i],
        "block": route_info["Block"][i]
    }

