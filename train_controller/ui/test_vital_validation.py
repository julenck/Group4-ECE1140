"""
Unit tests for vital validation in train controller.

Tests the vital_validator_first_check and vital_validator_second_check classes
to ensure safety-critical controls are properly validated before being applied.

Run with: python -m unittest test_vital_validation.py
Or: python test_vital_validation.py
"""

import unittest
import sys
import os

# Add parent directory to path to import train controller modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from train_controller_sw_ui import (
    train_controller,
    train_controller_api,
    vital_train_controls,
    vital_validator_first_check,
    vital_validator_second_check
)


class TestVitalValidatorFirstCheck(unittest.TestCase):
    """Test cases for vital_validator_first_check (hard safety rules)."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = vital_validator_first_check()
        
    def test_speed_exceeds_limit_fails(self):
        """Test that speed exceeding limit is rejected."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=70.0,  # Exceeds limit
            driver_velocity=70.0,
            emergency_brake=False,
            service_brake=0,
            power_command=50000,
            commanded_authority=100,
            speed_limit=60.0
        )
        self.assertFalse(self.validator.validate(controls))
        
    def test_speed_at_limit_passes(self):
        """Test that speed exactly at limit passes."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=60.0,  # At limit
            driver_velocity=60.0,
            emergency_brake=False,
            service_brake=0,
            power_command=50000,
            commanded_authority=100,
            speed_limit=60.0
        )
        self.assertTrue(self.validator.validate(controls))
        
    def test_power_exceeds_maximum_fails(self):
        """Test that power > 120kW is rejected."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=30.0,
            driver_velocity=30.0,
            emergency_brake=False,
            service_brake=0,
            power_command=150000,  # Exceeds 120kW
            commanded_authority=100,
            speed_limit=60.0
        )
        self.assertFalse(self.validator.validate(controls))
        
    def test_power_at_maximum_passes(self):
        """Test that power at exactly 120kW passes."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=30.0,
            driver_velocity=30.0,
            emergency_brake=False,
            service_brake=0,
            power_command=120000,  # At max
            commanded_authority=100,
            speed_limit=60.0
        )
        self.assertTrue(self.validator.validate(controls))
        
    def test_negative_power_fails(self):
        """Test that negative power is rejected."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=30.0,
            driver_velocity=30.0,
            emergency_brake=False,
            service_brake=0,
            power_command=-5000,  # Negative
            commanded_authority=100,
            speed_limit=60.0
        )
        self.assertFalse(self.validator.validate(controls))
        
    def test_both_brakes_active_fails(self):
        """Test that both brakes active simultaneously is rejected."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=30.0,
            driver_velocity=30.0,
            emergency_brake=True,  # Both brakes
            service_brake=100,
            power_command=0,
            commanded_authority=100,
            speed_limit=60.0
        )
        self.assertFalse(self.validator.validate(controls))
        
    def test_emergency_brake_only_passes(self):
        """Test that only emergency brake active passes."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=30.0,
            driver_velocity=0,
            emergency_brake=True,  # Only emergency
            service_brake=0,
            power_command=0,
            commanded_authority=100,
            speed_limit=60.0
        )
        self.assertTrue(self.validator.validate(controls))
        
    def test_service_brake_only_passes(self):
        """Test that only service brake active passes."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=30.0,
            driver_velocity=0,
            emergency_brake=False,  # Only service
            service_brake=100,
            power_command=0,
            commanded_authority=100,
            speed_limit=60.0
        )
        self.assertTrue(self.validator.validate(controls))
        
    def test_power_with_zero_authority_fails(self):
        """Test that power command with zero authority is rejected."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=30.0,
            driver_velocity=30.0,
            emergency_brake=False,
            service_brake=0,
            power_command=50000,  # Power with no authority
            commanded_authority=0,
            speed_limit=60.0
        )
        self.assertFalse(self.validator.validate(controls))
        
    def test_zero_power_with_zero_authority_passes(self):
        """Test that zero power with zero authority passes."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=0.0,
            driver_velocity=0.0,
            emergency_brake=False,
            service_brake=0,
            power_command=0,  # No power, no authority OK
            commanded_authority=0,
            speed_limit=60.0
        )
        self.assertTrue(self.validator.validate(controls))


class TestVitalValidatorSecondCheck(unittest.TestCase):
    """Test cases for vital_validator_second_check (soft rules with margin)."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = vital_validator_second_check()
        
    def test_speed_within_margin_passes(self):
        """Test that speed within 2% margin passes."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=60.5,  # 60 * 1.008 (within 2% margin)
            driver_velocity=60.5,
            emergency_brake=False,
            service_brake=0,
            power_command=50000,
            commanded_authority=100,
            speed_limit=60.0
        )
        self.assertTrue(self.validator.validate(controls))
        
    def test_speed_exceeds_margin_fails(self):
        """Test that speed exceeding 2% margin is rejected."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=61.5,  # 60 * 1.025 (exceeds 2% margin)
            driver_velocity=61.5,
            emergency_brake=False,
            service_brake=0,
            power_command=50000,
            commanded_authority=100,
            speed_limit=60.0
        )
        self.assertFalse(self.validator.validate(controls))
        
    def test_both_brakes_still_fails(self):
        """Test that both brakes active fails in second check too."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=30.0,
            driver_velocity=30.0,
            emergency_brake=True,
            service_brake=100,
            power_command=0,
            commanded_authority=100,
            speed_limit=60.0
        )
        self.assertFalse(self.validator.validate(controls))
        
    def test_power_with_zero_authority_still_fails(self):
        """Test that power with zero authority fails in second check too."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=30.0,
            driver_velocity=30.0,
            emergency_brake=False,
            service_brake=0,
            power_command=50000,
            commanded_authority=0,
            speed_limit=60.0
        )
        self.assertFalse(self.validator.validate(controls))


class TestTrainControllerVitalValidation(unittest.TestCase):
    """Integration tests for train_controller vital validation flow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.api = train_controller_api()
        self.controller = train_controller(self.api)
        
        # Set initial state
        self.api.update_state({
            'speed_limit': 60.0,
            'commanded_speed': 50.0,
            'commanded_authority': 100,
            'train_velocity': 30.0,
            'driver_velocity': 30.0,
            'emergency_brake': False,
            'service_brake': 0,
            'power_command': 0
        })
        
    def test_valid_speed_change_accepted(self):
        """Test that valid speed change is accepted."""
        result = self.controller.vital_control_check_and_update({
            'driver_velocity': 40.0,
            'train_velocity': 40.0
        })
        self.assertTrue(result)
        state = self.api.get_state()
        self.assertEqual(state['driver_velocity'], 40.0)
        
    def test_excessive_speed_rejected(self):
        """Test that excessive speed is rejected and state unchanged."""
        original_state = self.api.get_state().copy()
        result = self.controller.vital_control_check_and_update({
            'train_velocity': 80.0  # Exceeds limit
        })
        self.assertFalse(result)
        # Verify state unchanged
        new_state = self.api.get_state()
        self.assertEqual(new_state['train_velocity'], original_state['train_velocity'])
        
    def test_excessive_power_rejected(self):
        """Test that excessive power is rejected."""
        result = self.controller.vital_control_check_and_update({
            'power_command': 150000  # Exceeds 120kW
        })
        self.assertFalse(result)
        state = self.api.get_state()
        self.assertNotEqual(state['power_command'], 150000)
        
    def test_both_brakes_rejected(self):
        """Test that both brakes active is rejected."""
        result = self.controller.vital_control_check_and_update({
            'emergency_brake': True,
            'service_brake': 100
        })
        self.assertFalse(result)
        
    def test_emergency_brake_accepted(self):
        """Test that emergency brake alone is accepted."""
        result = self.controller.vital_control_check_and_update({
            'emergency_brake': True,
            'service_brake': 0,
            'power_command': 0,
            'driver_velocity': 0
        })
        self.assertTrue(result)
        state = self.api.get_state()
        self.assertTrue(state['emergency_brake'])
        
    def test_power_without_authority_rejected(self):
        """Test that power command without authority is rejected."""
        self.api.update_state({'commanded_authority': 0})
        result = self.controller.vital_control_check_and_update({
            'power_command': 50000
        })
        self.assertFalse(result)
        
    def test_multiple_validators_must_all_pass(self):
        """Test that change must pass ALL validators."""
        # This speed is within first check but exceeds second check margin
        result = self.controller.vital_control_check_and_update({
            'train_velocity': 61.5  # 60 * 1.025
        })
        self.assertFalse(result)


class TestVitalValidationEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator_first = vital_validator_first_check()
        self.validator_second = vital_validator_second_check()
        
    def test_zero_speed_limit_handled(self):
        """Test handling of zero speed limit."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=0.0,
            driver_velocity=0.0,
            emergency_brake=False,
            service_brake=0,
            power_command=0,
            commanded_authority=100,
            speed_limit=0.0
        )
        self.assertTrue(self.validator_first.validate(controls))
        
    def test_exact_margin_boundary(self):
        """Test behavior exactly at 2% margin boundary."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=61.2,  # Exactly 60 * 1.02
            driver_velocity=61.2,
            emergency_brake=False,
            service_brake=0,
            power_command=50000,
            commanded_authority=100,
            speed_limit=60.0
        )
        # Should pass first check (61.2 < 60 is false, but 61.2 <= 60*1.02 is true)
        # At exactly 1.02x, second check should accept (<=, not <)
        result = self.validator_second.validate(controls)
        self.assertTrue(result)
        
    def test_very_small_authority_with_power(self):
        """Test small but non-zero authority allows power."""
        controls = vital_train_controls(
            kp=10.0,
            ki=0.5,
            train_velocity=30.0,
            driver_velocity=30.0,
            emergency_brake=False,
            service_brake=0,
            power_command=50000,
            commanded_authority=0.1,  # Very small but > 0
            speed_limit=60.0
        )
        self.assertTrue(self.validator_first.validate(controls))


def run_verbose_tests():
    """Run tests with verbose output showing each test result."""
    print("\n" + "="*70)
    print("VITAL VALIDATION TEST SUITE")
    print("="*70 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestVitalValidatorFirstCheck))
    suite.addTests(loader.loadTestsFromTestCase(TestVitalValidatorSecondCheck))
    suite.addTests(loader.loadTestsFromTestCase(TestTrainControllerVitalValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestVitalValidationEdgeCases))
    
    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    print("="*70 + "\n")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    # Run tests with verbose output
    success = run_verbose_tests()
    sys.exit(0 if success else 1)
