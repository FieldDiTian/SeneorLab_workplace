# Octopus 控制器使用文档

## MotorController 类

本文档详细介绍了 `motorcontroller.py` 中 `MotorController` 类的所有功能和使用方法。该类用于通过串行通信控制 Octopus 控制板上的步进电机。

### 初始化

```python
mc = MotorController(port=None, baudrate=115200, auto_enable=True)
```

#### 参数说明

- `port`: 串口设备路径，如果设为 `None`，则自动检测可用串口
- `baudrate`: 通信波特率，默认为 115200
- `auto_enable`: 是否在初始化时自动准备步进电机，默认为 True

#### 示例

```python
# 自动检测串口并初始化控制器
mc = MotorController()

# 指定串口
mc = MotorController(port='/dev/tty.usbmodem123456')

# 不自动准备电机
mc = MotorController(auto_enable=False)
```

### 电机控制函数

#### prepare_motors()

准备步进电机状态。此方法获取当前状态信息、位置，并设置为绝对定位模式。

```python
mc.prepare_motors()
```

#### disable_steppers()

禁用所有步进电机以节省能源和减少热量，发送 M18 或 M84 命令。

```python
mc.disable_steppers()
```

#### set_absolute_positioning()

将控制器设置为绝对定位模式（G90 命令）。

```python
mc.set_absolute_positioning()
```

#### set_relative_positioning()

将控制器设置为相对定位模式（G91 命令）。

```python
mc.set_relative_positioning()
```

#### set_current_position()

设置所有轴的当前位置坐标（G92 命令）。

```python
# 将所有轴设置为原点
mc.set_current_position(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

# 仅设置 X 和 Y 轴
mc.set_current_position(x=10, y=20)
```

#### get_position()

获取所有轴的当前位置信息（M114 命令）。

```python
position = mc.get_position()
print(f"X 轴位置: {position['X']}")
```

#### select_extruder()

选择挤出机工具（T 命令）。

```python
# 选择第一个挤出机（单挤出机系统）
mc.select_extruder(0)
```

#### move_motor_by_steps()

通过步数移动指定的电机。

```python
# 参数: 电机名称, 步数, 速度(mm/min)
mc.move_motor_by_steps('X', 800, 1000)  # X 轴移动 800 步，速度 1000mm/min
```

支持的电机名称：'X', 'Y', 'Z', 'I', 'J', 'K', 'U', 'V', 'W', 'E'

#### move_to()

移动到指定的绝对坐标位置。

```python
# 参数: 各轴坐标, 速度(mm/min)
mc.move_to(x=100, y=50, z=10, feedrate=2000)
```

#### home()

使用 G28 命令归位指定的轴。

```python
# 归位所有已配置的轴
mc.home()

# 仅归位特定轴
mc.home(['X', 'Y'])

# 不等待归位完成
mc.home(['Z'], wait=False)
```

#### home_xyz()

归位 X、Y 和 Z 轴的快捷方法。

```python
mc.home_xyz()
```

#### home_all_linear()

归位所有 9 个线性轴（如果已配置端点）的快捷方法。

```python
mc.home_all_linear()
```

#### zero_extruder()

将挤出机位置设置为 0（无需归位，因为挤出机通常没有端点开关）。

```python
mc.zero_extruder()
```

### 通信函数

#### send_gcode()

发送 G 代码命令到控制板。

```python
response = mc.send_gcode("M114")  # 获取位置
```

#### close()

关闭串口连接。

```python
mc.close()
```

### 内部辅助函数

以下函数主要在类内部使用：

- `_find_available_ports()`: 查找系统上可用的串口设备
- `_send_test_command()`: 发送测试命令确认通信正常
- `_reopen()`: 尝试重新打开串口连接

## 最佳实践

1. **始终使用 with 语句或 try-finally 块**：确保在使用完毕后正确关闭连接和禁用步进电机。

```python
try:
    mc = MotorController()
    # 执行电机控制操作
finally:
    mc.disable_steppers()
    mc.close()
```

2. **避免使用 M17 命令**：系统已经移除对 M17 命令的使用，因为它可能导致设备断连。

3. **使用适当的延迟**：在发送命令后添加适当的延迟，特别是在移动操作后。

4. **错误处理**：为重要操作添加错误处理，以防连接丢失或命令失败。

## 常见错误和解决方案

- **设备断连**：如果设备突然断开连接，请检查电源情况，并确保没有发送 M17 命令。
- **电机不移动**：确保步进电机驱动器已通电，并检查端点开关状态（M119 命令）。
- **位置报告不准确**：尝试使用 `set_current_position()` 重置当前位置，然后再移动。

## 版本历史

- **2025-10-17**：移除了对 M17 命令的使用，用 prepare_motors() 方法替代 enable_steppers()，改进了错误处理。