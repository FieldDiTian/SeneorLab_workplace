#!/usr/bin/env python3
"""
电机控制测试程序 / Motor Control Test Program
允许用户按需控制所有10个电机轴的运动
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

from motorcontroller import MotorController


def print_menu():
    """打印菜单"""
    print("\n" + "=" * 70)
    print("电机控制测试程序 / Motor Control Test Program")
    print("=" * 70)
    print("可用的电机轴 / Available Motor Axes:")
    print("  X - NaCl (氯化钠) 蠕动泵 1")
    print("  Y - KCl (氯化钾) 蠕动泵 2")
    print("  Z - Urea (尿素) 蠕动泵 3")
    print("  U - Na_lactate (乳酸钠) 蠕动泵 4")
    print("  V - NH4Cl (氯化铵) 蠕动泵 5")
    print("  W - CaCl2 (氯化钙) 蠕动泵 6")
    print("  I - Glucose (葡萄糖) 蠕动泵 7")
    print("  J - WATER (蒸馏水) 水泵")
    print("  K - EXTRACT (废液) 废液泵")
    print("  E - MIX (搅拌) 搅拌电机")
    print("\n特殊命令:")
    print("  A - 运行所有轴测试")
    print("  Q - 退出程序")
    print("=" * 70)


def get_steps():
    """获取步数输入"""
    try:
        steps = input("请输入步数 (正数前进，负数后退): ").strip()
        return float(steps)
    except ValueError:
        print("无效输入，请输入数字")
        return None
    except KeyboardInterrupt:
        print("\n操作取消")
        return None


def move_motor(controller, axis_name, axis_function, custom_feedrate=None):
    """移动电机"""
    print(f"\n--- 控制 {axis_name} ---")
    steps = get_steps()
    if steps is None:
        return
    
    feedrate = custom_feedrate if custom_feedrate else controller.default_feedrate
    
    try:
        print(f"执行移动：{axis_name} {steps}步 (速度: {feedrate}步/分钟)")
        axis_function(steps, feedrate=feedrate, wait=True)
        print(f"✓ {axis_name} 移动完成")
    except Exception as e:
        print(f"✗ 移动失败: {e}")


def run_all_test(controller):
    """运行所有轴测试"""
    print("\n运行所有轴测试...")
    params = {
        'x_dist': -100, 'y_dist': -100, 'z_dist': -50,
        'i_dist': -100, 'j_dist': -100, 'k_dist': -50,
        'u_dist': -10, 'v_dist': -10, 'w_dist': -50,
        'e_dist': 5, 'feedrate': 1000, 'wait_time': 2
    }
    
    confirm = input("是否继续? (y/n): ").strip().lower()
    if confirm != 'y':
        print("测试取消")
        return
    
    try:
        controller.run_test(**params)
        print("\n✓ 所有轴测试完成")
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")


def main():
    """主程序"""
    print("\n正在初始化电机控制器...")
    
    try:
        controller = MotorController(
            port='COM8',
            baudrate=115200,
            auto_enable=True,
            default_feedrate=1000,
            wait_time=0.5
        )
        
        print("\n✓ 电机控制器初始化成功")
        
        motors = {
            'X': ('X轴 - NaCl (氯化钠)', controller.move_x, None),
            'Y': ('Y轴 - KCl (氯化钾)', controller.move_y, None),
            'Z': ('Z轴 - Urea (尿素)', controller.move_z, None),
            'U': ('U轴 - Na_lactate (乳酸钠)', controller.move_u, None),
            'V': ('V轴 - NH4Cl (氯化铵)', controller.move_v, None),
            'W': ('W轴 - CaCl2 (氯化钙)', controller.move_w, None),
            'I': ('I轴 - Glucose (葡萄糖)', controller.move_i, None),
            'J': ('J轴 - WATER (蒸馏水)', controller.move_j, 3000),
            'K': ('K轴 - EXTRACT (废液)', controller.move_k, 3000),
            'E': ('E轴 - MIX (搅拌)', controller.move_e, 3000)
        }
        
        while True:
            print_menu()
            choice = input("\n请输入电机字母 (X/Y/Z/U/V/W/I/J/K/E) 或命令 (A/Q): ").strip().upper()
            
            if choice == 'Q':
                print("\n退出程序...")
                break
            elif choice == 'A':
                run_all_test(controller)
            elif choice in motors:
                axis_name, axis_function, custom_feedrate = motors[choice]
                move_motor(controller, axis_name, axis_function, custom_feedrate)
            else:
                print("无效选择，请重新输入")
        
    except KeyboardInterrupt:
        print("\n\n检测到键盘中断")
    except Exception as e:
        print(f"\n初始化失败: {e}")
        print("请检查设备连接和串口状态")
        return 1
    finally:
        try:
            if 'controller' in locals():
                controller.close()
                print("✓ 资源已释放")
        except:
            pass
    
    print("\n程序结束")
    return 0


if __name__ == "__main__":
    sys.exit(main())
