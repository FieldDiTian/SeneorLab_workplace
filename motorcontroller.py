import serial
import time
import glob
import sys
import os

class MotorController:
    def __init__(self, port=None, baudrate=115200, auto_enable=True):
        # 自动检测端口（如果未指定）
        self.baudrate = baudrate
        # 不再使用 M17 命令，避免设备断连问题
        
        if port is None:
            print("未指定串口，尝试自动检测...")
            available_ports = self._find_available_ports()
            if not available_ports:
                raise serial.SerialException("找不到可用的串口设备，请检查设备连接")
            
            self.port = available_ports[0]
            print(f"自动选择串口: {self.port}")
        else:
            self.port = port
            
        # 连接到选定的串口
        print(f"正在连接到 {self.port}，波特率 {baudrate}...")
        try:
            self.ser = serial.Serial(self.port, baudrate, timeout=2, write_timeout=2)
            time.sleep(3)  # 增加等待时间，确保板子完全初始化
            
            # 发送一个简单命令测试连接
            self._send_test_command()
            
            # 如果设置了auto_enable，准备步进电机（但不使用M17命令）
            if auto_enable:
                print("准备步进电机...")
                # 使用安全的方式初始化步进电机状态
                self.prepare_motors()
                time.sleep(0.5)  # 等待稳定
        except Exception as e:
            print(f"连接失败: {e}")
            print("尝试其他可用串口...")
            success = False
            
            # 如果连接失败，尝试其他端口
            if port is None and len(available_ports) > 1:
                for alt_port in available_ports[1:]:
                    try:
                        print(f"尝试连接到 {alt_port}...")
                        self.port = alt_port
                        self.ser = serial.Serial(alt_port, baudrate, timeout=2, write_timeout=2)
                        time.sleep(2)
                        self._send_test_command()
                        success = True
                        
                        if auto_enable:
                            print("准备步进电机...")
                            # 使用安全的方式初始化步进电机状态
                            self.prepare_motors()
                            time.sleep(0.5)
                            
                        break
                    except Exception as alt_e:
                        print(f"连接到 {alt_port} 失败: {alt_e}")
                        
            if not success and port is not None:
                raise

        # Track positions for all motors (10 axes: X, Y, Z, I, J, K, U, V, W, E0)
        self.current_position = {
            'X': 0, 'Y': 0, 'Z': 0,
            'I': 0, 'J': 0, 'K': 0,
            'U': 0, 'V': 0, 'W': 0,
            'E': 0  # E0 only
        }

        # Steps per mm configuration (from Marlin Configuration.h)
        # DEFAULT_AXIS_STEPS_PER_UNIT: { 100, 100, 100, 100, 100, 100, 100, 100, 100, 100 }
        # Order: X, Y, Z, I, J, K, U, V, W, E0
        self.steps_per_mm = {
            'X': 100,   # Motor1
            'Y': 100,   # Motor2
            'Z': 100,   # Motor3
            'I': 100,   # Motor7
            'J': 100,   # Motor8
            'K': 100,   # Motor9
            'U': 100,   # Motor4
            'V': 100,   # Motor5
            'W': 100,   # Motor6
            'E': 100    # Motor10 (E0 extruder)
        }

    def _find_available_ports(self):
        """查找系统上可用的串口设备"""
        available_ports = []
        
        # 根据操作系统类型检测可能的串口
        if sys.platform.startswith('win'):  # Windows
            candidates = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):  # Linux
            candidates = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):  # macOS
            # 在 macOS 上，检查 tty.* 和 cu.* 设备
            candidates = glob.glob('/dev/tty.*') + glob.glob('/dev/cu.*')
        else:
            print(f"未知操作系统: {sys.platform}")
            return []
        
        # 过滤掉明显不是 3D 打印机控制板的设备
        for port in candidates:
            # 跳过蓝牙和调试端口
            if 'Bluetooth' in port or 'debug' in port or 'Dialin' in port:
                continue
                
            try:
                # 尝试打开串口以检查可用性
                test_serial = serial.Serial(port, 115200, timeout=0.5)
                test_serial.close()
                available_ports.append(port)
                print(f"找到可用串口: {port}")
            except (OSError, serial.SerialException):
                pass
                
        return available_ports
        
    def _send_test_command(self):
        """发送简单的测试命令，确认通信正常"""
        try:
            # 清除缓冲区
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            # 发送回显命令 M115 获取固件信息（通常是安全的命令）
            print("发送测试命令 M115...")
            self.ser.write("M115\r\n".encode())
            self.ser.flush()
            
            # 等待回应
            time.sleep(1)
            response = b""
            start_time = time.time()
            while time.time() - start_time < 3:  # 最多等待3秒
                if self.ser.in_waiting:
                    response += self.ser.readline()
                    if b"ok" in response.lower():
                        break
                time.sleep(0.1)
            
            # 打印收到的响应（用于调试）
            if response:
                print(f"收到响应: {response.decode('ascii', errors='ignore')}")
            else:
                print("警告: 未收到设备响应")
                
        except Exception as e:
            print(f"测试命令发送失败: {e}")

    def _reopen(self):
        try:
            self.ser.close()
        except Exception:
            pass
        time.sleep(0.5)  # 增加等待时间
        print(f"尝试重新连接到 {self.port}...")
        self.ser = serial.Serial(self.port, self.baudrate, timeout=2, write_timeout=2)
        time.sleep(1.5)  # 增加等待时间

    def send_gcode(self, cmd):
        print(f">> 发送命令: {cmd}")
        # Robust write with retry and CRLF line ending (some devices expect \r\n)
        payload = (cmd + "\r\n").encode(errors="ignore")
        
        # 在发送命令前先确保设备处于稳定状态
        time.sleep(0.1)
        
        for attempt in range(2):
            try:
                # 每次发送前先清空缓冲区
                try:
                    self.ser.reset_output_buffer()
                    self.ser.reset_input_buffer()
                except Exception:
                    pass
                
                # 增加一个小延迟，确保设备已准备好
                time.sleep(0.2)
                
                # 写入数据并等待发送完成
                bytes_written = self.ser.write(payload)
                self.ser.flush()
                
                # 确认数据写入成功
                if bytes_written == len(payload):
                    print(f"命令已发送 ({bytes_written} 字节)")
                else:
                    print(f"警告: 只发送了 {bytes_written}/{len(payload)} 字节")
                
                # 命令发送后短暂等待
                time.sleep(0.3)
                break
                
            except Exception as e:
                if attempt == 0:
                    print(f"[警告] 命令 '{cmd}' 发送失败，尝试重新连接... ({e})")
                    self._reopen()
                else:
                    print(f"[错误] 命令 '{cmd}' 发送失败: {e}")
                    raise
        response = []
        while True:
            line = self.ser.readline().decode(errors="ignore").strip()
            if line:
                # print(f"<< {line}")
                response.append(line)
                if line.startswith("X:"):
                    try:
                        parts = line.split()
                        for part in parts:
                            if ':' in part:
                                name, value = part.split(':')
                                if name in self.current_position:
                                    self.current_position[name] = float(value)
                    except Exception as e:
                        print(f"Error parsing position: {e}")
            # Typical Marlin replies include 'ok'. Some firmwares may send 'wait' periodically.
            if line.lower().startswith("ok"):
                break
            if line.lower().startswith("wait"):
                # Keep waiting for the actual 'ok' after moves
                continue
        return response

    def prepare_motors(self):
        """准备步进电机状态，但不使用M17命令"""
        print("准备步进电机状态...")
        # 发送前先等待，确保连接稳定
        time.sleep(0.5)
        
        try:
            # 获取当前状态信息
            self.send_gcode("M119")  # 获取所有开关状态
            time.sleep(0.5)
            
            # 获取当前位置
            self.send_gcode("M114")  # 获取当前位置
            time.sleep(0.5)
            
            # 设置绝对定位模式
            self.send_gcode("G90")
            time.sleep(0.5)
            
            print("步进电机准备就绪（将在首次移动时自动启用）")
        except Exception as e:
            print(f"准备步进电机状态时出错: {e}")
            print("继续尝试...")
            time.sleep(1.0)

    def disable_steppers(self):
        """禁用所有步进电机（节省能源和减少热量）"""
        print("禁用步进电机...")
        try:
            # M18 或 M84 命令可以禁用步进电机（两者效果相同）
            self.send_gcode("M18")  # 或使用 M84
            print("步进电机已禁用")
        except Exception as e:
            print(f"禁用步进电机时出错: {e}")
        time.sleep(0.5)

    def set_absolute_positioning(self):
        self.send_gcode("G90")
        time.sleep(0.5)

    def set_relative_positioning(self):
        print("设置相对定位模式...")
        # 先确保通信稳定
        try:
            # 先发送一个简单的查询命令
            self.send_gcode("M114")  # 查询位置
            # 然后设置相对定位
            self.send_gcode("G91")
            time.sleep(0.8)  # 增加等待时间
            print("相对定位模式设置成功")
            return True
        except Exception as e:
            print(f"设置相对定位模式失败: {e}")
            return False

    def set_current_position(self, x=0, y=0, z=0, i=0, j=0, k=0, u=0, v=0, w=0, e=0):
        """Set the current position for all 10 axes."""
        cmd = f"G92 X{x} Y{y} Z{z} I{i} J{j} K{k} U{u} V{v} W{w} E{e}"
        self.send_gcode(cmd)
        time.sleep(0.5)
        self.get_position()

    def get_position(self):
        self.send_gcode("M114")
        #print("Current position:")
        #for axis, value in self.current_position.items():
            #print(f"  {axis}: {value:.2f}")
        return self.current_position

    def select_extruder(self, index=0):
        """Select extruder tool (T command)."""
        self.send_gcode(f"T{index}")
        time.sleep(0.2)

    def move_motor_by_steps(self, motor_name, step_count, feedrate=1000):
        """Move a specified motor by step count."""
        valid_motors = ['X', 'Y', 'Z', 'I', 'J', 'K', 'U', 'V', 'W', 'E']
        if motor_name not in valid_motors:
            raise ValueError(f"Invalid motor: {motor_name}. Must be one of: {', '.join(valid_motors)}")

        mm = step_count / self.steps_per_mm[motor_name]

        # For E axis, select extruder first (T0 for single extruder)
        if motor_name == 'E':
            self.select_extruder(0)  # 选择挤出机0
            axis = 'E'
        else:
            axis = motor_name

        self.set_relative_positioning()
        gcode = f"G1 {axis}{mm:.4f} F{feedrate}"
        print(f"\nMoving {motor_name} by {step_count} steps ({mm:.3f} mm)...")
        self.send_gcode(gcode)
        time.sleep(1)
        # return self.get_position()

    def move_to(self, x=None, y=None, z=None, i=None, j=None, k=None, u=None, v=None, w=None, e=None, feedrate=1000):
        """Move to absolute position for any of the 10 axes."""
        cmd = "G1"
        if x is not None: cmd += f" X{x}"
        if y is not None: cmd += f" Y{y}"
        if z is not None: cmd += f" Z{z}"
        if i is not None: cmd += f" I{i}"
        if j is not None: cmd += f" J{j}"
        if k is not None: cmd += f" K{k}"
        if u is not None: cmd += f" U{u}"
        if v is not None: cmd += f" V{v}"
        if w is not None: cmd += f" W{w}"
        if e is not None: cmd += f" E{e}"
        cmd += f" F{feedrate}"
        print(f"\nExecuting move command: {cmd}")
        self.send_gcode(cmd)
        time.sleep(1)
        # return self.get_position()

    def home(self, axes=None, wait=True):
        """Home axes using G28.
        - axes: list like ['X','Y','Z'] or ['X','Y','Z','U','V','W','I','J','K'].
                 If None, home all supported axes per firmware config.
        - wait: send M400 to wait until motion completes.
        """
        if axes is None:
            cmd = "G28"
        else:
            # Ensure unique, valid axis letters and keep order
            valid = {'X','Y','Z','I','J','K','U','V','W'}
            req = [a for a in axes if a in valid]
            if not req:
                cmd = "G28"
            else:
                cmd = "G28 " + " ".join(req)
        print(f"\nHoming with: {cmd}")
        resp = self.send_gcode(cmd)
        if wait:
            self.send_gcode("M400")
        time.sleep(0.3)
        self.get_position()
        return resp

    def home_xyz(self, wait=True):
        """Convenience: Home only X, Y, Z."""
        return self.home(['X','Y','Z'], wait=wait)

    def home_all_linear(self, wait=True):
        """Convenience: Home all 9 linear axes (if endstops are configured)."""
        return self.home(['X','Y','Z','U','V','W','I','J','K'], wait=wait)

    def zero_extruder(self):
        """Set E position to 0 without homing (extruder typically has no endstop)."""
        self.send_gcode("G92 E0")

    def close(self):
        self.ser.close()


def main():
    # 使用默认参数创建控制器，自动启用步进电机
    controller = MotorController()  # 已经自动启用步进电机
    try:
        print("\nInitializing...")
        controller.send_gcode("M211 S0")  # Disable software endstops
        controller.set_absolute_positioning()
        controller.set_current_position(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        # Move core axes
        #controller.move_to(x=0, y=0, z=-1000000)
        #controller.move_to(e=-8000)
        #controller.move_motor_by_steps('Y', 800)
        #time.sleep(3)
        #controller.move_motor_by_steps('Y', 2000)
        #for i in range(6):            controller.move_motor_by_steps('I', 300000, 2000);            controller.move_motor_by_steps('K', -150000, 2000)

        #controller.move_motor_by_steps('Z', 5000, 2000)
        #controller.move_motor_by_steps('J', 10000, 1000) #test the volume of the new
        #time.sleep(3)
        controller.move_motor_by_steps('I', 400000, 2000)
        #controller.move_motor_by_steps('Z', -500000, 2000)
        controller.move_motor_by_steps('K', -150000, 2000)
        controller.move_motor_by_steps('I', 300000, 1000)
        #controller.move_motor_by_steps('Z', -500000, 2000)
        controller.move_motor_by_steps('K', -150000, 2000)
        controller.move_motor_by_steps('I', 300000, 2000)
        #controller.move_motor_by_steps('Z', -500000, 2000)
        controller.move_motor_by_steps('K', -150000, 2000)
        controller.move_motor_by_steps('I', 300000, 2000)
        #controller.move_motor_by_steps('Z', -500000, 2000)
        controller.move_motor_by_steps('K', -150000, 2000)
        controller.move_motor_by_steps('I', 300000, 2000)
        #controller.move_motor_by_steps('Z', -500000, 2000)
        controller.move_motor_by_steps('K', -150000, 2000)

        #controller.move_motor_by_steps('Y', 1053, 2000)
        #time.sleep(20)
        
        #time.sleep(3)       
        #controller.move_motor_by_steps('Y', 2000)
        #time.sleep(3)
        
        #time.sleep(1)
        #controller.move_motor_by_steps('J', 150000, 2500)
        #controller.move_motor_by_steps('Y', -1000)

        # Return to origin
        #controller.set_absolute_positioning()
        #controller.move_to(x=0, y=0, z=0)
        #controller.move_to(e=0)

    finally:
        print("\nDisabling steppers and closing connection...")
        controller.disable_steppers()
        controller.close()


if __name__ == "__main__":
    main()