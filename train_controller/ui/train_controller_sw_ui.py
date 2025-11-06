"""Train Controller Software UI.

This module provides the driver interface for the Train Controller,
implementing the same functionality as the hardware version but in software.
Interfaces with the train_controller_api for state management and Train Model communication.

Author: Julen Coca-Knorr
"""

import tkinter as tk
from tkinter import ttk
import os
import sys
import time  # Add time module for real-time tracking

# Add parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Import API
from api.train_controller_api import train_controller_api

class sw_train_controller_ui(tk.Tk):
    """Software implementation of the Train Controller driver interface.
    
    Provides the same functionality as the hardware implementation, including:
        - Speed control and display
        - Authority and commanded speed display
        - Door controls
        - Light controls
        - Temperature controls
        - Brake controls
        - Engineering panel with Kp/Ki settings
        
    Uses the train_controller_api to communicate with Train Model / TEST UI.
    """
    
    def __init__(self):
        """Initialize the driver interface."""
        super().__init__()
        
        # Configure window
        self.title("Train Controller - Driver Interface")
        self.geometry("1200x800")
        self.configure(bg='lightgray')
        
        # Initialize API
        self.api = train_controller_api()
        
        # Initialize set speed to match commanded speed
        initial_state = self.api.get_state()
        self.api.update_state({'set_speed': initial_state.get('commanded_speed', 0)})
        
        # Define colors for buttons
        self.active_color = '#ff4444'
        self.normal_color = 'lightgray'
        
        # Main layout configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=3)  # More space for top section
        self.grid_rowconfigure(1, weight=2)  # Space for controls
        self.grid_rowconfigure(2, weight=1)  # Less space for engineering panel
        
        # Create main container frames with proper weights
        self.top_frame = ttk.Frame(self)
        self.top_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        self.top_frame.grid_columnconfigure(0, weight=1)
        self.top_frame.grid_columnconfigure(1, weight=1)
        
        self.control_frame = ttk.Frame(self)
        self.control_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        
        self.engineering_frame = ttk.Frame(self)
        self.engineering_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        
        # Create UI sections in new layout
        self.create_speed_section()     # Left side of top frame
        self.create_info_table()        # Right side of top frame
        self.create_control_section()    # Middle frame
        self.create_engineering_panel()  # Bottom frame
        
        # Initialize PI controller variables
        self._accumulated_error = 0
        self._last_update_time = time.time()
        
        # Start periodic updates
        self.update_interval = 500  # 500ms = 0.5 seconds
        self.periodic_update()
    
    def create_speed_section(self):
        """Create speed control and display section."""
        speed_frame = ttk.LabelFrame(self.top_frame, text="Speed Control")
        speed_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        
        # Current speed display (large and centered)
        speed_display_frame = ttk.Frame(speed_frame)
        speed_display_frame.pack(expand=True, fill="both", pady=20)
        
        ttk.Label(speed_display_frame, text="Current Speed", font=('Arial', 14)).pack()
        self.speed_display = ttk.Label(speed_display_frame, text="0 MPH", font=('Arial', 36, 'bold'))
        self.speed_display.pack(pady=10)
        
        # Speed control buttons in their own frame
        control_frame = ttk.Frame(speed_frame)
        control_frame.pack(fill="x", padx=20, pady=10)
        
        # Speed Up/Down buttons side by side
        ttk.Button(control_frame, text="▲ Speed Up", command=self.speed_up).pack(side="left", expand=True, padx=5)
        ttk.Button(control_frame, text="▼ Speed Down", command=self.speed_down).pack(side="right", expand=True, padx=5)
        
        # Set speed display
        set_speed_frame = ttk.Frame(speed_frame)
        set_speed_frame.pack(fill="x", pady=10)
        ttk.Label(set_speed_frame, text="Driver Set Speed:").pack()
        self.set_speed_label = ttk.Label(set_speed_frame, text="0 MPH", font=('Arial', 12, 'bold'))
        self.set_speed_label.pack()
    
    def create_info_table(self):
        """Create the information table displaying train status and inputs from Train Model."""
        table_frame = ttk.LabelFrame(self.top_frame, text="Train Information")
        table_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        
        # Create a treeview for the table
        self.info_table = ttk.Treeview(table_frame, columns=("Name", "Value", "Unit"), show="headings", height=10)
        self.info_table.heading("Name", text="Parameter")
        self.info_table.heading("Value", text="Value")
        self.info_table.heading("Unit", text="Unit")
        
        # Configure column widths
        self.info_table.column("Name", width=200)
        self.info_table.column("Value", width=150)
        self.info_table.column("Unit", width=100)
        
        # Add rows with initial values - (Name, Value, Unit)
        self.info_table.insert("", "end", "commanded_speed", values=("Commanded Speed", "0", "mph"))
        self.info_table.insert("", "end", "speed_limit", values=("Speed Limit", "0", "mph"))
        self.info_table.insert("", "end", "authority", values=("Commanded Authority", "0", "yds"))
        self.info_table.insert("", "end", "temperature", values=("Train Temperature", "70", "°F"))
        self.info_table.insert("", "end", "next_stop", values=("Next Stop", "--", "Name"))
        self.info_table.insert("", "end", "power", values=("Power Command", "0", "W"))
        self.info_table.insert("", "end", "station_side", values=("Station Side", "--", "right/left"))
        self.info_table.insert("", "end", "failures", values=("System Failures", "None", ""))
        
        # Add explanatory text
        ttk.Label(table_frame, text="*Values shown are inputs from Train Model", 
                 font=('Arial', 8, 'italic')).pack(side="bottom", pady=5)
        
        self.info_table.pack(padx=5, pady=5, expand=True, fill="both")
    
    def create_control_section(self):
        """Create control buttons section."""
        controls_label_frame = ttk.LabelFrame(self.control_frame, text="Train Controls")
        controls_label_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create a frame for all buttons
        button_frame = ttk.Frame(controls_label_frame)
        button_frame.pack(expand=True, fill="both", padx=5, pady=5)
        
        # Configure grid for button layout
        for i in range(3):  # 3 rows
            button_frame.grid_rowconfigure(i, weight=1)
        for i in range(4):  # 4 columns
            button_frame.grid_columnconfigure(i, weight=1)
        
        # Create all buttons with consistent size and spacing
        button_width = 15
        button_height = 2
        padding = 5
        
        # Row 1
        self.lights_btn = tk.Button(button_frame, text="Lights", command=self.toggle_lights,
                                  bg=self.normal_color, width=button_width, height=button_height)
        self.lights_btn.grid(row=0, column=0, padx=padding, pady=padding)
        
        self.left_door_btn = tk.Button(button_frame, text="Left Door", command=self.toggle_left_door,
                                     bg=self.normal_color, width=button_width, height=button_height)
        self.left_door_btn.grid(row=0, column=1, padx=padding, pady=padding)
        
        self.right_door_btn = tk.Button(button_frame, text="Right Door", command=self.toggle_right_door,
                                      bg=self.normal_color, width=button_width, height=button_height)
        self.right_door_btn.grid(row=0, column=2, padx=padding, pady=padding)
        
        # Row 2 (Brake Controls)

        # Announcement button
        self.announce_btn = tk.Button(button_frame, text="Announcement", command=self.toggle_announcement,
                                   bg=self.normal_color, width=button_width, height=button_height)
        self.announce_btn.grid(row=1, column=0, padx=padding, pady=padding)

        self.service_brake_btn = tk.Button(button_frame, text="Service Brake", 
                                         command=self.toggle_service_brake,
                                         bg=self.normal_color, width=button_width, height=button_height)
        self.service_brake_btn.grid(row=1, column=1, padx=padding, pady=padding)
        
        self.emergency_brake_btn = tk.Button(button_frame, text="Emergency Brake", 
                                           command=self.emergency_brake,
                                           bg=self.normal_color, width=button_width, height=button_height)
        self.emergency_brake_btn.grid(row=1, column=2, padx=padding, pady=padding)

                
        # Row 3 (Temperature Controls)
        temperature_frame = ttk.LabelFrame(button_frame, text="Temperature Control")
        temperature_frame.grid(row=2, column=0, columnspan=1, padx=padding, pady=padding, sticky="nsew")
        
        # Set temperature display
        ttk.Label(temperature_frame, text="Set Temperature:").grid(row=0, column=0, padx=5, pady=2)
        self.set_temp_label = ttk.Label(temperature_frame, text="70°F", font=('Arial', 12))
        self.set_temp_label.grid(row=0, column=1, padx=5, pady=2)
        
        # Current temperature display
        ttk.Label(temperature_frame, text="Current Temp:").grid(row=1, column=0, padx=5, pady=2)
        self.current_temp_label = ttk.Label(temperature_frame, text="70°F", font=('Arial', 12))
        self.current_temp_label.grid(row=1, column=1, padx=5, pady=2)
        
        # Temperature control buttons
        ttk.Button(temperature_frame, text="↑", command=self.temp_up).grid(row=0, column=2, padx=5, pady=2)
        ttk.Button(temperature_frame, text="↓", command=self.temp_down).grid(row=1, column=2, padx=5, pady=2)

        
    def create_engineering_panel(self):
        """Create engineering control panel."""
        eng_frame = ttk.LabelFrame(self.engineering_frame, text="Engineering Panel")
        eng_frame.pack(fill="x", expand=True, padx=10, pady=5)
        
        # Kp and Ki inputs
        ttk.Label(eng_frame, text="Kp:").grid(row=0, column=0, padx=5, pady=5)
        self.kp_entry = ttk.Entry(eng_frame)
        self.kp_entry.grid(row=0, column=1, padx=5, pady=5)
        self.kp_entry.insert(0, "10.0")  # Default Kp value for good control
        
        ttk.Label(eng_frame, text="Ki:").grid(row=0, column=2, padx=5, pady=5)
        self.ki_entry = ttk.Entry(eng_frame)
        self.ki_entry.grid(row=0, column=3, padx=5, pady=5)
        self.ki_entry.insert(0, "0.5")  # Default Ki value for good control
        
        self.lock_btn = ttk.Button(eng_frame, text="Lock Values", command=self.lock_engineering_values)
        self.lock_btn.grid(row=0, column=4, padx=20, pady=5)
    
    def periodic_update(self):
        """Update display every update_interval milliseconds."""
        try:
            current_state = self.api.get_state()
            
            # Check for critical failures that require emergency brake
            critical_failure = (current_state.get('engine_failure', False) or 
                              current_state.get('signal_failure', False) or 
                              current_state.get('brake_failure', False))
            
            if critical_failure and not current_state['emergency_brake']:
                # Automatically engage emergency brake on critical failure
                self.emergency_brake()
                
            # Recalculate power command based on current state
            if (not current_state['emergency_brake'] and 
                current_state['service_brake'] == 0 and 
                not critical_failure):
                power = self.calculate_power_command(current_state)
                if power != current_state['power_command']:
                    self.api.update_state({'power_command': power})
            else:
                # Reset accumulated error when brakes are active
                if hasattr(self, '_accumulated_error'):
                    self._accumulated_error = 0
                # No power when brakes are active or failures present
                self.api.update_state({'power_command': 0,
                                     'set_speed': 0})
            
            # Update current speed display
            self.speed_display.config(text=f"{current_state['velocity']:.1f} MPH")
            
            # Update information table with values (Name column stays constant)
            self.info_table.set("commanded_speed", column="Value", value=f"{current_state['commanded_speed']:.1f}")
            self.info_table.set("speed_limit", column="Value", value=f"{current_state['speed_limit']:.1f}")
            self.info_table.set("authority", column="Value", value=f"{current_state['commanded_authority']:.1f}")
            self.info_table.set("temperature", column="Value", value=f"{current_state['train_temperature']:.1f}")
            self.info_table.set("next_stop", column="Value", value=current_state['next_stop'])
            self.info_table.set("power", column="Value", value=f"{current_state['power_command']:.1f}")
            self.info_table.set("station_side", column="Value", value=current_state['station_side'])
            
            # Update failures in table with color
            failures = []
            has_failures = False
            if current_state.get('engine_failure', False):
                failures.append("Engine")
                has_failures = True
            if current_state.get('signal_failure', False):
                failures.append("Signal")
                has_failures = True
            if current_state.get('brake_failure', False):
                failures.append("Brake")
                has_failures = True
            failure_text = ", ".join(failures) if failures else "None"
            
            # Update failure text and color
            self.info_table.set("failures", column="Value", value=failure_text)
            # Change text color based on failure state
            self.info_table.tag_configure("failure_tag", foreground="red")
            self.info_table.tag_configure("normal_tag", foreground="black")
            if has_failures:
                self.info_table.item("failures", tags=("failure_tag",))
            else:
                self.info_table.item("failures", tags=("normal_tag",))
            
            # Update speed displays
            self.speed_display.config(text=f"{current_state['velocity']:.1f} MPH")
            self.set_speed_label.config(text=f"{current_state['set_speed']:.1f} MPH")
            
            # Update temperature displays
            self.set_temp_label.config(text=f"{current_state['set_temperature']}°F")
            self.current_temp_label.config(text=f"{current_state['train_temperature']}°F")
            
            # Update control button states
            self.update_button_states(current_state)
            
        except Exception as e:
            print(f"Update error: {e}")
        finally:
            # Always schedule next update
            self.after(self.update_interval, self.periodic_update)
    
    def update_failure_indicator(self, label, system, failed):
        """Update a failure indicator label."""
        label.config(
            text=f"{system}: {'FAILED' if failed else 'OK'}",
            foreground="red" if failed else "green"
        )
    
    def update_button_states(self, state):
        """Update button colors based on their states."""
        # Door buttons
        self.left_door_btn.configure(bg=self.active_color if state['left_door'] else self.normal_color)
        self.right_door_btn.configure(bg=self.active_color if state['right_door'] else self.normal_color)
        
        # Announcement button
        self.announce_btn.configure(bg=self.active_color if state['announce_pressed'] else self.normal_color)
        
        # Lights button
        self.lights_btn.configure(bg=self.active_color if state['lights'] else self.normal_color)
        
        # Brake buttons
        self.service_brake_btn.configure(bg=self.active_color if state['service_brake'] > 0 else self.normal_color)
        
        # Emergency brake configuration
        if state['emergency_brake']:
            self.emergency_brake_btn.configure(bg=self.active_color, state='disabled')
        else:
            self.emergency_brake_btn.configure(bg=self.normal_color, state='normal')
    
    # Control methods
    def calculate_power_command(self, state):
        """Calculate power command based on speed difference and Kp/Ki values.
        
        Implements PI control with:
        - Real-time accumulated error tracking
        - Anti-windup protection
        - Power limiting
        - Zero power when error is zero
        """
        # Get current values
        current_speed = state['velocity']
        driver_set_speed = state['set_speed']
        kp = state['kp']
        ki = state['ki']
        
        # Calculate speed error
        speed_error = driver_set_speed - current_speed
        
        # If speed error is effectively zero (within small threshold), return zero power
        if abs(speed_error) < 0.01:  # 0.01 MPH threshold
            self._accumulated_error = 0  # Reset accumulated error
            return 0  # No power needed when at desired speed
        
        # Get current time
        current_time = time.time()  # Use real time in seconds
        
        # Ensure time tracking variables exist
        if not hasattr(self, '_last_update_time'):
            self._last_update_time = current_time
        if not hasattr(self, '_accumulated_error'):
            self._accumulated_error = 0
            
        # Calculate real time step
        dt = current_time - self._last_update_time
        dt = max(0.001, min(dt, 1.0))  # Limit dt between 1ms and 1s for stability
        
        # Update accumulated error with anti-windup and scaling
        # Scale the error integration based on time step
        self._accumulated_error += speed_error * dt
        
        # Anti-windup limits (scaled by ki to prevent excessive integral term)
        max_integral = 120000 / ki if ki != 0 else 0
        self._accumulated_error = max(-max_integral, min(max_integral, self._accumulated_error))
        
        # Calculate PI control output
        proportional = kp * speed_error
        integral = ki * self._accumulated_error
        
        # Debug monitoring
        if hasattr(self, 'debug') and self.debug:
            print(f"Time: {current_time:.3f}, dt: {dt:.3f}")
            print(f"Speed Error: {speed_error:.2f}, P: {proportional:.2f}, I: {integral:.2f}")
            print(f"Accumulated Error: {self._accumulated_error:.2f}")
        
        # Calculate total power command
        power = proportional + integral
        
        # Limit power
        power = max(0, min(power, 120000))  # 120kW max power
        
        # Anti-windup: adjust accumulated error when power saturates
        if power == 120000 and integral > 0:
            # Back-calculate integral term to match power limit
            self._accumulated_error = (120000 - proportional) / ki if ki != 0 else 0
        elif power == 0 and integral < 0:
            # Reset integral term when power is zero
            self._accumulated_error = -proportional / ki if ki != 0 else 0
        
        # Update last time for next iteration
        self._last_update_time = current_time
        
        return power
    
    def speed_up(self):
        """Increase driver's set speed and update power command."""
        state = self.api.get_state()
        current_set_speed = state['set_speed']
        commanded_speed = state['commanded_speed']
        speed_limit = state['speed_limit']
        
        # Increase set speed (not exceeding commanded speed or speed limit)
        max_allowed_speed = min(commanded_speed, speed_limit)
        new_speed = min(max_allowed_speed, current_set_speed + 1)
        
        # Update state with new set speed
        state['set_speed'] = new_speed
        
        # Calculate and update power command
        power = self.calculate_power_command(state)
        self.api.update_state({
            'set_speed': new_speed,
            'power_command': power
        })
    
    def speed_down(self):
        """Decrease driver's set speed and update power command."""
        state = self.api.get_state()
        current_set_speed = state['set_speed']
        
        # Decrease set speed (minimum 0)
        new_speed = max(0, current_set_speed - 1)
        
        # Update state with new set speed
        state['set_speed'] = new_speed
        
        # Calculate and update power command
        power = self.calculate_power_command(state)
        self.api.update_state({
            'set_speed': new_speed,
            'power_command': power
        })
    
    def toggle_left_door(self):
        """Toggle left door state."""
        state = self.api.get_state()
        self.api.update_state({'left_door': not state['left_door']})
    
    def toggle_right_door(self):
        """Toggle right door state."""
        state = self.api.get_state()
        self.api.update_state({'right_door': not state['right_door']})
    
    def toggle_lights(self):
        """Toggle lights state."""
        state = self.api.get_state()
        self.api.update_state({'lights': not state['lights']})
    
    def toggle_announcement(self):
        """Toggle announcement state."""
        state = self.api.get_state()
        # Toggle announce_pressed state
        self.api.update_state({'announce_pressed': not state['announce_pressed']})
        
    def temp_up(self):
        """Increase desired temperature setpoint."""
        current_state = self.api.get_state()
        set_temp = current_state['set_temperature']
        if set_temp < 95:  # Maximum temperature limit
            self.api.update_state({
                'set_temperature': set_temp + 1,
                'temperature_up': True,
                'temperature_down': False
            })
    
    def temp_down(self):
        """Decrease desired temperature setpoint."""
        current_state = self.api.get_state()
        set_temp = current_state['set_temperature']
        if set_temp > 55:  # Minimum temperature limit
            self.api.update_state({
                'set_temperature': set_temp - 1,
                'temperature_up': False,
                'temperature_down': True
            })
    
    def toggle_service_brake(self):
        """Toggle service brake state."""
        state = self.api.get_state()
        self.api.update_state({'service_brake': 100 if state['service_brake'] == 0 else 0})
    
    def emergency_brake(self):
        """Activate emergency brake for 5 seconds."""
        self.api.update_state({'emergency_brake': True,
                               'set_speed': 0 # set speed to 0 when the e brake is pressed
                               })
        # Schedule the brake to release after 5000ms (5 seconds)
        self.after(5000, self.release_emergency_brake)
    
    def release_emergency_brake(self):
        """Release the emergency brake after delay."""
        self.api.update_state({'emergency_brake': False})
    
    def lock_engineering_values(self):
        """Lock Kp and Ki values."""
        try:
            kp = float(self.kp_entry.get())
            ki = float(self.ki_entry.get())
            
            self.api.update_state({
                'kp': kp,
                'ki': ki,
                'engineering_panel_locked': True
            })
            
            # Disable inputs
            self.kp_entry.configure(state="disabled")
            self.ki_entry.configure(state="disabled")
            self.lock_btn.configure(state="disabled")
            
        except ValueError:
            tk.messagebox.showerror("Error", "Kp and Ki must be valid numbers")

if __name__ == "__main__":
    app = sw_train_controller_ui()
    app.mainloop()



