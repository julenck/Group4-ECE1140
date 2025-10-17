"""Database module for Train Controller state management.

This module provides database operations for storing and retrieving train states.
It manages the persistence of train data between the test UI and main UI.
"""

import sqlite3
from datetime import datetime
import os

# Database schema version
SCHEMA_VERSION = 1.0

class train_database:
    """Manages train state persistence using SQLite.
    
    This class handles all database operations for the Train Controller module,
    including creation, updates, and retrieval of train states. It maintains
    a separate database file for train controller to ensure module isolation.
    
    Attributes:
        db_path: String path to the SQLite database file.
    """
    
    def __init__(self):
        """Initialize database connection and create schema.
        
        Creates a new database file in the train_controller directory if it
        doesn't exist, or connects to an existing one. Automatically initializes
        the database schema on creation.
        """
        # Create database in train_controller directory for module isolation
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.db_path = os.path.join(base_dir, "train_controller.db")
        self.init_db()

    def init_db(self):
        """Initialize the database schema.
        
        Creates the train_states table if it doesn't exist. The schema includes:
            - Train identification
            - Speed and authority values
            - Station and beacon information
            - Brake status
            - Failure states
            - Automatic timestamp tracking
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS train_states (
                    id INTEGER PRIMARY KEY,
                    -- Engineering Controls (once locked, cannot be changed)
                    kp REAL,                 -- Proportional gain for speed control
                    ki REAL,                 -- Integral gain for speed control
                    engineering_panel_locked BOOLEAN, -- Whether Kp and Ki are locked
                    
                    -- Inputs from Train Model
                    commanded_speed REAL,      -- Target operating speed from CTC (mph)
                    commanded_authority REAL,  -- Distance train is permitted to travel (yards)
                    speed_limit REAL,         -- Maximum legal speed (mph)
                    velocity REAL,            -- Current train velocity (mph)
                    next_stop TEXT,           -- Next station stop (for announcements)
                    station_side TEXT,        -- Side doors to open at next station (left/right)
                    train_temperature INT,    -- Current temperature inside train (°F)
                    engine_failure BOOLEAN,   -- Train engine failure status
                    signal_failure BOOLEAN,   -- Signal pickup failure status
                    brake_failure BOOLEAN,    -- Brake failure status
                    
                    -- Inputs from Driver (shown in Test UI)
                    set_speed REAL,           -- Speed set by driver (mph)
                    service_brake INT,        -- Service brake percentage
                    right_door BOOLEAN,       -- Right door control
                    left_door BOOLEAN,        -- Left door control
                    lights BOOLEAN,           -- Lights control
                    temperature_up BOOLEAN,   -- Temperature increase command
                    temperature_down BOOLEAN, -- Temperature decrease command
                    announcement TEXT,        -- Announcement system message
                    emergency_brake BOOLEAN,  -- Emergency brake status
                    
                    -- Outputs to Train Model (shown in Test UI)
                    power_command REAL,       -- Power sent to train model (W)
                    
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def update_train_state(self, train_id: int, state_dict: dict) -> None:
        """Update or create a train state in the database.
        
        Updates an existing train's state if the train_id exists, otherwise
        creates a new train entry. All numeric values are converted to float
        where appropriate.
        
        Args:
            train_id: Unique identifier for the train.
            state_dict: Dictionary containing train state values:
                commanded_speed: Speed commanded by CTC (mph)
                commanded_authority: Distance permitted to travel (yards)
                speed_limit: Track speed limit (mph)
                velocity: Current train velocity (mph)
                next_stop: Next station stop (for announcements)
                station_side: Side doors to open at next station (left/right)
                train_temperature: Current temperature (°F)
                engine_failure: Engine failure status (boolean)
                signal_failure: Signal pickup failure status (boolean)
                brake_failure: Brake failure status (boolean)
                set_speed: Speed set by driver (mph)
                service_brake: Service brake percentage
                right_door: Right door control status (boolean)
                left_door: Left door control status (boolean)
                lights: Lights control status (boolean)
                temperature_up: Temperature increase command (boolean)
                temperature_down: Temperature decrease command (boolean)
                announcement: Announcement system message
                emergency_brake: Emergency brake status (boolean)
                power_command: Power sent to train model (W)
        
        Raises:
            sqlite3.Error: If database operation fails.
            ValueError: If numeric values cannot be converted to float.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM train_states WHERE id = ?", (train_id,))
            train_exists = cursor.fetchone() is not None
            
            if train_exists:
                query = """
                    UPDATE train_states SET
                        kp = ?,
                        ki = ?,
                        engineering_panel_locked = ?,
                        commanded_speed = ?,
                        commanded_authority = ?,
                        speed_limit = ?,
                        velocity = ?,
                        next_stop = ?,
                        station_side = ?,
                        train_temperature = ?,
                        engine_failure = ?,
                        signal_failure = ?,
                        brake_failure = ?,
                        set_speed = ?,
                        service_brake = ?,
                        right_door = ?,
                        left_door = ?,
                        lights = ?,
                        temperature_up = ?,
                        temperature_down = ?,
                        announcement = ?,
                        emergency_brake = ?,
                        power_command = ?,
                        timestamp = CURRENT_TIMESTAMP
                    WHERE id = ?
                """
                values = (
                    float(state_dict.get('kp', 0.0)),
                    float(state_dict.get('ki', 0.0)),
                    bool(state_dict.get('engineering_panel_locked', False)),
                    float(state_dict.get('commanded_speed', 0.0)),
                    float(state_dict.get('commanded_authority', 0.0)),
                    float(state_dict.get('speed_limit', 40.0)),
                    float(state_dict.get('velocity', 0.0)),
                    state_dict.get('next_stop', ''),
                    state_dict.get('station_side', 'right'),
                    int(state_dict.get('train_temperature', 70)),
                    bool(state_dict.get('engine_failure', False)),
                    bool(state_dict.get('signal_failure', False)),
                    bool(state_dict.get('brake_failure', False)),
                    float(state_dict.get('set_speed', 0.0)),
                    int(state_dict.get('service_brake', 0)),
                    bool(state_dict.get('right_door', False)),
                    bool(state_dict.get('left_door', False)),
                    bool(state_dict.get('lights', False)),
                    bool(state_dict.get('temperature_up', False)),
                    bool(state_dict.get('temperature_down', False)),
                    state_dict.get('announcement', ''),
                    bool(state_dict.get('emergency_brake', False)),
                    float(state_dict.get('power_command', 0.0)),
                    train_id
                )
            else:
                query = """
                    INSERT INTO train_states (
                        id, kp, ki, engineering_panel_locked,
                        commanded_speed, commanded_authority, speed_limit,
                        velocity, next_stop, station_side, train_temperature, 
                        engine_failure, signal_failure, brake_failure, set_speed,
                        service_brake, right_door, left_door, lights,
                        temperature_up, temperature_down, announcement,
                        emergency_brake, power_command
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                values = (
                    train_id,
                    float(state_dict.get('kp', 0.0)),
                    float(state_dict.get('ki', 0.0)),
                    bool(state_dict.get('engineering_panel_locked', False)),
                    float(state_dict.get('commanded_speed', 0.0)),
                    float(state_dict.get('commanded_authority', 0.0)),
                    float(state_dict.get('speed_limit', 40.0)),
                    float(state_dict.get('velocity', 0.0)),
                    state_dict.get('next_stop', ''),
                    state_dict.get('station_side', 'right'),
                    int(state_dict.get('train_temperature', 70)),
                    bool(state_dict.get('engine_failure', False)),
                    bool(state_dict.get('signal_failure', False)),
                    bool(state_dict.get('brake_failure', False)),
                    float(state_dict.get('set_speed', 0.0)),
                    int(state_dict.get('service_brake', 0)),
                    bool(state_dict.get('right_door', False)),
                    bool(state_dict.get('left_door', False)),
                    bool(state_dict.get('lights', False)),
                    bool(state_dict.get('temperature_up', False)),
                    bool(state_dict.get('temperature_down', False)),
                    state_dict.get('announcement', ''),
                    bool(state_dict.get('emergency_brake', False)),
                    float(state_dict.get('power_command', 0.0))
                )
            cursor.execute(query, values)

    def get_train_state(self, train_id: int) -> tuple:
        """Retrieve the current state of a specific train.
        
        Args:
            train_id: Unique identifier for the train.
            
        Returns:
            tuple: Contains all state values in schema order:
                (id, commanded_speed, commanded_authority, speed_limit,
                velocity, train_temperature, engine_failure,
                signal_failure, brake_failure, set_speed,
                service_brake, right_door, left_door, lights,
                temperature_up, temperature_down, announcement,
                emergency_brake, power_command, timestamp)
            None if train_id doesn't exist.
            
        Raises:
            sqlite3.Error: If database operation fails.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM train_states WHERE id = ?", (train_id,))
            return cursor.fetchone()
    
    def get_all_train_ids(self) -> list:
        """Retrieve IDs of all trains in the database.
        
        Returns:
            list: List of integer train IDs, sorted in ascending order.
            Empty list if no trains exist.
            
        Raises:
            sqlite3.Error: If database operation fails.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM train_states ORDER BY id")
            return [row[0] for row in cursor.fetchall()]