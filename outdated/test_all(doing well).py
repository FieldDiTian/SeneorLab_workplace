#!/usr/bin/env python3
"""
全部10轴顺序运动测试脚本

此脚本会轮流驱动所有10个轴（XYZ、UVW、IJK和E），按照设定的顺序和距离运动。
每个轴运动完成后会等待指定的时间，然后移动下一个轴。
完成一个完整循环后结束运行。
"""

from motorcontroller import MotorController
import time
import serial

# ========== 用户配置参数 ==========
# 每个轴的运动距离（毫米）
# XYZ - 基本轴
X_DISTANCE = -100    # X轴移动距离
Y_DISTANCE = -100    # Y轴移动距离
Z_DISTANCE = -50     # Z轴移动距离

# UVW - 额外轴组1
U_DISTANCE = -10    # U轴移动距离
V_DISTANCE = -10    # V轴移动距离
W_DISTANCE = -50     # W轴移动距离

# IJK - 额外轴组2
I_DISTANCE = -100    # I轴移动距离
J_DISTANCE = -100    # J轴移动距离
K_DISTANCE = -50     # K轴移动距离

# E - 挤出机轴
E_DISTANCE = 5     # 挤出机轴移动距离

# 运动速度（毫米/分钟）
FEEDRATE = 1000    # 默认速度

# 每次移动后的等待时间（秒）
WAIT_TIME = 2      # 电机移动间的等待时间

# 是否使用相对定位模式（True）或绝对定位模式（False）
USE_RELATIVE_MODE = True

# 循环次数 - 始终为1，只运行一次
LOOP_COUNT = 1

# 不返回原点
RETURN_TO_ORIGIN = False

# ================================

def print_header():
    """打印脚本头信息"""
    print("\n" + "=" * 60)
    print("十轴顺序运动测试")
    print("=" * 60)
    print("主要轴 (XYZ):")
    print(f"  X轴移动: {X_DISTANCE}mm, Y轴移动: {Y_DISTANCE}mm, Z轴移动: {Z_DISTANCE}mm")
    print("额外轴组1 (UVW):")
    print(f"  U轴移动: {U_DISTANCE}mm, V轴移动: {V_DISTANCE}mm, W轴移动: {W_DISTANCE}mm")
    print("额外轴组2 (IJK):")
    print(f"  I轴移动: {I_DISTANCE}mm, J轴移动: {J_DISTANCE}mm, K轴移动: {K_DISTANCE}mm")
    print("挤出机轴 (E):")
    print(f"  E轴移动: {E_DISTANCE}mm")
    print(f"运动速度: {FEEDRATE}mm/min, 等待时间: {WAIT_TIME}秒")
    print(f"定位模式: {'相对定位' if USE_RELATIVE_MODE else '绝对定位'}")
    print(f"循环次数: {LOOP_COUNT}")
    print(f"循环后返回原点: {'是' if RETURN_TO_ORIGIN else '否'}")
    print("=" * 60 + "\n")

def main():
    """主函数"""
    print_header()
    
    try:
        # 初始化控制器
        print("正在连接到控制板...")
        mc = MotorController(port=None, auto_enable=True)
        time.sleep(1)
        
        # 确保通信正常
        print("\n验证通信...")
        mc.send_gcode("M115")  # 获取固件信息
        time.sleep(0.5)
        
        # 保存初始位置
        print("获取初始位置...")
        initial_position = mc.get_position()
        print(f"初始位置: X={initial_position.get('X', 0)}, "
              f"Y={initial_position.get('Y', 0)}, "
              f"Z={initial_position.get('Z', 0)}")
        
        # 设置定位模式
        if USE_RELATIVE_MODE:
            print("\n设置相对定位模式...")
            mc.set_relative_positioning()
        else:
            print("\n设置绝对定位模式...")
            mc.set_absolute_positioning()
        
        # 开始循环移动
        loop = 0
        try:
            while LOOP_COUNT < 0 or loop < LOOP_COUNT:
                loop += 1
                print(f"\n===== 开始循环 {loop} {'(最后一次)' if loop == LOOP_COUNT else ''} =====")
                
                # ===== 主要轴 (XYZ) =====
                print("\n----- 开始移动主要轴 (XYZ) -----")
                
                # X轴移动
                print(f"\n移动X轴 {X_DISTANCE}mm...")
                if USE_RELATIVE_MODE:
                    mc.move_to(x=X_DISTANCE, feedrate=FEEDRATE)
                else:
                    current_pos = mc.get_position()
                    mc.move_to(x=current_pos['X'] + X_DISTANCE, feedrate=FEEDRATE)
                mc.send_gcode("M400")  # 等待移动完成
                position = mc.get_position()
                print(f"当前位置: X={position.get('X', 0)}")
                print(f"等待 {WAIT_TIME} 秒...")
                time.sleep(WAIT_TIME)
                
                # Y轴移动
                print(f"\n移动Y轴 {Y_DISTANCE}mm...")
                if USE_RELATIVE_MODE:
                    mc.move_to(y=Y_DISTANCE, feedrate=FEEDRATE)
                else:
                    current_pos = mc.get_position()
                    mc.move_to(y=current_pos['Y'] + Y_DISTANCE, feedrate=FEEDRATE)
                mc.send_gcode("M400")  # 等待移动完成
                position = mc.get_position()
                print(f"当前位置: Y={position.get('Y', 0)}")
                print(f"等待 {WAIT_TIME} 秒...")
                time.sleep(WAIT_TIME)
                
                # Z轴移动
                print(f"\n移动Z轴 {Z_DISTANCE}mm...")
                if USE_RELATIVE_MODE:
                    mc.move_to(z=Z_DISTANCE, feedrate=FEEDRATE)
                else:
                    current_pos = mc.get_position()
                    mc.move_to(z=current_pos['Z'] + Z_DISTANCE, feedrate=FEEDRATE)
                mc.send_gcode("M400")  # 等待移动完成
                position = mc.get_position()
                print(f"当前位置: Z={position.get('Z', 0)}")
                print(f"等待 {WAIT_TIME} 秒...")
                time.sleep(WAIT_TIME)

                # ===== 额外轴组1 (UVW) =====
                print("\n----- 开始移动额外轴组1 (UVW) -----")
                
                # U轴移动
                print(f"\n移动U轴 {U_DISTANCE}mm...")
                if USE_RELATIVE_MODE:
                    mc.move_to(u=U_DISTANCE, feedrate=FEEDRATE)
                else:
                    current_pos = mc.get_position()
                    mc.move_to(u=current_pos['U'] + U_DISTANCE, feedrate=FEEDRATE)
                mc.send_gcode("M400")  # 等待移动完成
                position = mc.get_position()
                print(f"当前位置: U={position.get('U', 0)}")
                print(f"等待 {WAIT_TIME} 秒...")
                time.sleep(WAIT_TIME)
                
                # V轴移动
                print(f"\n移动V轴 {V_DISTANCE}mm...")
                if USE_RELATIVE_MODE:
                    mc.move_to(v=V_DISTANCE, feedrate=FEEDRATE)
                else:
                    current_pos = mc.get_position()
                    mc.move_to(v=current_pos['V'] + V_DISTANCE, feedrate=FEEDRATE)
                mc.send_gcode("M400")  # 等待移动完成
                position = mc.get_position()
                print(f"当前位置: V={position.get('V', 0)}")
                print(f"等待 {WAIT_TIME} 秒...")
                time.sleep(WAIT_TIME)
                
                # W轴移动
                print(f"\n移动W轴 {W_DISTANCE}mm...")
                if USE_RELATIVE_MODE:
                    mc.move_to(w=W_DISTANCE, feedrate=FEEDRATE)
                else:
                    current_pos = mc.get_position()
                    mc.move_to(w=current_pos['W'] + W_DISTANCE, feedrate=FEEDRATE)
                mc.send_gcode("M400")  # 等待移动完成
                position = mc.get_position()
                print(f"当前位置: W={position.get('W', 0)}")
                print(f"等待 {WAIT_TIME} 秒...")
                time.sleep(WAIT_TIME)

                # ===== 额外轴组2 (IJK) =====
                print("\n----- 开始移动额外轴组2 (IJK) -----")
                
                # I轴移动
                print(f"\n移动I轴 {I_DISTANCE}mm...")
                if USE_RELATIVE_MODE:
                    mc.move_to(i=I_DISTANCE, feedrate=FEEDRATE)
                else:
                    current_pos = mc.get_position()
                    mc.move_to(i=current_pos['I'] + I_DISTANCE, feedrate=FEEDRATE)
                mc.send_gcode("M400")  # 等待移动完成
                position = mc.get_position()
                print(f"当前位置: I={position.get('I', 0)}")
                print(f"等待 {WAIT_TIME} 秒...")
                time.sleep(WAIT_TIME)
                
                # J轴移动
                print(f"\n移动J轴 {J_DISTANCE}mm...")
                if USE_RELATIVE_MODE:
                    mc.move_to(j=J_DISTANCE, feedrate=FEEDRATE)
                else:
                    current_pos = mc.get_position()
                    mc.move_to(j=current_pos['J'] + J_DISTANCE, feedrate=FEEDRATE)
                mc.send_gcode("M400")  # 等待移动完成
                position = mc.get_position()
                print(f"当前位置: J={position.get('J', 0)}")
                print(f"等待 {WAIT_TIME} 秒...")
                time.sleep(WAIT_TIME)
                
                # K轴移动
                print(f"\n移动K轴 {K_DISTANCE}mm...")
                if USE_RELATIVE_MODE:
                    mc.move_to(k=K_DISTANCE, feedrate=FEEDRATE)
                else:
                    current_pos = mc.get_position()
                    mc.move_to(k=current_pos['K'] + K_DISTANCE, feedrate=FEEDRATE)
                mc.send_gcode("M400")  # 等待移动完成
                position = mc.get_position()
                print(f"当前位置: K={position.get('K', 0)}")
                print(f"等待 {WAIT_TIME} 秒...")
                time.sleep(WAIT_TIME)
                
                # ===== 挤出机轴 (E) =====
                print("\n----- 开始移动挤出机轴 (E) -----")
                
                # 首先选择挤出机0
                print("选择挤出机0...")
                mc.select_extruder(0)
                time.sleep(0.5)
                
                # E轴移动
                print(f"\n移动E轴 {E_DISTANCE}mm...")
                if USE_RELATIVE_MODE:
                    # 确保挤出机使用相对模式
                    mc.send_gcode("M83")  # 设置挤出机为相对模式
                    time.sleep(0.5)
                    mc.move_to(e=E_DISTANCE, feedrate=FEEDRATE)
                else:
                    current_pos = mc.get_position()
                    # 确保挤出机使用绝对模式
                    mc.send_gcode("M82")  # 设置挤出机为绝对模式
                    time.sleep(0.5)
                    mc.move_to(e=current_pos['E'] + E_DISTANCE, feedrate=FEEDRATE)
                mc.send_gcode("M400")  # 等待移动完成
                position = mc.get_position()
                print(f"当前位置: E={position.get('E', 0)}")
                print(f"等待 {WAIT_TIME} 秒...")
                time.sleep(WAIT_TIME)
                
                # 不执行返回原点的代码，每个轴移动一次后结束程序
                print(f"\n===== 循环 {loop} 完成 =====")
                
                # 如果是无限循环，询问是否继续
                if LOOP_COUNT < 0 and loop % 3 == 0:  # 每3次循环询问一次
                    response = input("\n按 Enter 继续，输入 'q' 退出: ")
                    if response.lower() == 'q':
                        print("用户请求退出，停止循环")
                        break
        
        except KeyboardInterrupt:
            print("\n检测到键盘中断，停止循环")
        
        # 显示最终位置
        final_position = mc.get_position()
        print("\n最终位置:")
        print("主要轴 (XYZ):")
        print(f"  X: {final_position.get('X', 0)}")
        print(f"  Y: {final_position.get('Y', 0)}")
        print(f"  Z: {final_position.get('Z', 0)}")
        print("额外轴组1 (UVW):")
        print(f"  U: {final_position.get('U', 0)}")
        print(f"  V: {final_position.get('V', 0)}")
        print(f"  W: {final_position.get('W', 0)}")
        print("额外轴组2 (IJK):")
        print(f"  I: {final_position.get('I', 0)}")
        print(f"  J: {final_position.get('J', 0)}")
        print(f"  K: {final_position.get('K', 0)}")
        print("挤出机轴 (E):")
        print(f"  E: {final_position.get('E', 0)}")
    
    except serial.SerialException as e:
        print(f"\n串口通信错误: {e}")
        print("请检查设备连接和电源状态")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 确保关闭连接
        try:
            if 'mc' in locals():
                print("\n清理资源...")
                mc.disable_steppers()
                mc.close()
        except Exception as e:
            print(f"清理过程中出错: {e}")
            
    print("\n程序执行完毕")

if __name__ == "__main__":
    main()