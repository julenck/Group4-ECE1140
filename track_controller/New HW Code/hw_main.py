from time import sleep
from hw_display import hw_display
from hw_wayside_controller import hw_wayside_controller
from hw_wayside_controller_ui import hw_wayside_controller_ui

def main() -> None:
    display = hw_display()
    controller = hw_wayside_controller()
    ui = hw_wayside_controller_ui(controller, display)

    display.init()

    # seed blocks and states
    block_ids = [0, 1, 2, 3, 4, 5]
    controller.light_states = [0] * len(block_ids)
    controller.gate_states = [0] * len(block_ids)
    controller.switch_states = [0] * len(block_ids)
    display.update_blocks(block_ids)

    # Simulated updates (replace later with your runtime feed)
    ui.apply_vital_inputs(block_ids, {
        "emergency": False,
        "speed_mph": 40,
        "authority_yards": 520,
        "occupied_blocks": [2, 3],
    })
    sleep(0.8)
    ui.apply_vital_inputs(block_ids, {
        "emergency": True,
        "speed_mph": 18,
        "authority_yards": 200,
        "occupied_blocks": [3],
    })
    sleep(0.8)
    ui.apply_vital_inputs(block_ids, {
        "emergency": False,
        "speed_mph": 35,
        "authority_yards": 460,
        "occupied_blocks": [1, 4],
    })

    # keep window alive
    display.run_forever()

if __name__ == "__main__":
    main()
