#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import sys
import os

# 尝试导入同目录下的模块
try:
    from motorcontroller import MotorController
    from scale_reader import open_scale, read_weight, wait_for_stable_weight
    # 如果需要EIS模块，取消下面的注释
    from eis_module import main as run_eis 
except ImportError as e:
    print(f"Import Error: {e}")
    print("Make sure motorcontroller.py, scale_reader.py, and eis_module.py are in the same folder.")
    sys.exit(1)

# ==========================================
#              CONFIG AREA
# ==========================================

# --- 1. Axis Mapping (Your 10-Axis Setup) ---
AXIS_MAP = {
    'NaCl':       'X',  # Solution A
    'KCl':        'Y',  # Solution B
    'Urea':       'Z',  # Solution C
    'Na_lactate': 'U',  # Solution D
    'NH4Cl':      'V',  # Solution E
    'CaCl2':      'W',  # Solution F
    'Glucose':    'I',  # Solution G
    
    'WATER':      'J',  # Water Pump
    'EXTRACT':    'K',  # Waste Pump
    'MIX':        'E',  # Air Mixing
}

# --- 2. Calibration ---
STEPS_PER_MM = 100.0  # Must match your motorcontroller settings

# Steps per mL (Negative if needed for direction)
STEPS_PER_ML = {
    'NaCl':       -1345,  # 实际标定值
    'KCl':        -1350,  # 实际标定值
    'Urea':       -1150,  # 实际标定值
    'Na_lactate': -1000,  # 待标定
    'NH4Cl':      -1000,  # 待标定
    'CaCl2':      -1000,  # 待标定
    'Glucose':    -1000,  # 待标定
    
    'WATER':      -10760, # 水泵
    'EXTRACT':    10000   # 废液泵
}

# --- 3. Speed (mm/min) ---
SPEED = {
    'DISPENSE': 2000,
    'WATER':    2500,
    'EXTRACT':  3000,
    'MIX':      2000
}

# --- 4. Experiment Parameters ---
CONFIG = {
    'MAX_WEIGHT_LIMIT': 135.0, # Scale safety limit (g)
    'FINAL_VOLUME':     20.0,  # Target volume (mL)
    'WASH_CYCLES':      3,     # Number of washes
    'WASH_VOLUME':      25.0,  # Wash volume (mL)
    'MIX_DURATION_MM':  2000,  # Mixing duration (mm distance)
    'EXTRACT_DIST_MM':  5000,  # Extraction distance (mm)
}

# 推荐的优化母液浓度 (mM)
CONC_INIT = {
    # --- 高浓度组 ---
    'NaCl':       1000.0,  # 方便计算 (是常见目标浓度10-90的10倍以上)
    'KCl':        100.0,   # 方便计算 (是常见目标浓度2-10的10倍以上)
    'Urea':       500.0,   # 方便计算 (是常见目标浓度5-40的10倍以上)
    'Na_lactate': 500.0,   # 方便计算 (是常见目标浓度5-40的10倍以上)
    # --- 低浓度组 (显著降低浓度以提高精度) ---
    'NH4Cl':      100.0,   # 从1000降至100, 稀释倍数从100倍降至10倍
    'CaCl2':      50.0,    # 从1000降至50, 稀释倍数从500-1000倍降至25-50倍
    'Glucose':    25.0     # 从1000降至25, 稀释倍数从2000倍降至50倍
}

# ==========================================
#              Helpers
# ==========================================

def ml_to_mm(ml, solution_type):
    steps_per_ml = STEPS_PER_ML.get(solution_type, 1000)
    total_steps = ml * steps_per_ml
    distance_mm = total_steps / STEPS_PER_MM
    return distance_mm

def move_smart(controller, axis_name, distance_mm, feedrate):
    """Dynamically calls move_x, move_y, etc."""
    method_name = f"move_{axis_name.lower()}"
    if hasattr(controller, method_name):
        func = getattr(controller, method_name)
        func(distance_mm, feedrate, wait=True)
    else:
        print(f"Error: Controller has no method {method_name}")

# ==========================================
#              Main Logic
# ==========================================

def automated_pipeline(target_concentrations):
    """
    Runs the full automated pipeline for a given set of target concentrations.

    Args:
        target_concentrations (dict): A dictionary mapping chemical names to target
                                      concentrations in mM. 
                                      e.g., {'NaCl': 10, 'KCl': 5, 'Urea': 20}
    """
    # Create a formatted string for the task title
    task_title = ", ".join([f"{name}={val}mM" for name, val in target_concentrations.items()])
    print("\n" + "="*60)
    print(f"Starting Task: {task_title}")
    print("="*60)

    try:
        motor = MotorController(auto_enable=True)
    except Exception as e:
        return f"Controller Error: {e}"

    try:
        # --- Volume Calculation ---
        volumes_to_dispense = {}
        plan_str_parts = []
        for name, target_conc in target_concentrations.items():
            if target_conc > 0 and name in CONC_INIT:
                volume = (target_conc * CONFIG['FINAL_VOLUME']) / CONC_INIT[name]
                volumes_to_dispense[name] = volume
                plan_str_parts.append(f"{name}={volume:.2f}mL")
        
        print("Plan: " + ", ".join(plan_str_parts))
        
        # 1. Empty & Tare
        print(">>> [1/7] Emptying Waste (Axis K)...")
        move_smart(motor, AXIS_MAP['EXTRACT'], CONFIG['EXTRACT_DIST_MM'], SPEED['EXTRACT'])
        
        print(">>> [2/7] Taring Scale...")
        time.sleep(2)
        initial_weight = wait_for_stable_weight()
        print(f"    Tare: {initial_weight:.4f} g")
        
        current_weight = initial_weight
        
        # --- Dynamic Dispensing Loop ---
        step_num = 3
        sorted_chemicals = [chem for chem in AXIS_MAP.keys() if chem in volumes_to_dispense]
        
        for name in sorted_chemicals:
            volume = volumes_to_dispense[name]
            print(f">>> [{step_num}/7] Adding {name} ({volume:.2f} mL)...")
            dist = ml_to_mm(volume, name)
            move_smart(motor, AXIS_MAP[name], dist, SPEED['DISPENSE'])
            time.sleep(1)
            current_weight = wait_for_stable_weight()
            if current_weight > CONFIG['MAX_WEIGHT_LIMIT']:
                raise ValueError(f"Scale Limit Exceeded after adding {name}!")
            step_num += 1

        # 5. Top up Water (Axis J)
        print(f">>> [{step_num}/7] Topping up with Water...")
        net_weight = current_weight - initial_weight
        # Assuming density is close to 1 g/mL for all solutions
        vol_water_needed = CONFIG['FINAL_VOLUME'] - net_weight
        
        if vol_water_needed > 0.1:
            print(f"    Adding Water ({vol_water_needed:.2f} mL)...")
            dist_water = ml_to_mm(vol_water_needed, 'WATER')
            move_smart(motor, AXIS_MAP['WATER'], dist_water, SPEED['WATER'])
            time.sleep(2)
            final_weight = wait_for_stable_weight()
            print(f"    Final Weight: {final_weight:.4f} g")
        else:
            print("    Water not needed.")
            final_weight = current_weight
        step_num += 1

        # 6. Mix (Axis E)
        print(f">>> [{step_num}/7] Mixing (Axis E)...")
        move_smart(motor, AXIS_MAP['MIX'], CONFIG['MIX_DURATION_MM'], SPEED['MIX'])
        time.sleep(2)
        step_num += 1

        # 7. EIS Test
        print(f">>> [{step_num}/7] Running EIS...")
        try:
            # Prepare arguments for run_eis, defaulting to 0
            eis_args = {
                'nacl': target_concentrations.get('NaCl', 0),
                'kcl': target_concentrations.get('KCl', 0),
                'urea': target_concentrations.get('Urea', 0),
                'na_lactate': target_concentrations.get('Na_lactate', 0),
                'nh4cl': target_concentrations.get('NH4Cl', 0),
                'cacl2': target_concentrations.get('CaCl2', 0),
                'glucose': target_concentrations.get('Glucose', 0),
            }
            run_eis(**eis_args)
            print("    EIS Done.")
        except Exception as e:
            print(f"    EIS Error: {e}")

        # 8. Wash Cycle
        print("\n>>> Washing...")
        for i in range(CONFIG['WASH_CYCLES']):
            print(f"    Cycle {i+1}")
            move_smart(motor, AXIS_MAP['EXTRACT'], CONFIG['EXTRACT_DIST_MM'], SPEED['EXTRACT']) # Empty
            dist_wash = ml_to_mm(CONFIG['WASH_VOLUME'], 'WATER')
            move_smart(motor, AXIS_MAP['WATER'], dist_wash, SPEED['WATER']) # Fill
            move_smart(motor, AXIS_MAP['MIX'], CONFIG['MIX_DURATION_MM'] / 2, SPEED['MIX']) # Mix
        
        print("    Final Drain...")
        move_smart(motor, AXIS_MAP['EXTRACT'], CONFIG['EXTRACT_DIST_MM'], SPEED['EXTRACT'])
        print(">>> Done.")

        return "Success"

    except Exception as e:
        print(f"\n!!! Error: {e}")
        return f"Error: {e}"
    finally:
        if 'motor' in locals():
            motor.disable_steppers()
            motor.close()

if __name__ == "__main__":
    # Example dictionary of target concentrations
    test_concentrations = {
        'NaCl': 20,
        'KCl': 4,
        'Urea': 20.5,
        'Na_lactate': 10
    }
    automated_pipeline(test_concentrations)