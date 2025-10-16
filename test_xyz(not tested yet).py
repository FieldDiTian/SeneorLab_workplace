from motorcontroller import MotorController
import time

# 使用默认参数创建控制器，自动启用步进电机
mc = MotorController()

try:
    # 要移动的距离（毫米）
    mm_distance = -100
    feedrate = 1200  # mm/min，线性轴安全值

    # X轴移动 -100mm
    print(f"\n[TEST] 移动 X 轴 {mm_distance}mm")
    x_steps = int(round(mm_distance * mc.steps_per_mm['X']))
    mc.move_motor_by_steps('X', x_steps, feedrate)
    mc.send_gcode("M400")  # 等待动作完成
    print(f"X轴移动完成，等待5秒...")
    time.sleep(5)  # 等待5秒
    
    # Y轴移动 -100mm
    print(f"\n[TEST] 移动 Y 轴 {mm_distance}mm")
    y_steps = int(round(mm_distance * mc.steps_per_mm['Y']))
    mc.move_motor_by_steps('Y', y_steps, feedrate)
    mc.send_gcode("M400")
    print(f"Y轴移动完成，等待5秒...")
    time.sleep(5)  # 等待5秒
    
    # Z轴移动 -100mm
    print(f"\n[TEST] 移动 Z 轴 {mm_distance}mm")
    z_steps = int(round(mm_distance * mc.steps_per_mm['Z']))
    mc.move_motor_by_steps('Z', z_steps, feedrate)
    mc.send_gcode("M400")
    print(f"Z轴移动完成")
    
    # 显示最终位置
    pos = mc.get_position()
    print("\n[TEST] 最终位置:")
    print(f"X: {pos.get('X')}, Y: {pos.get('Y')}, Z: {pos.get('Z')}")

finally:
    # 无论是否出现异常，确保关闭连接并禁用步进电机
    print("\n清理资源...")
    mc.disable_steppers()
    mc.close()