from motorcontroller import MotorController
import time
import serial

# 使用非常保守的测试距离
mm_distance = 100   # 使用 10mm 的小移动距离
feedrate = 500     # 使用非常保守的速度，提高稳定性

print("=== 开始测试，使用以下参数 ===")
print(f"移动距离: {mm_distance}mm, 速度: {feedrate}mm/min")

try:
    # 使用自动检测功能创建控制器实例，启用自动准备电机
    print("正在连接到控制板...")
    mc = MotorController(port=None, auto_enable=True)  # 自动检测可用串口，自动准备电机
    
    # 先测试通信是否正常
    print("\n测试通信...")
    mc.send_gcode("M115")  # 获取固件信息
    time.sleep(1)
    
    # 完全跳过步进电机启用，仅测试通信
    print("\n注意: 跳过步进电机启用步骤，仅测试串口通信")
    
    # 测试一些安全的查询命令
    try:
        print("获取固件信息...")
        mc.send_gcode("M115")  # 固件信息
        time.sleep(1)
        
        print("获取温度信息...")
        mc.send_gcode("M105")  # 获取温度
        time.sleep(1)
        
        # 设置绝对定位模式而不是相对定位
        print("设置绝对定位模式...")
        mc.send_gcode("G90")  # 绝对定位
        time.sleep(1)
    except Exception as e:
        print(f"警告: 初始命令失败: {e}")
        print("继续尝试后续测试...")
    
    # 获取当前位置
    print("\n获取当前位置...")
    init_pos = mc.get_position()
    print(f"初始位置: X={init_pos.get('X', 'unknown')}")
    
    # 确认设备通信正常
    print("\n发送测试命令...")
    mc.send_gcode("M115")  # 获取固件信息
    
    # 计算步数（X轴 80 steps/mm）
    steps = int(round(mm_distance * mc.steps_per_mm['X']))
    
    # 尝试一个微小的移动
    print("\n[TEST] 尝试小幅移动（1mm）...")
    
    try:
        # 获取端点状态
        print("获取端点状态...")
        mc.send_gcode("M119")  # 获取端点状态
        time.sleep(1)
        
        # 获取位置
        print("获取当前位置...")
        mc.send_gcode("M114")  # 获取位置
        time.sleep(1)
        
        # 设置相对定位
        print("设置相对定位模式...")
        mc.send_gcode("G91")
        time.sleep(1)
        
        # 尝试小幅移动 1mm
        print("尝试移动 X 轴 1mm...")
        tiny_steps = int(1 * mc.steps_per_mm['X'])
        mc.send_gcode(f"G1 X1 F200")  # 非常慢的速度
        time.sleep(2)
        mc.send_gcode("M400")  # 等待移动完成
        time.sleep(1)
        
        # 获取位置
        print("获取移动后位置...")
        mc.send_gcode("M114")
        time.sleep(1)
        
    except Exception as e:
        print(f"测试移动失败: {e}")
    
    # 获取中间位置
    mid_pos = mc.get_position()
    print(f"中间位置: X={mid_pos.get('X', 'unknown')}")
    
    # 尝试返回原位
    try:
        print("\n[TEST] 返回原位置...")
        mc.send_gcode("G1 X-1 F200")  # 非常慢的速度
        time.sleep(2)
        mc.send_gcode("M400")  # 等待移动完成
        time.sleep(1)
        
        # 恢复绝对定位
        print("恢复绝对定位模式...")
        mc.send_gcode("G90")
        time.sleep(1)
    except Exception as e:
        print(f"返回原位失败: {e}")
    
    # 获取最终位置
    final_pos = mc.get_position()
    print(f"\n[TEST] 最终位置: X={final_pos.get('X', 'unknown')}")

except serial.SerialException as e:
    print(f"\n串口通信错误: {e}")
    print("请检查设备连接和电源状态")
except Exception as e:
    print(f"\n测试过程中出现错误: {e}")
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
        
print("\n=== 测试完成 ===")