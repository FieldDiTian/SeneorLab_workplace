# 电机控制器使用说明 / Motor Controller User Guide

## 简介 / Introduction

**中文：**  
这是一个用于控制10轴步进电机的 Python 程序。它可以通过串口与控制板（使用 Marlin 固件）通信，控制 10 个独立的电机轴移动。程序包含两个主要文件：
- `motorcontroller.py`：核心控制库，包含所有控制功能
- `user_test.py`：测试脚本，提供简单的菜单界面供用户测试电机

**English:**  
This is a Python program for controlling 10-axis stepper motors. It communicates with a control board (running Marlin firmware) via serial port to control 10 independent motor axes. The program consists of two main files:
- `motorcontroller.py`: Core control library containing all control functions
- `user_test.py`: Test script providing a simple menu interface for testing motors

## 快速开始 / Quick Start

Use usb connect with board and Run user_test.py
---

## 主要功能说明 / Main Features

### MotorController 类 / MotorController Class

**中文：**  
`MotorController` 是核心控制类，提供以下主要功能：

**English:**  
`MotorController` is the core control class providing the following main features:

#### 1. 初始化连接 / Initialize Connection

**中文：**
- **功能**：自动检测并连接到控制板
- **使用方法**：
  ```python
  mc = MotorController()  # 自动检测串口
  # 或指定串口：mc = MotorController(port='/dev/ttyUSB0')
  ```
- **说明**：程序会自动搜索可用串口并连接，优先选择 USB 模块端口

**English:**
- **Function**: Automatically detect and connect to the control board
- **Usage**:
  ```python
  mc = MotorController()  # Auto-detect serial port
  # Or specify port: mc = MotorController(port='/dev/ttyUSB0')
  ```
- **Description**: The program will automatically search for available ports and connect, prioritizing USB module ports

---

#### 2. 发送 G-code 命令 / Send G-code Commands

**中文：**
- **功能**：向控制板发送标准 G-code 命令
- **使用方法**：
  ```python
  mc.send_gcode("G28")  # 回零命令
  mc.send_gcode("M115")  # 获取固件信息
  ```
- **说明**：这是与控制板通信的底层方法，支持所有标准 Marlin G-code 命令

**English:**
- **Function**: Send standard G-code commands to the control board
- **Usage**:
  ```python
  mc.send_gcode("G28")  # Home command
  mc.send_gcode("M115")  # Get firmware info
  ```
- **Description**: This is the low-level method for communicating with the board, supporting all standard Marlin G-code commands

---

#### 3. 单轴移动 / Single Axis Movement

**中文：**
- **功能**：控制单个轴移动指定距离（毫米）
- **可用轴**：X, Y, Z, U, V, W, I, J, K, E（挤出机）
- **使用方法**：
  ```python
  mc.move_x(10)      # X轴正向移动10毫米
  mc.move_y(-5)      # Y轴负向移动5毫米
  mc.move_z(2.5)     # Z轴正向移动2.5毫米
  mc.move_e(10)      # 挤出机移动10毫米
  ```
- **参数说明**：
  - `distance`：移动距离（毫米），正数为正向，负数为负向
  - `feedrate`（可选）：移动速度（毫米/分钟），默认 1000
  - `wait`（可选）：是否等待移动完成，默认 True

**English:**
- **Function**: Control a single axis to move a specified distance (millimeters)
- **Available axes**: X, Y, Z, U, V, W, I, J, K, E (extruder)
- **Usage**:
  ```python
  mc.move_x(10)      # Move X-axis forward 10mm
  mc.move_y(-5)      # Move Y-axis backward 5mm
  mc.move_z(2.5)     # Move Z-axis forward 2.5mm
  mc.move_e(10)      # Move extruder 10mm
  ```
- **Parameters**:
  - `distance`: Movement distance (mm), positive for forward, negative for backward
  - `feedrate` (optional): Movement speed (mm/min), default 1000
  - `wait` (optional): Whether to wait for movement to complete, default True

---

#### 4. 完整测试序列 / Full Test Sequence

**中文：**
- **功能**：按顺序测试所有 10 个轴
- **使用方法**：
  ```python
  mc.run_test_all()  # 使用默认参数
  # 或自定义参数：
  mc.run_test_all(x_dist=-100, y_dist=-100, feedrate=2000)
  ```
- **说明**：依次移动每个轴，适合初次测试或完整功能验证

**English:**
- **Function**: Test all 10 axes sequentially
- **Usage**:
  ```python
  mc.run_test_all()  # Use default parameters
  # Or customize parameters:
  mc.run_test_all(x_dist=-100, y_dist=-100, feedrate=2000)
  ```
- **Description**: Moves each axis in sequence, suitable for initial testing or full functionality verification

---

#### 5. 电机控制 / Motor Control

**中文：**
- **准备电机**（自动启用）：
  ```python
  mc.prepare_motors()
  ```
- **禁用电机**（释放扭矩）：
  ```python
  mc.disable_steppers()
  ```
- **说明**：初始化时会自动准备电机；使用完毕后建议禁用电机以节能和减少发热

**English:**
- **Prepare motors** (auto-enable):
  ```python
  mc.prepare_motors()
  ```
- **Disable motors** (release torque):
  ```python
  mc.disable_steppers()
  ```
- **Description**: Motors are automatically prepared during initialization; it's recommended to disable motors after use to save power and reduce heating

---

#### 6. 定位模式 / Positioning Mode

**中文：**
- **相对定位**（默认）：每次移动基于当前位置
  ```python
  mc.set_relative_positioning()
  ```

**English:**
- **Relative positioning** (default): Each movement is relative to current position
  ```python
  mc.set_relative_positioning()
  ```

---

#### 7. 关闭连接 / Close Connection

**中文：**
- **功能**：安全关闭串口连接
- **使用方法**：
  ```python
  mc.close()
  ```
- **说明**：程序结束前务必调用此方法，避免串口被占用

**English:**
- **Function**: Safely close serial port connection
- **Usage**:
  ```python
  mc.close()
  ```
- **Description**: Always call this method before program exit to avoid port occupation

---

## 自定义使用示例 / Custom Usage Examples

**中文：**  
如果你想编写自己的控制脚本，可以参考以下示例：

**English:**  
If you want to write your own control script, you can refer to the following examples:

### 示例 1：简单移动 / Example 1: Simple Movement

```python
from motorcontroller import MotorController
import time

# 初始化控制器 / Initialize controller
mc = MotorController()

# 移动X轴50mm / Move X-axis 50mm
mc.move_x(50)
time.sleep(2)

# 移动Y轴-30mm / Move Y-axis -30mm
mc.move_y(-30)
time.sleep(2)

# 关闭连接 / Close connection
mc.disable_steppers()
mc.close()
```

### 示例 2：自定义速度 / Example 2: Custom Speed

```python
from motorcontroller import MotorController

mc = MotorController()

# 快速移动（3000mm/min）/ Fast movement (3000mm/min)
mc.move_x(100, feedrate=3000)

# 慢速移动（500mm/min）/ Slow movement (500mm/min)
mc.move_z(10, feedrate=500)

mc.disable_steppers()
mc.close()
```

### 示例 3：循环移动 / Example 3: Repeated Movement

```python
from motorcontroller import MotorController
import time

mc = MotorController()

# 重复移动5次 / Repeat movement 5 times
for i in range(5):
    print(f"第 {i+1} 次移动 / Movement {i+1}")
    mc.move_x(10)
    time.sleep(1)
    mc.move_x(-10)
    time.sleep(1)

mc.disable_steppers()
mc.close()
```

---

## 故障排除 / Troubleshooting

### 问题 1：找不到串口 / Issue 1: Cannot Find Serial Port

**中文：**
- **现象**：程序提示"找不到可用的串口设备"
- **解决方法**：
  1. 检查 USB 线是否正确连接
  2. 检查控制板是否通电
  3. 在设备管理器（Windows）或终端（Mac/Linux）中确认设备已识别
  4. 尝试手动指定串口：`mc = MotorController(port='COM3')`（Windows）或 `mc = MotorController(port='/dev/ttyUSB0')`（Linux）

**English:**
- **Symptom**: Program shows "Cannot find available serial port device"
- **Solution**:
  1. Check if USB cable is properly connected
  2. Check if control board is powered on
  3. Confirm device is recognized in Device Manager (Windows) or Terminal (Mac/Linux)
  4. Try manually specifying port: `mc = MotorController(port='COM3')` (Windows) or `mc = MotorController(port='/dev/ttyUSB0')` (Linux)

---

### 问题 2：电机不移动 / Issue 2: Motors Not Moving

**中文：**
- **可能原因**：
  1. 电机未启用
  2. 控制板未正确配置
  3. 电机驱动器未通电
- **解决方法**：
  1. 确认初始化时 `auto_enable=True`（默认）
  2. 手动调用 `mc.prepare_motors()`
  3. 检查硬件连接和电源

**English:**
- **Possible causes**:
  1. Motors not enabled
  2. Control board not properly configured
  3. Motor drivers not powered
- **Solution**:
  1. Confirm `auto_enable=True` during initialization (default)
  2. Manually call `mc.prepare_motors()`
  3. Check hardware connections and power supply

---

### 问题 3：程序运行报错 / Issue 3: Program Error

**中文：**
- **常见错误**：`ModuleNotFoundError: No module named 'serial'`
- **解决方法**：安装 pyserial 库
  ```bash
  pip install pyserial
  ```

**English:**
- **Common error**: `ModuleNotFoundError: No module named 'serial'`
- **Solution**: Install pyserial library
  ```bash
  pip install pyserial
  ```

---

## 安全提示 / Safety Notes

**中文：**
1. ⚠️ **首次运行前**：确保电机周围无障碍物，避免碰撞
2. ⚠️ **移动范围**：了解每个轴的物理限位，避免超出范围导致损坏
3. ⚠️ **紧急停止**：运行中按 `Ctrl+C` 可立即中断程序
4. ⚠️ **使用完毕**：务必调用 `mc.disable_steppers()` 禁用电机，避免过热

**English:**
1. ⚠️ **Before first run**: Ensure no obstacles around motors to avoid collisions
2. ⚠️ **Movement range**: Know the physical limits of each axis to avoid damage from exceeding range
3. ⚠️ **Emergency stop**: Press `Ctrl+C` during operation to immediately interrupt the program
4. ⚠️ **After use**: Always call `mc.disable_steppers()` to disable motors and prevent overheating

---
