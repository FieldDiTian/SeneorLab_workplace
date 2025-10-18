#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from statistics import mean

from motorcontroller import MotorController
from scale_reader   import open_scale, read_weight
from eis_module     import main as run_eis  # Uncomment if EIS module is needed

# —— Configurable Parameters —— #
MOTOR_A        = 'X'     # Dispense Solution A (+)
MOTOR_B        = 'Y'     # Dispense Solution B (-)
MOTOR_MIX      = 'E2'    # Mixing motor (bubbling)
MOTOR_EXTRACT  = 'E1'    # Extraction (+)
MOTOR_WASH_IN  = 'E3'    # Wash-in （-）
MOTOR_WASH_OUT = 'E1'    # Wash-out (+)

STEPS_PER_ML_A = 35      # Motor steps per mL for A
STEPS_PER_ML_B = -950       # Motor steps per mL for B

PRE_ADD_ML_A   = 1.0     # Initial volume of A
MIXING_STEPS   = 200000
EXTRACT_STEPS  = 300000
ADDING_STEPS = -150000
WASH_CYCLES    = 3
WASH_VOLUME_ML = 10.0

CONC_A_INIT    = 1.0     # Initial concentration of A (M)

PORT_MOTOR     = 'COM4'
PORT_SCALE     = 'COM5'
# —— End Config —— #

def steps_to_volume(steps, per_ml):
    return steps / per_ml

def wait_for_stable_weight(window=3, threshold=0.001, timeout=6):
    """
    Ultra-fast weight stabilization checker using non-blocking reads.
    Uses serial.in_waiting to maximize response speed.
    """
    from statistics import mean
    import collections

    weights = collections.deque(maxlen=window)
    start_time = time.time()
    ser = open_scale(port=PORT_SCALE, timeout=0.05)

    try:
        while True:
            if ser.in_waiting:  # If there is data to be read by this port
                try:
                    w = read_weight(ser)
                    weights.append(w)
                    if len(weights) == window:
                        delta = max(weights) - min(weights)
                        if delta < threshold:
                            return mean(weights)
                except Exception as e:
                    print(f"[Warning] read failed: {e}")
            if time.time() - start_time > timeout:
                print()
                return mean(weights) if weights else 0.0
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nEnd by user.")
    finally:
        ser.close()

def automated_pipeline():
    motor     = MotorController(port=PORT_MOTOR)

    for i in range(1, 21):
        print("---------------This is Cycle ", i, " ---------------")
        motor.enable_steppers()
        motor.set_absolute_positioning()
        motor.set_current_position(0, 0, 0, {f'E{i}': 0 for i in range(5)})
        motor.move_motor_by_steps(MOTOR_WASH_OUT, EXTRACT_STEPS, 2000)
        # Step 1: Initial stable weight
        print(">>> Measuring initial stable weight...")
        time.sleep(5)  
        initial_weight = wait_for_stable_weight()
        print(f"Initial weight: {initial_weight:.4f} g")

        # Step 2: Add Solution A
        print(">>> Dispensing Solution A")
        steps_A = int(PRE_ADD_ML_A * STEPS_PER_ML_A)
        motor.move_motor_by_steps(MOTOR_A, -300)
        motor.move_motor_by_steps(MOTOR_A, 50)
        time.sleep(10)
        weight_after_A = wait_for_stable_weight()
        delta_A = weight_after_A - initial_weight
        print(f"[A] Current weight: {weight_after_A:.4f} g | Estimated volume: {delta_A:.2f} mL")

        # Step 3: Add Solution B and water in small increments, monitor for stabilization
        print(">>> Dispensing Solution B")
  

        motor.move_motor_by_steps(MOTOR_B, 300)
        motor.move_motor_by_steps(MOTOR_B, -50)
        time.sleep(10)
        stable_weight = wait_for_stable_weight()
        delta = stable_weight - weight_after_A
        print(f"[B] Current weight: {stable_weight:.4f} g | Incremental volume: {delta:.2f} mL")

        print(f">>> Adding water")
        steps_in = -50000
        motor.move_motor_by_steps(MOTOR_WASH_IN, steps_in)
        time.sleep(5)
        print(f"    Wash-in finished!")

        total_weight = wait_for_stable_weight()
        vol_A = weight_after_A - initial_weight
        vol_B = stable_weight - weight_after_A
        total_volume = total_weight
        final_conc = (vol_A * CONC_A_INIT) / total_volume
        print(f"Total volume: {total_volume:.2f} mL | Final concentration: {final_conc:.4f} M")

        # Step 4: Mixing
        print(">>> Mixing...")
        motor.move_motor_by_steps(MOTOR_MIX, MIXING_STEPS, 2000)
        time.sleep(5)

        # Step 5: EIS test (optional)
        print(">>> Running first EIS")
        #Z1 = run_eis()

        # Step 6: Extract solution
        print(">>> Extracting solution...")
        motor.move_motor_by_steps(MOTOR_EXTRACT, EXTRACT_STEPS, 2000)
        time.sleep(2)
        post_extract_weight = wait_for_stable_weight()
        loss = total_weight - post_extract_weight
        print(f"Extracted volume: {loss:.2f} mL | Weight after extraction: {post_extract_weight:.4f} g")

        # Step 7: Wash cycles
        for i in range(WASH_CYCLES):
            print(f">>> Wash cycle {i+1} - Injecting {WASH_VOLUME_ML} mL")
            steps_in = -150000
            motor.move_motor_by_steps(MOTOR_WASH_IN, steps_in)
            time.sleep(1)
            print(f"    Wash-in finished!")

            print(f">>> Wash cycle {i+1} - Extracting")
            motor.move_motor_by_steps(MOTOR_WASH_OUT, EXTRACT_STEPS, 2000)
            time.sleep(1)
            print(f"    Wash-out finished!")

        # Step 8: Second EIS test (optional)
        print(">>> Running second EIS")
        motor.move_motor_by_steps(MOTOR_WASH_IN, -100000)
        #Z2 = run_eis()
        #time.sleep(10)
        print(">>> Protocol complete.")
    try:
        print("---------------All 10 cycles complete!!---------------")
    finally:
        motor.disable_steppers()
        motor.close()

if __name__ == "__main__":
    automated_pipeline()
