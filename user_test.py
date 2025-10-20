#!/usr/bin/env python3
"""
简化版电机控制器测试脚本 / Simplified Motor Controller Test Script

这个脚本展示了如何使用简化版的电机控制器，只包含单轴移动功能，
确保最大的兼容性和可靠性。

This script demonstrates how to use the simplified motor controller with only 
single-axis movement functionality, ensuring maximum compatibility and reliability.
"""

from motorcontroller import MotorController
import time

def test_single_axes():
    """测试单轴移动 / Test single axis movement"""
    print("\n===== 测试单轴移动 / Test Single Axis Movement =====")
    
    # 测试X轴 / Test X-axis
    print("\n--- 测试X轴 / Test X-axis ---")
    mc.move_x(-10)
    time.sleep(1)
    mc.move_x(10)  # 移回原位 / Move back to origin
    
    # 测试Y轴 / Test Y-axis
    print("\n--- 测试Y轴 / Test Y-axis ---")
    mc.move_y(-10)
    time.sleep(1)
    mc.move_y(10)  # 移回原位 / Move back to origin
    
    # 测试Z轴 / Test Z-axis
    print("\n--- 测试Z轴 / Test Z-axis ---")
    mc.move_z(-5)
    time.sleep(1)
    mc.move_z(5)  # 移回原位 / Move back to origin
    
    print("\n单轴基础测试完成 / Single axis basic test completed")

def test_all_axes():
    """测试所有轴 / Test all axes"""
    print("\n===== 测试所有轴 / Test All Axes =====")
    
    axes = [
        {'name': 'X轴 / X-axis', 'method': mc.move_x, 'dist': -10},
        {'name': 'Y轴 / Y-axis', 'method': mc.move_y, 'dist': -10},
        {'name': 'Z轴 / Z-axis', 'method': mc.move_z, 'dist': -10},
        {'name': 'U轴 / U-axis', 'method': mc.move_u, 'dist': -10},
        {'name': 'V轴 / V-axis', 'method': mc.move_v, 'dist': -10},
        {'name': 'W轴 / W-axis', 'method': mc.move_w, 'dist': -10},
        {'name': 'I轴 / I-axis', 'method': mc.move_i, 'dist': -10},
        {'name': 'J轴 / J-axis', 'method': mc.move_j, 'dist': -10},
        {'name': 'K轴 / K-axis', 'method': mc.move_k, 'dist': -10},
        {'name': '挤出机(E)轴 / Extruder(E)-axis', 'method': mc.move_e, 'dist': -10}
    ]
    
    for axis in axes:
        print(f"\n--- 测试 / Testing {axis['name']} ---")
        axis['method'](axis['dist'])
        time.sleep(2)
        
        # 移回原位 (对挤出机特殊处理) / Move back to origin (special handling for extruder)
        if axis['name'] == '挤出机(E)轴 / Extruder(E)-axis':
            axis['method'](-axis['dist'])  # 挤出机反向移动 / Extruder reverse movement
        else:
            axis['method'](-axis['dist'])  # 其他轴反向移动 / Other axes reverse movement
        time.sleep(1)
    
    print("\n所有轴测试完成 / All axes test completed")

def run_predefined_sequence():
    """运行预定义的测试序列 / Run predefined test sequence"""
    print("\n===== 运行完整测试序列 / Running Complete Test Sequence =====")
    
    # 使用默认参数运行全部轴测试 / Run all axes test with default parameters
    mc.run_test_all()

if __name__ == "__main__":
    try:
        print("初始化简化版电机控制器... / Initializing Simplified Motor Controller...")
        mc = MotorController()
        
        while True:
            print("\n" + "=" * 50)
            print("电机控制器测试菜单 / Motor Controller Test Menu")
            print("=" * 50)
            print("1. 测试基础轴 (X, Y, Z) / Test Basic Axes (X, Y, Z)")
            print("2. 测试所有轴 (一次一个) / Test All Axes (One at a Time)")
            print("3. 运行完整测试序列 / Run Complete Test Sequence")
            print("0. 退出 / Exit")
            print("=" * 50)
            
            choice = input("\n请选择测试 / Please select test [0-3]: ")
            
            if choice == "1":
                test_single_axes()
            elif choice == "2":
                test_all_axes()
            elif choice == "3":
                run_predefined_sequence()
            elif choice == "0":
                print("退出测试程序 / Exiting test program")
                break
            else:
                print("选择无效，请重试 / Invalid selection, please try again")
    
    except KeyboardInterrupt:
        print("\n\n测试被用户中断 / Test interrupted by user")
    except Exception as e:
        print(f"\n发生错误 / Error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'mc' in locals():
            print("\n清理资源... / Cleaning up resources...")
            mc.disable_steppers()
            mc.close()
    
    print("\n测试程序结束 / Test program ended")