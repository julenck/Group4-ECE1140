# failure_test.py
from train_model_ui import TrainModel, DEFAULT_SPECS   # import your class

def show(title):
    print("\n" + "="*50)
    print(title)
    print("="*50)

def check(name, cond, detail=""):
    if cond:
        print(f"[PASS] {name}")
        return True
    print(f"[FAIL] {name}  {detail}")
    return False


# =====================================================
# 1. ENGINE FAILURE
# =====================================================
def test_engine_failure():
    show("ENGINE FAILURE TEST")

    m = TrainModel(DEFAULT_SPECS)
    m.velocity_mph = 10

    out = m.update(
        commanded_speed=40,
        commanded_authority=100,
        speed_limit=40,
        current_station="",
        next_station="",
        side_door="",
        power_command=50000,
        engine_failure=True,
        brake_failure=False,
        emergency_brake=False,
        service_brake=False
    )

    return check(
        "Engine failure stops propulsion",
        out["acceleration_ftps2"] <= 0.01,
        f"accel={out['acceleration_ftps2']}"
    )


# =====================================================
# 2. BRAKE FAILURE
# =====================================================
def test_brake_failure():
    show("BRAKE FAILURE TEST")

    m = TrainModel(DEFAULT_SPECS)
    m.velocity_mph = 20

    out = m.update(
        commanded_speed=0,
        commanded_authority=100,
        speed_limit=40,
        current_station="",
        next_station="",
        side_door="",
        power_command=0,
        engine_failure=False,
        brake_failure=True,
        emergency_brake=False,
        service_brake=True
    )

    return check(
        "Brake failure prevents service brake",
        abs(out["acceleration_ftps2"]) < 0.01,
        f"accel={out['acceleration_ftps2']}"
    )


# =====================================================
# 3. SIGNAL FAILURE  —— Should NOT affect physics
# =====================================================
def test_signal_failure():
    show("SIGNAL FAILURE TEST (physics unaffected)")

    # NO failure
    m1 = TrainModel(DEFAULT_SPECS)
    a1 = m1.update(
        commanded_speed=20,
        commanded_authority=100,
        speed_limit=40,
        current_station="",
        next_station="",
        side_door="",
        power_command=50000,
    )["acceleration_ftps2"]

    # SIGNAL FAILURE —— physics unaffected (handled externally)
    m2 = TrainModel(DEFAULT_SPECS)
    a2 = m2.update(
        commanded_speed=20,
        commanded_authority=100,
        speed_limit=40,
        current_station="",
        next_station="",
        side_door="",
        power_command=50000,
        brake_failure=False,
        engine_failure=False,
    )["acceleration_ftps2"]

    return check(
        "Signal failure does not change physics",
        abs(a1 - a2) < 0.0001,
        f"{a1} != {a2}"
    )


# =====================================================
# RUN ALL TESTS
# =====================================================
if __name__ == "__main__":
    results = [
        test_engine_failure(),
        test_brake_failure(),
        test_signal_failure(),
    ]
    print("\n====================")
    print(f"{results.count(True)} PASSED / {len(results)} TOTAL")
    print("====================")
