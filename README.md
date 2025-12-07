# Group 4 Choo Crew
|Name| Module|
|-|-|
|Mari Inglese | CTC|
|Connor Kariotis | SW Wayside Controller|
|Oliver Kettleson-Belinkie| HW Wayside Controller|
|Ledi Zhao | Train Model|
|Julen Coca Knorr | SW Train Controller|
|James Struyk | HW Train Controller|


# User Help

## CTC

## SW Wayside Controller
<img src="./screenshots/sw_wayside_UI_ss.png">

The software wayside controller is defaulted to automatic mode, and must be assigned a plc file prior to running the program, however it can be changed later.

The software wayside controller is responsible for the state of all track feature, such as the switches, gates, and lights. It also recieves suggested speed and authority from the CTC and determines commanded speed and authority for each train.

### Select A Block

The lower right section of the UI is where the user can view all block information and select a block to better view that blocks data

<img src="./screenshots/sw_wayside_select_block_ss.png">

- By selecting a block using a checkbox displayed on the left, the user will see that blocks information in more detail outlined in red on the image above.

### View Active Train Data

The upper middle section of the UI displays all active train information if the train is occupying a block that is within that waysides controlled blocks

<img src="./screenshots/sw_wayside_active_train_data.png">

- The train ID, current block position, commanded speed, and commanded authority will be visible. 

### Maintenance Mode

Maintenance mode of the software wayside controller can be accessed by clicking the checkbox labeled "Toggle Maintenance"

<img src="./screenshots/sw_wayside_maintenance.png">

- After maintenace is toggles, the two selection boxes are used to manually change switch positions. Use the upper selection box to select a switch, and the lower one to select the state.
- Below that, the user can select a new plc file by using the "Browse" click button. This button will open file explorer and allow you to select a new .py to run. if your upload is successful, the filename below the click button will update to the new file name.

## HW Wayside Controller

## Train Model

## SW Train Controller

## HW Train Controller
