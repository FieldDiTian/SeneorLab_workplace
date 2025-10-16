from motorcontroller import MotorController
import time

# 要移动的距离（毫米）。如需 100mm，改为 100
mm_distance = -1000
feedrate = 1200  # mm/min，线性轴安全值

# 使用默认参数创建控制器实例，自动启用步进电机
mc = MotorController()
try:

    # 计算步数（X轴 80 steps/mm）
    steps = int(round(mm_distance * mc.steps_per_mm['X']))

    print(f"\n[TEST] Move X +{mm_distance}mm")
    mc.move_motor_by_steps('X', steps, feedrate)
    mc.send_gcode("M400")  # 等待动作完成

    print(f"[TEST] Move X -{mm_distance}mm")
    mc.move_motor_by_steps('X', -steps, feedrate)
    mc.send_gcode("M400")

    pos = mc.get_position()
    print("\n[TEST] Final X position:", pos.get('X'))
finally:
    mc.disable_steppers()
    mc.close()