#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
针管填充调试工具 / Syringe Refill Debug Tool

用于手动控制针管的吸水和排水操作
Used for manual control of syringe filling and draining operations
"""

import sys
import os
import threading
import time

sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
from motorcontroller import MotorController

# 轴映射
AXIS_MAP = {
    '1': ('X', 'NaCl'),
    '2': ('Y', 'KCl'),
    '3': ('Z', 'Urea'),
    '4': ('U', 'Na_lactate'),
    '5': ('V', 'NH4Cl'),
    '6': ('W', 'CaCl2'),
    '7': ('I', 'Glucose'),
    '8': ('J', 'Water'),
    '9': ('K', 'Extract'),
    '10': ('E', 'Air/Mix'),
}

STEP_INCREMENT = 100  # 每次移动的步数
FEEDRATE = 1500  # 速度 (步/分钟)

def print_menu():
    """显示针管选择菜单"""
    print("\n" + "=" * 60)
    print("针管填充调试工具 / Syringe Refill Debug Tool")
    print("=" * 60)
    print("请选择要操作的针管 / Please select syringe:")
    print()
    print("  1. X轴 - NaCl (氯化钠)")
    print("  2. Y轴 - KCl (氯化钾)")
    print("  3. Z轴 - Urea (尿素)")
    print("  4. U轴 - Na_lactate (乳酸钠)")
    print("  5. V轴 - NH4Cl (氯化铵)")
    print("  6. W轴 - CaCl2 (氯化钙)")
    print("  7. I轴 - Glucose (葡萄糖)")
    print("  8. J轴 - Water (水)")
    print("  9. K轴 - Extract (废液泵)")
    print(" 10. E轴 - Air/Mix (空气混合)")
    print()
    print("  0. 退出程序 / Exit")
    print("=" * 60)

def print_action_menu(axis_name, chemical_name):
    """显示操作选择菜单"""
    print("\n" + "-" * 60)
    print(f"当前选择 / Current Selection: {axis_name}轴 - {chemical_name}")
    print("-" * 60)
    print("操作选项 / Action Options:")
    print()
    print(f"  1. 后退 (+{STEP_INCREMENT}步) - 吸入液体 / Retract - Draw liquid")
    print(f"  2. 前进 (-{STEP_INCREMENT}步) - 排出液体 / Advance - Dispense liquid")
    print()
    print("  b. 返回针管选择 / Back to syringe selection")
    print("  0. 退出程序 / Exit")
    print("-" * 60)

def control_syringe(motor, axis, axis_name, chemical_name):
    """
    控制单个针管的吸入/排出
    
    Args:
        motor: 电机控制器实例
        axis: 轴标识符 ('X', 'Y', 'Z', etc.)
        axis_name: 轴名称（用于显示）
        chemical_name: 化学物质名称（用于显示）
    """
    total_steps = 0  # 累计步数
    stop_flag = False  # 停止标志
    
    def continuous_move(direction):
        """连续移动电机直到用户停止"""
        nonlocal total_steps, stop_flag
        
        steps = STEP_INCREMENT if direction == 'retract' else -STEP_INCREMENT
        move_count = 0
        
        # 计算预估移动时间
        estimated_time = abs(steps) / (FEEDRATE / 60.0)
        wait_time = estimated_time + 0.5  # 预估时间 + 0.5秒
        
        print(f"\n{'='*60}")
        print(f"电机开始连续移动 ({'+' if steps > 0 else ''}{steps}步/次)")
        print(f"每次等待: {wait_time:.2f}秒 (预估: {estimated_time:.2f}秒 + 0.5秒)")
        print(f"按 Enter 键停止 / Press Enter to STOP")
        print(f"{'='*60}\n")
        
        try:
            while not stop_flag:
                move_count += 1
                print(f"[{move_count}] 移动 {steps:+d}步... ", end='', flush=True)
                
                try:
                    # 发送G-code指令
                    motor.move_axis(axis, steps, FEEDRATE, wait=False)
                    total_steps += steps
                    
                    # 等待预估时间 + 0.5秒
                    time.sleep(wait_time)
                    print(f"✓ (累计: {total_steps:+d}步)")
                    
                except Exception as e:
                    print(f"❌ 错误: {e}")
                    break
        
        except KeyboardInterrupt:
            print("\n检测到中断...")
        
        finally:
            print(f"\n{'='*60}")
            print(f"电机已停止")
            print(f"本次累计移动: {total_steps:+d}步 (共{move_count}次)")
            print(f"{'='*60}")
    
    while True:
        print_action_menu(axis_name, chemical_name)
        print(f"历史累计移动 / Total movement: {total_steps:+d} 步 / steps")
        
        choice = input("\n请选择操作 / Select action: ").strip()
        
        if choice == '1':
            # 后退（吸入）- 连续移动
            stop_flag = False
            
            # 创建移动线程
            move_thread = threading.Thread(target=continuous_move, args=('retract',))
            move_thread.daemon = True
            move_thread.start()
            
            # 等待用户按Enter停止
            input()  # 阻塞直到用户按Enter
            stop_flag = True
            move_thread.join(timeout=2)  # 等待线程结束
        
        elif choice == '2':
            # 前进（排出）- 连续移动
            stop_flag = False
            
            # 创建移动线程
            move_thread = threading.Thread(target=continuous_move, args=('advance',))
            move_thread.daemon = True
            move_thread.start()
            
            # 等待用户按Enter停止
            input()  # 阻塞直到用户按Enter
            stop_flag = True
            move_thread.join(timeout=2)  # 等待线程结束
        
        elif choice.lower() == 'b':
            # 返回上一级菜单
            print(f"\n返回针管选择菜单...")
            print(f"本次{axis_name}轴总移动: {total_steps:+d}步")
            break
        
        elif choice == '0':
            # 退出程序
            print(f"\n本次{axis_name}轴总移动: {total_steps:+d}步")
            return False  # 返回False表示退出整个程序
        
        else:
            print("❌ 无效选择，请重新输入")
    
    return True  # 返回True表示继续

def main():
    """主函数"""
    print("\n正在连接电机控制器...")
    
    try:
        motor = MotorController(port='COM8', auto_enable=True)
        print("✓ 电机控制器连接成功！")
    except Exception as e:
        print(f"❌ 无法连接电机控制器: {e}")
        print("请检查：")
        print("  1. Marlin控制板是否已连接到COM8")
        print("  2. 串口是否被其他程序占用")
        return
    
    try:
        while True:
            print_menu()
            choice = input("\n请选择针管编号 / Select syringe number: ").strip()
            
            if choice == '0':
                print("\n退出程序...")
                break
            
            if choice not in AXIS_MAP:
                print("❌ 无效选择，请输入0-10之间的数字")
                continue
            
            # 获取轴信息
            axis, chemical_name = AXIS_MAP[choice]
            axis_name = axis
            
            # 进入针管操作模式
            continue_program = control_syringe(motor, axis, axis_name, chemical_name)
            
            if not continue_program:
                # 用户选择退出
                break
    
    except KeyboardInterrupt:
        print("\n\n检测到 Ctrl+C，程序中断")
    
    finally:
        # 关闭电机
        print("\n正在禁用步进电机...")
        motor.disable_steppers()
        motor.close()
        print("✓ 程序已安全退出")

if __name__ == "__main__":
    main()
