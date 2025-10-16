from motorcontroller import MotorController
import time

#############################################
# 用户配置区 - 请在此处修改各轴移动距离(mm)和速度
# User Configuration Area - Modify axis movement distances(mm) and speed here
#############################################

# 移动距离配置 (负值表示反方向移动)
# Movement distance configuration (negative values indicate reverse direction)
axis_distances = {
    'X': -100,    # X轴移动距离(mm) / X-axis movement distance(mm)
    'Y': -100,    # Y轴移动距离(mm) / Y-axis movement distance(mm)
    'Z': -100,    # Z轴移动距离(mm) / Z-axis movement distance(mm)
    'U': -100,    # U轴移动距离(mm) / U-axis movement distance(mm)
    'V': -100,    # V轴移动距离(mm) / V-axis movement distance(mm)
}

# 通用配置 / General Configuration
feedrate = 1200  # 移动速度 (mm/min)，线性轴安全值 / Movement speed (mm/min), safe value for linear axes
wait_time = 5    # 各轴移动之间的等待时间(秒) / Wait time between axis movements (seconds)

#############################################
# 程序开始 / Program Start
#############################################

# 使用默认参数创建控制器实例，自动启用步进电机
# Create controller instance with default parameters, automatically enable steppers
mc = MotorController()
try:
    # 按顺序移动X、Y、Z、U、V五个轴
    # Move the five axes X, Y, Z, U, V in sequence
    axes_to_move = ['X', 'Y', 'Z', 'U', 'V']
    
    for axis in axes_to_move:
        # 获取当前轴的移动距离
        # Get the movement distance for the current axis
        distance = axis_distances[axis]
        
        # 计算步数 (距离 * 每毫米步数)
        # Calculate steps (distance * steps per mm)
        steps = int(round(distance * mc.steps_per_mm[axis]))
        
        # 移动当前轴
        # Move the current axis
        print(f"\n[TEST] 移动 {axis} 轴 {distance}mm / Moving {axis} axis {distance}mm")
        mc.move_motor_by_steps(axis, steps, feedrate)
        mc.send_gcode("M400")  # 等待动作完成 / Wait for completion
        print(f"{axis} 轴移动完成 / {axis} axis movement completed")
        
        # 如果不是最后一个轴，等待指定时间再移动下一个轴
        # If not the last axis, wait for the specified time before moving the next axis
        if axis != axes_to_move[-1]:
            print(f"等待{wait_time}秒... / Waiting                                                                            for {wait_time} seconds...")
            time.sleep(wait_time)
    
    # 显示所有轴的最终位置
    # Display final positions of all axes
    pos = mc.get_position()
    print("\n[TEST] 最终位置 / Final Position:")
    for axis in axes_to_move:
        print(f"{axis}: {pos.get(axis)}", end=", ")
    print()

finally:
    # 无论是否出现异常，确保关闭连接并禁用步进电机
    # Regardless of exceptions, ensure the connection is closed and steppers are disabled
    print("\n清理资源... / Cleaning up resources...")
    mc.disable_steppers()
    mc.close()