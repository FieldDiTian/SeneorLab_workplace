#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from statistics import mean

from motorcontroller import MotorController
from scale_reader   import open_scale, read_weight
from eis_module_updated  import main as run_eis  # Uncomment if EIS module is needed


def wait_for_stable_weight(window=3, threshold=0.001, timeout=6):
    """
    Ultra-fast weight stabilization checker using non-blocking reads.
    Uses serial.in_waiting to maximize response speed.
    """
    from statistics import mean
    import collections
    PORT_SCALE     = 'COM5'
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

def automated_pipeline(CONC_A, CONC_B, CONC_C):

    # —— Configurable Parameters —— #
    MOTOR_A        = 'X'     # Dispense Solution A NACL (-)
    MOTOR_B        = 'E0'     # Dispense Solution B KCL (-)
    MOTOR_C        = 'E2'     # Dispense Solution C (-)
    MOTOR_MIX      = 'E4'    # Mixing motor (bubbling) (+)
    MOTOR_EXTRACT  = 'E1'    # Extraction (+)
    MOTOR_WASH_IN  = 'E3'    # Wash-in （-）

    STEPS_PER_ML_A = -1345      # Motor steps per mL for A (X)
    STEPS_PER_ML_B = -1350       # Motor steps per mL for B (E0)
    STEPS_PER_ML_C = -1150       # Motor steps per mL for C (E2)
    STEPS_PER_ML_WATER = -10760

    # Chemistry parameters
    CONC_A_INIT    = 1250      # Initial concentration of A (mM)
    CONC_B_INIT    = 150      # Initial concentration of B (mM)
    CONC_C_INIT    = 687.5      # Initial concentration of C (mM)
    # Process parameters
    FINAL_VOLUME = 10.0
    VOLUME_A   = CONC_A * FINAL_VOLUME / CONC_A_INIT      # Pre-dispense A: a mL baseline
    print(f"Expected A weight: {VOLUME_A:.4f} g")
    VOLUME_B   = CONC_B * FINAL_VOLUME / CONC_B_INIT      # Pre-dispense B: b mL baseline
    print(f"Expected B weight: {VOLUME_B:.4f} g")
    VOLUME_C   = CONC_C * FINAL_VOLUME / CONC_C_INIT      # Pre-dispense B: b mL baseline
    print(f"Expected C weight: {VOLUME_C:.4f} g")
    BUBBLE_STEPS   = 300000   # Bubble/mix step count
    EXTRACT_STEPS  = 300000   # Extraction step count
    WASH_CYCLES    = 6        # Number of wash cycles
    WASH_VOLUME_ML = 10.0     # Volume per wash cycle (mL)

    PORT_MOTOR     = 'COM4'

    MAX_VOLUME = 30
    # —— End Config —— #

    motor     = MotorController(port=PORT_MOTOR)

    motor.enable_steppers()
    motor.set_absolute_positioning()
    motor.set_current_position(0, 0, 0, {f'E{i}': 0 for i in range(5)})
    motor.move_motor_by_steps(MOTOR_EXTRACT, 500000, 2000)
    
    # Step 1: Initial stable weight
    time.sleep(60)  
    print(">>> Measuring initial stable weight...")
    initial_weight = wait_for_stable_weight()
    MAX_VOLUME = MAX_VOLUME + initial_weight
    time.sleep(10)
    print(f"Initial weight: {initial_weight:.4f} g")

    # Step 2: Add Solution A
    print(">>> Dispensing Solution A")
    steps_A = int(VOLUME_A * STEPS_PER_ML_A)
    motor.move_motor_by_steps(MOTOR_A, steps_A, 2000)
    time.sleep(40)
    weight_after_A = wait_for_stable_weight()
    time.sleep(10)
    if weight_after_A >= MAX_VOLUME:
        print(">>> Extracting solution...")
        motor.move_motor_by_steps(MOTOR_EXTRACT, EXTRACT_STEPS, 500)
        return "Warning! Weight over max range!!"
    delta_A = weight_after_A - initial_weight
    print(f"[A] Current weight: {weight_after_A:.4f} g | Estimated volume: {delta_A:.2f} mL")

    # Step 3: Add Solution B
    print(">>> Dispensing Solution B")
    steps_B = int(VOLUME_B * STEPS_PER_ML_B)
    motor.move_motor_by_steps(MOTOR_B, steps_B, 500)
    time.sleep(40)
    weight_after_B = wait_for_stable_weight()
    time.sleep(5)
    if weight_after_B >= MAX_VOLUME:
        print(">>> Extracting solution...")
        motor.move_motor_by_steps(MOTOR_EXTRACT, EXTRACT_STEPS, 2000)
        return "Warning! Weight over max range!!"
    delta_B = weight_after_B - weight_after_A
    print(f"[B] Current weight: {weight_after_B:.4f} g | Incremental volume: {delta_B:.2f} mL")

    # Step 4: Add Solution C
    print(">>> Dispensing Solution C")
    steps_C = int(VOLUME_C * STEPS_PER_ML_C)
    motor.move_motor_by_steps(MOTOR_C, steps_C, 500)
    time.sleep(40)
    weight_after_C = wait_for_stable_weight()
    time.sleep(5)
    if weight_after_C >= MAX_VOLUME:
        print(">>> Extracting solution...")
        motor.move_motor_by_steps(MOTOR_EXTRACT, EXTRACT_STEPS, 2000)
        return "Warning! Weight over max range!!"
    delta_C = weight_after_C - weight_after_B
    print(f"[C] Current weight: {weight_after_C:.4f} g | Incremental volume: {delta_C:.2f} mL")
    
    # Step 5: Add Water and calculate the real concentration
    print(f">>> Adding water")
    VOLUME_WATER = FINAL_VOLUME - delta_A - delta_B - delta_C
    steps_water = int(VOLUME_WATER * STEPS_PER_ML_WATER)
    motor.move_motor_by_steps(MOTOR_WASH_IN, steps_water, 1000)
    print(f"    Wash-in finished!")
    
    time.sleep(60)
    total_weight = wait_for_stable_weight()
    time.sleep(5)
    if total_weight >= MAX_VOLUME:
        print(">>> Extracting solution...")
        motor.move_motor_by_steps(MOTOR_EXTRACT, EXTRACT_STEPS, 2000)
        return "Warning! Weight over max range!!"
    delta_Water = total_weight - weight_after_C
    print(f"[D] Current weight: {total_weight:.4f} g | Incremental volume: {delta_Water:.2f} mL")
    vol_A = weight_after_A - initial_weight
    vol_B = weight_after_B - weight_after_A
    vol_C = weight_after_C - weight_after_B
    total_volume = total_weight - initial_weight
    final_conc_A = (vol_A * CONC_A_INIT) / total_volume
    final_conc_B = (vol_B * CONC_B_INIT) / total_volume
    final_conc_C = (vol_C * CONC_C_INIT) / total_volume
    print(f"Total volume: {total_volume:.2f} mL | Final concentration of A: {final_conc_A:.4f} mM | Final concentration of B: {final_conc_B:.4f} mM | Final concentration of C: {final_conc_C:.4f} mM")

    # Step 6: Mixing
    motor.move_motor_by_steps(MOTOR_MIX, BUBBLE_STEPS, 2000)
    print(">>> Mixing...")
    time.sleep(40)

    # Step 7: EIS test (optional) 
    Z1 = run_eis(final_conc_A, final_conc_B, final_conc_C)
    print(">>> Running first EIS")
    
    # Step 8: Extract solution
    motor.move_motor_by_steps(MOTOR_EXTRACT, EXTRACT_STEPS, 2000)
    print(">>> Extracting solution...")
    time.sleep(20)
    post_extract_weight = wait_for_stable_weight()
    loss = total_weight - post_extract_weight
    print(f"Extracted volume: {loss:.2f} mL | Weight after extraction: {post_extract_weight:.4f} g")

    # Step 9: Wash cycles
    for i in range(WASH_CYCLES):
        
        steps_in = int((VOLUME_WATER + 2) * STEPS_PER_ML_WATER)
        motor.move_motor_by_steps(MOTOR_WASH_IN, steps_in, 1000)
        print(f"    Wash-out finished!")
        print(f">>> Wash cycle {i+1} - Injecting {WASH_VOLUME_ML+5} mL")
        time.sleep(1)
        
        motor.move_motor_by_steps(MOTOR_EXTRACT, EXTRACT_STEPS, 2000)
        print(f"    Wash-in finished!")
        print(f">>> Wash cycle {i+1} - Extracting")
        time.sleep(1)
        

    # Step 10: Second EIS test (optional)
    time.sleep(5)
    motor.move_motor_by_steps(MOTOR_WASH_IN, steps_water, 1000)
    print(f"    Wash-out finished! Now adding water for 2nd EIS")
    time.sleep(30)
    Z2 = run_eis(0, 0, 0)
    print(">>> Second EIS finished")
    time.sleep(10)

    motor.disable_steppers()
    motor.close()
    return ">>> Protocol complete."

if __name__ == "__main__":
    print(automated_pipeline(20, 4, 20.5))
