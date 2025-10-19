#!/usr/bin/env python3
"""
增强版电机控制器 (简化版)

这个控制器扩展了原有的MotorController功能，为每个轴提供单独的移动方法，
简化了运动控制，并集成了安全机制。专注于相对移动，无需位置报告。
只提供单轴移动功能，确保最大的兼容性和可靠性。
"""

import serial
import time
import glob
import sys
import os

class EnhancedMotorController:
    def __init__(self, port=None, baudrate=115200, auto_enable=True, default_feedrate=1000, wait_time=0.5):
        """
        初始化电机控制器
        
        参数:
        - port: 串口路径，如果为None则自动检测
        - baudrate: 波特率，默认115200
        - auto_enable: 是否自动启用步进电机
        - default_feedrate: 默认进给速度(mm/min)
        - wait_time: 默认运动后等待时间(秒)
        """
        # 保存设置
        self.baudrate = baudrate
        self.default_feedrate = default_feedrate
        self.wait_time = wait_time
        self.is_connected = False
        self.ser = None
        
        # 自动检测端口（如果未指定）
        if port is None:
            print("未指定串口，尝试自动检测...")
            available_ports = self._find_available_ports()
            if not available_ports:
                raise serial.SerialException("找不到可用的串口设备，请检查设备连接")
            
            # 使用第一个检测到的端口（优先USB模块端口）
            self.port = available_ports[0]
            print(f"自动选择串口: {self.port}")
            
            # 连接到选定的串口
            self._connect_to_port(self.port)
            
            # 如果首选端口连接失败，尝试其他端口
            if not self.is_connected and len(available_ports) > 1:
                print("首选端口连接失败，尝试其他端口...")
                for alt_port in available_ports[1:]:
                    print(f"尝试备选端口: {alt_port}")
                    self._connect_to_port(alt_port)
                    if self.is_connected:
                        self.port = alt_port
                        print(f"成功连接到备选端口: {alt_port}")
                        break
        else:
            # 直接使用指定的端口
            self.port = port
            print(f"使用指定串口: {self.port}")
            self._connect_to_port(self.port)
            
        # 检查连接状态
        if not self.is_connected or not self.ser:
            raise serial.SerialException("无法连接到任何可用的串口设备，请检查连接或手动指定端口")
            
        # 如果设置了auto_enable，准备步进电机
        if auto_enable:
            print("准备步进电机...")
            self.prepare_motors()
            time.sleep(0.5)  # 等待稳定
        
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
        """查找系统上可用的串口设备"""
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
            raise EnvironmentError('不支持的操作系统')
        
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
                    print(f"找到USB设备端口: {port}")
                else:
                    available_ports.append(port)
            except (OSError, serial.SerialException):
                pass
        
        # 首先返回USB模块端口，然后是其他可用端口
        all_ports = preferred_ports + available_ports
        print(f"发现可用端口: {all_ports}")
        
        if not all_ports:
            print("警告: 未找到可用的串口设备")
            
        return all_ports
    
    def _connect_to_port(self, port):
        """连接到指定的串口"""
        try:
            print(f"正在连接到 {port}，波特率 {self.baudrate}...")
            self.ser = serial.Serial(port, self.baudrate, timeout=2, write_timeout=2)
            time.sleep(3)  # 增加等待时间，确保板子完全初始化
            
            # 发送一个简单命令测试连接，并验证是否是Marlin固件
            response = self._send_test_command()
            
            # 验证是否收到了Marlin固件的响应
            if response and ('FIRMWARE_NAME:Marlin' in response or 'ok' in response.lower()):
                self.is_connected = True
                print(f"成功连接到 {port} (Marlin固件已验证)")
            else:
                print(f"警告: {port} 未返回有效的Marlin固件响应")
                self.is_connected = False
                
        except Exception as e:
            print(f"连接 {port} 失败: {e}")
            self.is_connected = False
    
    def _try_alternative_ports(self, available_ports):
        """尝试连接到备选端口"""
        if len(available_ports) > 1:
            print("尝试其他可用串口...")
            for alt_port in available_ports[1:]:
                self._connect_to_port(alt_port)
                if self.is_connected:
                    self.port = alt_port
                    return
    
    def _send_test_command(self):
        """发送测试命令确认连接，返回响应字符串"""
        try:
            # 清空缓冲区
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            # 发送M115命令获取固件信息
            print("发送: M115")
            self.ser.write("M115\n".encode())
            self.ser.flush()
            
            # 等待响应
            time.sleep(1)
            response = ""
            start_time = time.time()
            while time.time() - start_time < 2:  # 最多等待2秒
                if self.ser.in_waiting:
                    response += self.ser.read(self.ser.in_waiting).decode(errors='ignore')
                    if 'ok' in response.lower() or 'FIRMWARE_NAME:Marlin' in response:
                        break
                time.sleep(0.1)
            
            if response:
                print(f"接收: {response.strip()}")
            else:
                print("警告: 未收到响应")
                
            return response
            
        except Exception as e:
            print(f"发送测试命令时出错: {e}")
            return ""
    
    def close(self):
        """关闭串口连接"""
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()
            print("串口连接已关闭")
    
    def send_gcode(self, command):
        """发送G-code命令到控制器"""
        if not hasattr(self, 'ser') or not self.ser or not self.ser.is_open:
            raise serial.SerialException("串口未连接或已关闭")
        
        # 准备命令    
        command = command.strip()
        print(f"发送: {command}")
        
        # 添加换行符并尝试发送，带重试
        command += "\n"
        
        for attempt in range(2):  # 最多尝试2次
            try:
                # 清空缓冲区
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                
                # 发送命令
                bytes_written = self.ser.write(command.encode())
                self.ser.flush()
                
                if bytes_written != len(command):
                    print(f"警告: 只发送了 {bytes_written}/{len(command)} 字节")
                
                # 等待并读取响应
                time.sleep(0.2)  # 稍微等待，确保有时间接收响应
                response = ""
                start_time = time.time()
                
                # 最多等待1秒获取完整响应
                while time.time() - start_time < 1:
                    if self.ser.in_waiting:
                        chunk = self.ser.read(self.ser.in_waiting).decode(errors='ignore')
                        response += chunk
                        if 'ok' in response.lower():
                            break  # 收到ok回复，可以结束了
                    time.sleep(0.1)
                
                if response:
                    print(f"接收: {response.strip()}")
                
                return response
                
            except Exception as e:
                if attempt == 0:  # 第一次尝试失败，重试一次
                    print(f"发送命令时出错，重试中: {e}")
                    time.sleep(0.5)
                else:
                    print(f"发送命令失败: {e}")
                    raise
    
    def prepare_motors(self):
        """准备电机，替代M17命令的安全方法"""
        # 不使用M17命令，而是通过其他方式确保电机已准备好
        print("安全准备电机，不使用M17命令...")
        
        # 设置绝对定位模式 (G90)
        self.send_gcode("G90")
        time.sleep(0.2)
        
        # 确保电机加速度和速度设置正确
        self.send_gcode("M201 X3000 Y3000 Z3000 I3000 J3000 K3000 U3000 V3000 W3000 E3000")  # 设置加速度
        self.send_gcode("M203 X300 Y300 Z300 I300 J300 K300 U300 V300 W300 E300")  # 设置最大速度
        time.sleep(0.3)
        
        # 回到相对模式 (G91)
        self.send_gcode("G91")
    
    def disable_steppers(self):
        """禁用所有步进电机 (M18/M84)"""
        print("禁用步进电机...")
        self.send_gcode("M18")  # 或者使用 M84
    
    def set_relative_positioning(self):
        """设置为相对定位模式 (G91)"""
        print("设置相对定位模式...")
        self.send_gcode("G91")  # 相对坐标模式
        # 同时设置挤出机为相对模式
        self.send_gcode("M83")
    
    def set_absolute_positioning(self):
        """设置为绝对定位模式 (G90)"""
        print("设置绝对定位模式...")
        self.send_gcode("G90")  # 绝对坐标模式
        # 同时设置挤出机为绝对模式
        self.send_gcode("M82")
    
    def wait_for_movement(self):
        """等待所有移动完成 (M400)"""
        self.send_gcode("M400")
        time.sleep(self.wait_time)  # 额外等待确保稳定
    
    def move_axis(self, axis, distance, feedrate=None, wait=True):
        """
        移动指定轴指定距离
        
        参数:
        - axis: 轴名称 ('X', 'Y', 'Z', 'I', 'J', 'K', 'U', 'V', 'W', 'E')
        - distance: 移动距离 (毫米)
        - feedrate: 进给速度 (毫米/分钟)，如果为None则使用默认值
        - wait: 是否等待移动完成
        """
        valid_axes = ['X', 'Y', 'Z', 'I', 'J', 'K', 'U', 'V', 'W', 'E']
        if axis not in valid_axes:
            raise ValueError(f"无效轴: {axis}. 必须是以下之一: {', '.join(valid_axes)}")
        
        if feedrate is None:
            feedrate = self.default_feedrate
        
        # 确保在相对模式下
        self.set_relative_positioning()
        
        # 如果是E轴，先选择挤出机0
        if axis == 'E':
            self.select_extruder(0)
            
        # 执行移动命令
        cmd = f"G1 {axis}{distance:.4f} F{feedrate}"
        print(f"\n移动 {axis}轴 {distance}mm (速度: {feedrate}mm/min)...")
        self.send_gcode(cmd)
        
        # 等待移动完成
        if wait:
            self.wait_for_movement()
    
    # === 以下为每个轴的专用移动方法 ===
    
    def move_x(self, distance, feedrate=None, wait=True):
        """移动X轴指定距离"""
        self.move_axis('X', distance, feedrate, wait)
    
    def move_y(self, distance, feedrate=None, wait=True):
        """移动Y轴指定距离"""
        self.move_axis('Y', distance, feedrate, wait)
    
    def move_z(self, distance, feedrate=None, wait=True):
        """移动Z轴指定距离"""
        self.move_axis('Z', distance, feedrate, wait)
    
    def move_i(self, distance, feedrate=None, wait=True):
        """移动I轴指定距离"""
        self.move_axis('I', distance, feedrate, wait)
    
    def move_j(self, distance, feedrate=None, wait=True):
        """移动J轴指定距离"""
        self.move_axis('J', distance, feedrate, wait)
    
    def move_k(self, distance, feedrate=None, wait=True):
        """移动K轴指定距离"""
        self.move_axis('K', distance, feedrate, wait)
    
    def move_u(self, distance, feedrate=None, wait=True):
        """移动U轴指定距离"""
        self.move_axis('U', distance, feedrate, wait)
    
    def move_v(self, distance, feedrate=None, wait=True):
        """移动V轴指定距离"""
        self.move_axis('V', distance, feedrate, wait)
    
    def move_w(self, distance, feedrate=None, wait=True):
        """移动W轴指定距离"""
        self.move_axis('W', distance, feedrate, wait)
    
    def move_e(self, distance, feedrate=None, wait=True):
        """移动E轴(挤出机)指定距离"""
        self.move_axis('E', distance, feedrate, wait)
    
    def select_extruder(self, index=0):
        """选择挤出机 (T命令)"""
        self.send_gcode(f"T{index}")
        time.sleep(0.2)
    
    def run_test_all(self, x_dist=-100, y_dist=-100, z_dist=-50,
                   u_dist=-10, v_dist=-10, w_dist=-50,
                   i_dist=-100, j_dist=-100, k_dist=-50,
                   e_dist=5, feedrate=1000, wait_time=2):
        """
        运行全部10轴顺序测试
        
        这是test_all(doing well).py脚本功能的集成版本
        """
        print("\n" + "=" * 60)
        print("十轴顺序运动测试")
        print("=" * 60)
        print("主要轴 (XYZ):")
        print(f"  X轴移动: {x_dist}mm, Y轴移动: {y_dist}mm, Z轴移动: {z_dist}mm")
        print("额外轴组1 (UVW):")
        print(f"  U轴移动: {u_dist}mm, V轴移动: {v_dist}mm, W轴移动: {w_dist}mm")
        print("额外轴组2 (IJK):")
        print(f"  I轴移动: {i_dist}mm, J轴移动: {j_dist}mm, K轴移动: {k_dist}mm")
        print("挤出机轴 (E):")
        print(f"  E轴移动: {e_dist}mm")
        print(f"运动速度: {feedrate}mm/min, 等待时间: {wait_time}秒")
        print("=" * 60 + "\n")
        
        try:
            # 确保通信正常
            print("\n验证通信...")
            self.send_gcode("M115")  # 获取固件信息
            time.sleep(0.5)
            
            # 确保相对模式
            self.set_relative_positioning()
            
            # 开始移动测试
            print("\n----- 开始移动主要轴 (XYZ) -----")
            self.move_x(x_dist, feedrate)
            time.sleep(wait_time)
            
            self.move_y(y_dist, feedrate)
            time.sleep(wait_time)
            
            self.move_z(z_dist, feedrate)
            time.sleep(wait_time)
            
            print("\n----- 开始移动额外轴组1 (UVW) -----")
            self.move_u(u_dist, feedrate)
            time.sleep(wait_time)
            
            self.move_v(v_dist, feedrate)
            time.sleep(wait_time)
            
            self.move_w(w_dist, feedrate)
            time.sleep(wait_time)
            
            print("\n----- 开始移动额外轴组2 (IJK) -----")
            self.move_i(i_dist, feedrate)
            time.sleep(wait_time)
            
            self.move_j(j_dist, feedrate)
            time.sleep(wait_time)
            
            self.move_k(k_dist, feedrate)
            time.sleep(wait_time)
            
            print("\n----- 开始移动挤出机轴 (E) -----")
            self.select_extruder(0)
            time.sleep(0.5)
            self.move_e(e_dist, feedrate)
            time.sleep(wait_time)
            
        except KeyboardInterrupt:
            print("\n检测到键盘中断，停止测试")
        
        print("\n全部测试完成")


# 示例用法
if __name__ == "__main__":
    try:
        print("初始化增强版电机控制器...")
        mc = EnhancedMotorController()
        
        print("\n运行简单测试...")
        mc.move_x(10)  # X轴移动10mm
        time.sleep(1)
        mc.move_y(10)  # Y轴移动10mm
        
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'mc' in locals():
            print("\n清理资源...")
            mc.disable_steppers()
            mc.close()