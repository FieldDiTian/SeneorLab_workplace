#!/usr/bin/env python3
"""
简化版电机控制器测试脚本

这个脚本展示了如何使用简化版的电机控制器，只包含单轴移动功能，
确保最大的兼容性和可靠性。
"""

from simple_motorcontroller import EnhancedMotorController
import time

def test_single_axes():
    """测试单轴移动"""
    print("\n===== 测试单轴移动 =====")
    
    # 测试X轴
    print("\n--- 测试X轴 ---")
    mc.move_x(-10)
    time.sleep(1)
    mc.move_x(10)  # 移回原位
    
    # 测试Y轴
    print("\n--- 测试Y轴 ---")
    mc.move_y(-10)
    time.sleep(1)
    mc.move_y(10)  # 移回原位
    
    # 测试Z轴
    print("\n--- 测试Z轴 ---")
    mc.move_z(-5)
    time.sleep(1)
    mc.move_z(5)  # 移回原位
    
    print("\n单轴基础测试完成")

def test_all_axes():
    """测试所有轴"""
    print("\n===== 测试所有轴 =====")
    
    axes = [
        {'name': 'X轴', 'method': mc.move_x, 'dist': -10},
        {'name': 'Y轴', 'method': mc.move_y, 'dist': -10},
        {'name': 'Z轴', 'method': mc.move_z, 'dist': -5},
        {'name': 'U轴', 'method': mc.move_u, 'dist': -5},
        {'name': 'V轴', 'method': mc.move_v, 'dist': -5},
        {'name': 'W轴', 'method': mc.move_w, 'dist': -5},
        {'name': 'I轴', 'method': mc.move_i, 'dist': -10},
        {'name': 'J轴', 'method': mc.move_j, 'dist': -10},
        {'name': 'K轴', 'method': mc.move_k, 'dist': -10},
        {'name': '挤出机(E)轴', 'method': mc.move_e, 'dist': 5}
    ]
    
    for axis in axes:
        print(f"\n--- 测试 {axis['name']} ---")
        axis['method'](axis['dist'])
        time.sleep(2)
        
        # 移回原位 (对挤出机特殊处理)
        if axis['name'] == '挤出机(E)轴':
            axis['method'](-axis['dist'])  # 挤出机反向移动
        else:
            axis['method'](-axis['dist'])  # 其他轴反向移动
        time.sleep(1)
    
    print("\n所有轴测试完成")

def run_predefined_sequence():
    """运行预定义的测试序列"""
    print("\n===== 运行完整测试序列 =====")
    
    # 使用默认参数运行全部轴测试
    mc.run_test_all()

if __name__ == "__main__":
    try:
        print("初始化简化版电机控制器...")
        mc = EnhancedMotorController()
        
        while True:
            print("\n" + "=" * 50)
            print("电机控制器测试菜单")
            print("=" * 50)
            print("1. 测试基础轴 (X, Y, Z)")
            print("2. 测试所有轴 (一次一个)")
            print("3. 运行完整测试序列")
            print("0. 退出")
            print("=" * 50)
            
            choice = input("\n请选择测试 [0-3]: ")
            
            if choice == "1":
                test_single_axes()
            elif choice == "2":
                test_all_axes()
            elif choice == "3":
                run_predefined_sequence()
            elif choice == "0":
                print("退出测试程序")
                break
            else:
                print("选择无效，请重试")
    
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'mc' in locals():
            print("\n清理资源...")
            mc.disable_steppers()
            mc.close()
    
    print("\n测试程序结束")