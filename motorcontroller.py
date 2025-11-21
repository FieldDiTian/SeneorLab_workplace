#!/usr/bin/env python3
"""
增强版电机控制器 (简化版) / Enhanced Motor Controller (Simplified Version)

这个控制器扩展了原有的MotorController功能，为每个轴提供单独的移动方法，
简化了运动控制，并集成了安全机制。专注于相对移动，无需位置报告。
只提供单轴移动功能，确保最大的兼容性和可靠性。

This controller extends the original MotorController functionality, providing individual 
movement methods for each axis, simplifying motion control, and integrating safety mechanisms. 
Focuses on relative movement without position reporting. Only provides single-axis movement 
functionality to ensure maximum compatibility and reliability.
"""

import serial
import time
import glob
import sys
import os

class MotorController:
    def __init__(self, port=None, baudrate=115200, auto_enable=True, default_feedrate=1000, wait_time=0.5):
        """
        初始化电机控制器 / Initialize Motor Controller
        
        参数 / Parameters:
        - port: 串口路径，如果为None则自动检测 / Serial port path, auto-detect if None
        - baudrate: 波特率，默认115200 / Baud rate, default 115200
        - auto_enable: 是否自动启用步进电机 / Whether to auto-enable stepper motors
        - default_feedrate: 默认进给速度(mm/min) / Default feed rate (mm/min)
        - wait_time: 默认运动后等待时间(秒) / Default wait time after movement (seconds)
        """
        # 保存设置
        self.baudrate = baudrate
        self.default_feedrate = default_feedrate
        self.wait_time = wait_time
        self.is_connected = False
        self.ser = None
        
        # 自动检测端口（如果未指定）
        if port is None:
            print("未指定串口，尝试自动检测... / Serial port not specified, attempting auto-detection...")
            available_ports = self._find_available_ports()
            if not available_ports:
                raise serial.SerialException("找不到可用的串口设备，请检查设备连接 / Cannot find available serial devices, please check device connection")
            
            # 使用第一个检测到的端口（优先USB模块端口）
            self.port = available_ports[0]
            print(f"自动选择串口 / Auto-selected serial port: {self.port}")
            
            # 连接到选定的串口
            self._connect_to_port(self.port)
            
            # 如果首选端口连接失败，尝试其他端口
            if not self.is_connected and len(available_ports) > 1:
                print("首选端口连接失败，尝试其他端口... / Primary port connection failed, trying other ports...")
                for alt_port in available_ports[1:]:
                    print(f"尝试备选端口 / Trying alternative port: {alt_port}")
                    self._connect_to_port(alt_port)
                    if self.is_connected:
                        self.port = alt_port
                        print(f"成功连接到备选端口 / Successfully connected to alternative port: {alt_port}")
                        break
        else:
            # 直接使用指定的端口
            self.port = port
            print(f"使用指定串口 / Using specified serial port: {self.port}")
            self._connect_to_port(self.port)
            
        # 检查连接状态
        if not self.is_connected or not self.ser:
            raise serial.SerialException("无法连接到任何可用的串口设备，请检查连接或手动指定端口 / Cannot connect to any available serial device, please check connection or manually specify port")
            
        # 如果设置了auto_enable，准备步进电机
        if auto_enable:
            print("准备步进电机... / Preparing stepper motors...")
            self.prepare_motors()
            time.sleep(0.5)  # 等待稳定 / Wait for stabilization
        
        # Steps per mm configuration (统一设置为100步/毫米)
        self.steps_per_mm = {
            'X': 100,  # Motor1
            'Y': 100,  # Motor2
            'Z': 100,  # Motor3
            'I': 100,  # Motor7
            'J': 100,  # Motor8
            'K': 100,  # Motor9
            'U': 100,  # Motor4
            'V': 100,  # Motor5
            'W': 100,  # Motor6
            'E': 100   # Motor10 (E0 extruder)
        }
        
        # 设置为相对移动模式
        self.set_relative_positioning()

    def _find_available_ports(self):
        """查找系统上可用的串口设备 / Find available serial devices on the system"""
        available_ports = []
        preferred_ports = []
        
        # 根据操作系统类型检测可能的串口
        if sys.platform.startswith('win'):  # Windows
            candidates = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):  # Linux
            candidates = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):  # MacOS
            candidates = glob.glob('/dev/tty.*') + glob.glob('/dev/cu.*')
        else:
            raise EnvironmentError('不支持的操作系统 / Unsupported operating system')
        
        # 尝试打开每个候选端口
        for port in candidates:
            try:
                # 跳过不需要的设备
                if any(skip in port for skip in ['Bluetooth', 'debug-console', 'Dialin']):
                    continue
                
                # 检查端口是否可用
                s = serial.Serial(port, 115200, timeout=0.1)
                s.close()
                
                # 将USB模块设备(usbmodem)添加到首选端口列表
                if 'usbmodem' in port:
                    preferred_ports.append(port)
                    print(f"找到USB设备端口 / Found USB device port: {port}")
                else:
                    available_ports.append(port)
            except (OSError, serial.SerialException):
                pass
        
        # 首先返回USB模块端口，然后是其他可用端口
        all_ports = preferred_ports + available_ports
        print(f"发现可用端口 / Discovered available ports: {all_ports}")
        
        if not all_ports:
            print("警告: 未找到可用的串口设备 / Warning: No available serial devices found")
            
        return all_ports
    
    def _connect_to_port(self, port):
        """连接到指定的串口 / Connect to specified serial port"""
        try:
            print(f"正在连接到 / Connecting to {port}，波特率 / baudrate {self.baudrate}...")
            self.ser = serial.Serial(port, self.baudrate, timeout=2, write_timeout=2)
            time.sleep(3)  # 增加等待时间，确保板子完全初始化 / Wait longer to ensure board is fully initialized
            
            # 发送一个简单命令测试连接，并验证是否是Marlin固件
            response = self._send_test_command()
            
            # 验证是否收到了Marlin固件的响应
            if response and ('FIRMWARE_NAME:Marlin' in response or 'ok' in response.lower()):
                self.is_connected = True
                print(f"成功连接到 / Successfully connected to {port} (Marlin固件已验证 / Marlin firmware verified)")
            else:
                print(f"警告 / Warning: {port} 未返回有效的Marlin固件响应 / did not return valid Marlin firmware response")
                self.is_connected = False
                
        except Exception as e:
            print(f"连接 / Connection to {port} 失败 / failed: {e}")
            self.is_connected = False
    
    def _try_alternative_ports(self, available_ports):
        """尝试连接到备选端口 / Try connecting to alternative ports"""
        if len(available_ports) > 1:
            print("尝试其他可用串口... / Trying other available serial ports...")
            for alt_port in available_ports[1:]:
                self._connect_to_port(alt_port)
                if self.is_connected:
                    self.port = alt_port
                    return
    
    def _send_test_command(self):
        """发送测试命令确认连接，返回响应字符串 / Send test command to confirm connection, return response string"""
        try:
            # 清空缓冲区 / Clear buffer
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            # 发送M115命令获取固件信息 / Send M115 command to get firmware info
            print("发送 / Sending: M115")
            self.ser.write("M115\n".encode())
            self.ser.flush()
            
            # 等待响应 / Wait for response
            time.sleep(1)
            response = ""
            start_time = time.time()
            while time.time() - start_time < 2:  # 最多等待2秒 / Wait max 2 seconds
                if self.ser.in_waiting:
                    response += self.ser.read(self.ser.in_waiting).decode(errors='ignore')
                    if 'ok' in response.lower() or 'FIRMWARE_NAME:Marlin' in response:
                        break
                time.sleep(0.1)
            
            if response:
                print(f"接收 / Received: {response.strip()}")
            else:
                print("警告: 未收到响应 / Warning: No response received")
                
            return response
            
        except Exception as e:
            print(f"发送测试命令时出错 / Error sending test command: {e}")
            return ""
    
    def close(self):
        """关闭串口连接 / Close serial port connection"""
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()
            print("串口连接已关闭 / Serial port connection closed")
    
    def send_gcode(self, command):
        """发送G-code命令到控制器 / Send G-code command to controller"""
        if not hasattr(self, 'ser') or not self.ser or not self.ser.is_open:
            raise serial.SerialException("串口未连接或已关闭 / Serial port not connected or closed")
        
        # 准备命令 / Prepare command
        command = command.strip()
        print(f"发送 / Sending: {command}")
        
        # 添加换行符并尝试发送，带重试 / Add newline and try to send with retry
        command += "\n"
        
        for attempt in range(2):  # 最多尝试2次 / Try max 2 times
            try:
                # 清空缓冲区 / Clear buffer
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                
                # 发送命令 / Send command
                bytes_written = self.ser.write(command.encode())
                self.ser.flush()
                
                if bytes_written != len(command):
                    print(f"警告: 只发送了 / Warning: Only sent {bytes_written}/{len(command)} 字节 / bytes")
                
                # 等待并读取响应 / Wait and read response
                time.sleep(0.2)  # 稍微等待，确保有时间接收响应 / Wait briefly to ensure time to receive response
                response = ""
                start_time = time.time()
                
                # 最多等待1秒获取完整响应 / Wait max 1 second for complete response
                while time.time() - start_time < 1:
                    if self.ser.in_waiting:
                        chunk = self.ser.read(self.ser.in_waiting).decode(errors='ignore')
                        response += chunk
                        if 'ok' in response.lower():
                            break  # 收到ok回复，可以结束了 / Received ok reply, can finish
                    time.sleep(0.1)
                
                if response:
                    print(f"接收 / Received: {response.strip()}")
                
                return response
                
            except Exception as e:
                if attempt == 0:  # 第一次尝试失败，重试一次 / First attempt failed, retry once
                    print(f"发送命令时出错，重试中 / Error sending command, retrying: {e}")
                    time.sleep(0.5)
                else:
                    print(f"发送命令失败 / Command sending failed: {e}")
                    raise
    
    def prepare_motors(self):
        # 相对模式 (G91) / Return to relative mode (G91)
        print("相对模式 (G91) / Return to relative mode (G91)")
        self.send_gcode("G91")
    
    def disable_steppers(self):
        """禁用所有步进电机 (M18/M84) / Disable all stepper motors (M18/M84)"""
        print("禁用步进电机... / Disabling stepper motors...")
        self.send_gcode("M18")  # 或者使用 M84 / Or use M84
    
    def set_relative_positioning(self):
        """设置为相对定位模式 (G91) / Set to relative positioning mode (G91)"""
        print("设置相对定位模式... / Setting relative positioning mode...")
        self.send_gcode("G91")  # 相对坐标模式 / Relative coordinate mode
        # 同时设置挤出机为相对模式 / Also set extruder to relative mode
        self.send_gcode("M83")
    
    def set_absolute_positioning(self):
        """设置为绝对定位模式 (G90) / Set to absolute positioning mode (G90)"""
        print("设置绝对定位模式... / Setting absolute positioning mode...")
        self.send_gcode("G90")  # 绝对坐标模式 / Absolute coordinate mode
        # 同时设置挤出机为绝对模式 / Also set extruder to absolute mode
        self.send_gcode("M82")
    
    def wait_for_movement(self):
        """等待所有移动完成 (M400) / Wait for all movements to complete (M400)"""
        self.send_gcode("M400")
        time.sleep(self.wait_time)  # 额外等待确保稳定 / Extra wait to ensure stability
    
    def move_axis(self, axis, distance, feedrate=None, wait=True):
        """
        移动指定轴指定距离 / Move specified axis by specified distance
        
        参数 / Parameters:
        - axis: 轴名称 / Axis name ('X', 'Y', 'Z', 'I', 'J', 'K', 'U', 'V', 'W', 'E')
        - distance: 移动距离 (毫米) / Movement distance (millimeters)
        - feedrate: 进给速度 (毫米/分钟)，如果为None则使用默认值 / Feed rate (mm/min), use default if None
        - wait: 是否等待移动完成 / Whether to wait for movement to complete
        """
        valid_axes = ['X', 'Y', 'Z', 'I', 'J', 'K', 'U', 'V', 'W', 'E']
        if axis not in valid_axes:
            raise ValueError(f"无效轴 / Invalid axis: {axis}. 必须是以下之一 / Must be one of: {', '.join(valid_axes)}")
        
        if feedrate is None:
            feedrate = self.default_feedrate
        
        # 确保在相对模式下 / Ensure in relative mode
        self.set_relative_positioning()
        
        # 如果是E轴，先选择挤出机0 / If E axis, select extruder 0 first
        if axis == 'E':
            self.select_extruder(0)
            
        # 执行移动命令 / Execute movement command
        cmd = f"G1 {axis}{distance:.4f} F{feedrate}"
        print(f"\n移动 / Moving {axis}轴 / axis {distance}mm (速度 / speed: {feedrate}mm/min)...")
        self.send_gcode(cmd)
        
        # 增加一个固定的延时来防止主板断联
        time.sleep(1)
        
        # 等待移动完成 / Wait for movement to complete
        if wait:
            self.wait_for_movement()
    
    # === 以下为每个轴的专用移动方法 / Following are dedicated movement methods for each axis ===
    
    def move_x(self, distance, feedrate=None, wait=True):
        """移动X轴指定距离 / Move X-axis by specified distance"""
        self.move_axis('X', distance, feedrate, wait)
    
    def move_y(self, distance, feedrate=None, wait=True):
        """移动Y轴指定距离 / Move Y-axis by specified distance"""
        self.move_axis('Y', distance, feedrate, wait)
    
    def move_z(self, distance, feedrate=None, wait=True):
        """移动Z轴指定距离 / Move Z-axis by specified distance"""
        self.move_axis('Z', distance, feedrate, wait)
    
    def move_i(self, distance, feedrate=None, wait=True):
        """移动I轴指定距离 / Move I-axis by specified distance"""
        self.move_axis('I', distance, feedrate, wait)
    
    def move_j(self, distance, feedrate=None, wait=True):
        """移动J轴指定距离 / Move J-axis by specified distance"""
        self.move_axis('J', distance, feedrate, wait)
    
    def move_k(self, distance, feedrate=None, wait=True):
        """移动K轴指定距离 / Move K-axis by specified distance"""
        self.move_axis('K', distance, feedrate, wait)
    
    def move_u(self, distance, feedrate=None, wait=True):
        """移动U轴指定距离 / Move U-axis by specified distance"""
        self.move_axis('U', distance, feedrate, wait)
    
    def move_v(self, distance, feedrate=None, wait=True):
        """移动V轴指定距离 / Move V-axis by specified distance"""
        self.move_axis('V', distance, feedrate, wait)
    
    def move_w(self, distance, feedrate=None, wait=True):
        """移动W轴指定距离 / Move W-axis by specified distance"""
        self.move_axis('W', distance, feedrate, wait)
    
    def move_e(self, distance, feedrate=None, wait=True):
        """移动E轴(挤出机)指定距离 / Move E-axis (extruder) by specified distance"""
        self.move_axis('E', distance, feedrate, wait)
    
    def select_extruder(self, index=0):
        """选择挤出机 (T命令) / Select extruder (T command)"""
        self.send_gcode(f"T{index}")
        time.sleep(0.2)
    
    def run_test(self, x_dist=-100, y_dist=-100, z_dist=-50,
                   u_dist=-10, v_dist=-10, w_dist=-50,
                   i_dist=-100, j_dist=-100, k_dist=-50,
                   e_dist=5, feedrate=1000, wait_time=2):
        """
        运行全部10轴顺序测试 / Run sequential test of all 10 axes
        
        这是test_all(doing well).py脚本功能的集成版本 / This is an integrated version of the test_all(doing well).py script functionality
        """
        print("\n" + "=" * 60)
        print("十轴顺序运动测试 / 10-Axis Sequential Movement Test")
        print("=" * 60)
        print("主要轴 (XYZ) / Main Axes (XYZ):")
        print(f"  X轴移动 / X-axis movement: {x_dist}mm, Y轴移动 / Y-axis movement: {y_dist}mm, Z轴移动 / Z-axis movement: {z_dist}mm")
        print("额外轴组1 (UVW) / Additional Axes Group 1 (UVW):")
        print(f"  U轴移动 / U-axis movement: {u_dist}mm, V轴移动 / V-axis movement: {v_dist}mm, W轴移动 / W-axis movement: {w_dist}mm")
        print("额外轴组2 (IJK) / Additional Axes Group 2 (IJK):")
        print(f"  I轴移动 / I-axis movement: {i_dist}mm, J轴移动 / J-axis movement: {j_dist}mm, K轴移动 / K-axis movement: {k_dist}mm")
        print("挤出机轴 (E) / Extruder Axis (E):")
        print(f"  E轴移动 / E-axis movement: {e_dist}mm")
        print(f"运动速度 / Movement speed: {feedrate}mm/min, 等待时间 / Wait time: {wait_time}秒 / seconds")
        print("=" * 60 + "\n")
        
        try:
            # 确保通信正常 / Ensure communication is normal
            print("\n验证通信... / Verifying communication...")
            self.send_gcode("M115")  # 获取固件信息 / Get firmware info
            time.sleep(0.5)
            
            # 确保相对模式 / Ensure relative mode
            self.set_relative_positioning()
            
            # 开始移动测试 / Start movement test
            print("\n----- 开始移动主要轴 (XYZ) / Start Moving Main Axes (XYZ) -----")
            self.move_x(x_dist, feedrate)
            time.sleep(wait_time)
            
            self.move_y(y_dist, feedrate)
            time.sleep(wait_time)
            
            self.move_z(z_dist, feedrate)
            time.sleep(wait_time)
            
            print("\n----- 开始移动额外轴组1 (UVW) / Start Moving Additional Axes Group 1 (UVW) -----")
            self.move_u(u_dist, feedrate)
            time.sleep(wait_time)
            
            self.move_v(v_dist, feedrate)
            time.sleep(wait_time)
            
            self.move_w(w_dist, feedrate)
            time.sleep(wait_time)
            
            print("\n----- 开始移动额外轴组2 (IJK) / Start Moving Additional Axes Group 2 (IJK) -----")
            self.move_i(i_dist, feedrate)
            time.sleep(wait_time)
            
            self.move_j(j_dist, feedrate)
            time.sleep(wait_time)
            
            self.move_k(k_dist, feedrate)
            time.sleep(wait_time)
            
            print("\n----- 开始移动挤出机轴 (E) / Start Moving Extruder Axis (E) -----")
            self.select_extruder(0)
            time.sleep(0.5)
            self.move_e(e_dist, feedrate)
            time.sleep(wait_time)
            
        except KeyboardInterrupt:
            print("\n检测到键盘中断，停止测试 / Keyboard interrupt detected, stopping test")
        
        print("\n全部测试完成 / All tests completed")
