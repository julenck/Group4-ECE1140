route_info = {
    "ID": [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21],
    "Name": ["Yard",
            "Glenbury",
             "Dormont", 
             "Mt. Lebanon",
             "Poplar",
             "Castle Shannon",
             "Dormont",
             "Glenbury",
             "Overbrook",
             "Inglewood",
             "Central",
             "Whited",
             "?",
             "Edgebrook",
             "Pioneer",
             "?",
             "Whited",
             "South Bank",
             "Central",
             "Inglewood",
             "Overbrook",
             "Yard"
    ],

    # inlcudes length of next station block but not current station block
    "Meters to next": [100,900,600,2686.6,600,715,952,540,450,450,1859,1050,850,700,800,1200,1150,400,396,450,100,0]
}

route_lookup = {}
for i in range(len(route_info["ID"])):
    name = route_info["Name"][i]
    route_lookup[name] = {
        "id": route_info["ID"][i],
        "meters_to_next": route_info["Meters to next"][i]
    }
