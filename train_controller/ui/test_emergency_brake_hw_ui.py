import sys
import os
 
# Add parent directory to path to import train_controller modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Import after adding to path
from api.train_controller_api import train_controller_api
from train_controller_hw_ui import train_controller

class MockUI:
    pass


def create_test_controller(api):
    gpio_pins = {}  # Empty for testing
    i2c_bus_number = 1
    i2c_address = {}
    
    return train_controller(
        ui=MockUI(),
        api=api,
        gpio_pins=gpio_pins,
        i2c_bus_number=i2c_bus_number,
        i2c_address=i2c_address
    )


def print_state(state, label="STATE"):
    print(f"\n{label}:")
    print(f"  Emergency Brake: {state['emergency_brake']}")
    print(f"  Driver Velocity: {state['driver_velocity']:.2f} mph")

def test_emergency_brake_activation():
    print("TEST 1: EMERGENCY BRAKE ACTIVATION")
    
    api = train_controller_api(train_id=999)
    controller = create_test_controller(api)
    
    # Initial ADC potentiometer setting
    adc_potentiometer_setting = 45.0  # Simulates physical pot position
    
    api.update_state({
        'emergency_brake': False,
        'driver_velocity': adc_potentiometer_setting
    })
    
    print_state(api.get_state(), "INITIAL VALUES")

    # Activating emergency brake
    print("\nActivating Emergency Brake")
    api.update_state({'emergency_brake': True})
    controller.emergency_brake_activated()
    
    state_after = api.get_state()
    print_state(state_after, "NEW VALUES")

    expected_emergency_brake = True
    expected_driver_velocity = 0.0  # emergency_brake_activated() sets this to 0

    print(f"\nExpected Values: Emergency Brake={expected_emergency_brake}, Driver Velocity={expected_driver_velocity} mph")

    test_passed = False
    
    if (expected_emergency_brake == state_after['emergency_brake']):
        print("Emergency Brake state is as expected. TEST PASSED")
    else:
        print("TEST FAILED")
    if (abs(expected_driver_velocity - state_after['driver_velocity']) < 0.01):
        print("Driver Velocity is as expected. TEST PASSED")
    else:
        print("TEST FAILED")
    
    if (expected_emergency_brake == state_after['emergency_brake'] and
        abs(expected_driver_velocity - state_after['driver_velocity']) < 0.01):
        test_passed = True
        print("\nALL TESTS PASSED")
        return test_passed
    else:
        return test_passed

def test_emergency_brake_deactivation():
    print("\nTEST 2: EMERGENCY BRAKE DEACTIVATION")
    
    api = train_controller_api(train_id=999)
    controller = create_test_controller(api)

    # Initial ADC potentiometer setting
    adc_potentiometer_setting = 45.0  # Simulates physical pot position
    
    api.update_state({
        'emergency_brake': False,
        'driver_velocity': adc_potentiometer_setting
    })
    
    print_state(api.get_state(), "INITIAL VALUES")
    
    # Activating and Deactivating emergency brake
    print("\nActivating Emergency Brake")
    api.update_state({'emergency_brake': True})
    controller.emergency_brake_activated()
    
    state_after = api.get_state()
    print_state(state_after, "EMERGENCY ACTIVE VALUES")

    print("\nDeactivating Emergency Brake")
    api.update_state({'emergency_brake': False})
    controller.emergency_brake_activated()
    
    # ADC still reads potentiometer setting
    api.update_state({'driver_velocity': adc_potentiometer_setting})

    state_after = api.get_state()
    print_state(state_after, "EMERGENCY DEACTIVE VALUES")
    
    expected_emergency_brake = False
    expected_driver_velocity = adc_potentiometer_setting

    print(f"\nExpected Values: Emergency Brake={expected_emergency_brake}, Driver Velocity={expected_driver_velocity} mph")

    test_passed = False
    
    if (expected_emergency_brake == state_after['emergency_brake']):
        print("Emergency Brake state is as expected. TEST PASSED")
    else:
        print("TEST FAILED")
    if (abs(expected_driver_velocity - state_after['driver_velocity']) < 0.01):
        print("Driver Velocity is as expected. TEST PASSED")
    else:
        print("TEST FAILED")
    
    if (expected_emergency_brake == state_after['emergency_brake'] and
        abs(expected_driver_velocity - state_after['driver_velocity']) < 0.01):
        test_passed = True
        print("\nALL TESTS PASSED")
        return test_passed
    else:
        return test_passed

if __name__ == "__main__":
    # Run tests
    test1_result = test_emergency_brake_activation()
    test2_result = test_emergency_brake_deactivation()
