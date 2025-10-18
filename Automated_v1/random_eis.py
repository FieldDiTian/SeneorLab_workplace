#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import random
from statistics import mean

from motorcontroller import MotorController
from scale_reader   import open_scale, read_weight
from eis_module     import main as run_eis  # Uncomment if EIS module is needed

# —— Configurable Parameters —— #
MOTOR_MIX      = 'E3'    # Mixing (bubbling)
MOTOR_EXTRACT  = 'E1'    # Extraction
MOTOR_WASH_IN  = 'E2'    # Initial water injection
MOTOR_WASH_OUT = 'E1'    # Waste removal

MAX_WEIGHT     = 135     # Maximum total mass threshold (g)
MIXING_STEPS   = 200000
EXTRACT_STEPS  = 300000
ADDING_STEPS   = 150000
WASH_CYCLES    = 3
WASH_VOLUME_ML = 10.0

PORT_MOTOR     = 'COM4'
PORT_SCALE     = 'COM5'
# —— End Config —— #

# Solution concentrations (mol/L)
SOLUTION_CONCENTRATIONS = {
    'A': 0.5, #need set
    'B': 0.5, #need set
    'C': 0.5 #need set
}

# Motor assignment for each solution
SOLUTION_MOTORS = {
    'A': 'X',
    'B': 'Y',
    'C': 'E0'
}

# Steps for dispensing each solution
STEPS_PER_SOLUTION = {
    'A': 100,
    'B': 100,
    'C': -100
}

DENSITY = 1.0  # Assumed density in g/mL (water)

def steps_to_volume(steps, per_ml):
    return steps / per_ml

def wait_for_stable_weight(window=3, threshold=0.001, timeout=6):
    """
    Read the electronic scale until a stable weight is reached.
    Uses non-blocking serial read for fast convergence.
    """
    import collections
    weights = collections.deque(maxlen=window)
    start_time = time.time()
    ser = open_scale(port=PORT_SCALE, timeout=0.05)

    try:
        while True:
            if ser.in_waiting:
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
        print("\nInterrupted by user.")
    finally:
        ser.close()

def run_wash_cycle(motor):
    """
    Perform solution extraction and washing steps.
    """
    print(">>> Extracting solution...")
    total_weight = wait_for_stable_weight()
    motor.move_motor_by_steps(MOTOR_EXTRACT, EXTRACT_STEPS, 2000)
    time.sleep(2)
    post_extract_weight = wait_for_stable_weight()
    loss = total_weight - post_extract_weight
    print(f"Extracted volume: {loss:.2f} mL | Post-extraction weight: {post_extract_weight:.4f} g")

    for i in range(WASH_CYCLES):
        print(f">>> Wash cycle {i+1} - Injecting {WASH_VOLUME_ML} mL")
        steps_in = 150000
        motor.move_motor_by_steps(MOTOR_WASH_IN, steps_in,2500)
        time.sleep(1)
        print(f"    Wash-in complete.")

        print(f">>> Wash cycle {i+1} - Extracting")
        motor.move_motor_by_steps(MOTOR_WASH_OUT, EXTRACT_STEPS, 2000)
        time.sleep(1)
        print(f"    Wash-out complete.")

    print(">>> Running second EIS")
    #Z2 = run_eis()

def automated_pipeline():
    motor = MotorController(port=PORT_MOTOR)
    total_cycles = 20

    print(f">>> Prefilling system with water...")
    steps_in = 100000
    motor.move_motor_by_steps(MOTOR_WASH_IN, steps_in, 2500)
    time.sleep(5)

    initial_weight = wait_for_stable_weight()
    initial_volume = initial_weight / DENSITY
    total_volume = initial_volume
    total_moles = 0.0

    print(f"    Initial weight: {initial_weight:.4f} g")
    print(f"→ System initialized with {total_volume:.2f} mL pure solvent, 0 mol solute")

    for i in range(total_cycles):
        print("--------------- Cycle ", i + 1, " ---------------")
        motor.enable_steppers()
        motor.set_absolute_positioning()
        motor.set_current_position(0, 0, 0, {f'E{j}': 0 for j in range(5)})

        weight = wait_for_stable_weight()
        if weight >= MAX_WEIGHT:
            print(">>> Maximum weight reached. Performing wash cycle.")
            run_wash_cycle(motor)
            motor.move_motor_by_steps(MOTOR_WASH_IN, 50000, 2500) #need set corresponding to concentration we wanted
            weight = wait_for_stable_weight()
            total_volume = weight / DENSITY
            total_moles = 0.0
            print(f"→ Post-wash: Volume reset to {total_volume:.2f} mL, 0 mol solute")

        print(">>> Measuring weight before dispensing...")
        time.sleep(5)
        initial_weight = wait_for_stable_weight()
        print(f"Initial weight: {initial_weight:.4f} g")

        # Randomly select one solution to add
        selected_solution = random.choice(['A', 'B', 'C'])
        selected_motor = SOLUTION_MOTORS[selected_solution]
        selected_conc = SOLUTION_CONCENTRATIONS[selected_solution]
        steps = STEPS_PER_SOLUTION[selected_solution]

        print(f">>> Selected solution: {selected_solution} (motor: {selected_motor})")
        print(f"    Dispensing {steps} steps...")
        motor.move_motor_by_steps(selected_motor, steps)
        time.sleep(2)

        final_weight = wait_for_stable_weight()
        delta_mass = final_weight - initial_weight
        delta_volume = delta_mass / DENSITY
        added_moles = (selected_conc * delta_volume) / 1000

        total_volume += delta_volume
        total_moles += added_moles
        final_conc = total_moles / (total_volume / 1000) if total_volume > 0 else 0.0

        print(f"[{selected_solution}] Δmass: {delta_mass:.2f} g | Δvol: {delta_volume:.2f} mL | added mol: {added_moles:.5f} mol")
        print(f"→ Total volume: {total_volume:.2f} mL | Total mol: {total_moles:.5f} mol")
        print(f"→ Current concentration: {final_conc:.4f} M")

        print(">>> Mixing...")
        motor.move_motor_by_steps(MOTOR_MIX, MIXING_STEPS, 2000)
        time.sleep(5)

        print(">>> Running EIS (optional)")
        #Z1 = run_eis()

        print(">>> Cycle complete.")

    try:
        print("--------------- All", total_cycles, "cycles complete! ---------------")
    finally:
        motor.disable_steppers()
        motor.close()

if __name__ == "__main__":
    automated_pipeline()