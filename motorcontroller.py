import serial
import time

class MotorController:
    def __init__(self, port='COM8', baudrate=115200, auto_enable=True):
        # Remember connection params for possible reopen
        self.port = port
        self.baudrate = baudrate
        self.ser = serial.Serial(port, baudrate, timeout=2, write_timeout=2)
        time.sleep(2)  # Wait for board to initialize
        
        # 如果设置了auto_enable，自动启用步进电机
        if auto_enable:
            self.enable_steppers()
            time.sleep(0.3)

        # Track positions for all motors (10 axes: X, Y, Z, I, J, K, U, V, W, E0)
        self.current_position = {
            'X': 0, 'Y': 0, 'Z': 0,
            'I': 0, 'J': 0, 'K': 0,
            'U': 0, 'V': 0, 'W': 0,
            'E': 0  # E0 only
        }

        # Steps per mm configuration (from Marlin Configuration.h)
        # DEFAULT_AXIS_STEPS_PER_UNIT: { 80, 80, 400, 80, 80, 80, 80, 80, 80, 500 }
        # Order: X, Y, Z, I, J, K, U, V, W, E0
        self.steps_per_mm = {
            'X': 80,   # Motor1
            'Y': 80,   # Motor2
            'Z': 80,   # Motor3
            'I': 80,   # Motor7
            'J': 80,   # Motor8
            'K': 80,   # Motor9
            'U': 80,   # Motor4
            'V': 80,   # Motor5
            'W': 80,   # Motor6
            'E': 500   # Motor10 (E0 extruder)
        }

    def _reopen(self):
        try:
            self.ser.close()
        except Exception:
            pass
        time.sleep(0.3)
        self.ser = serial.Serial(self.port, self.baudrate, timeout=2, write_timeout=2)
        time.sleep(1.0)

    def send_gcode(self, cmd):
        # print(f">> {cmd}")
        # Robust write with retry and CRLF line ending (some devices expect \r\n)
        payload = (cmd + "\r\n").encode(errors="ignore")
        for attempt in range(2):
            try:
                # Clear any stale buffers before sending
                try:
                    self.ser.reset_output_buffer()
                    self.ser.reset_input_buffer()
                except Exception:
                    pass
                self.ser.write(payload)
                self.ser.flush()
                break
            except Exception as e:
                if attempt == 0:
                    print(f"[WARN] write failed on '{cmd}', attempting reopen... ({e})")
                    self._reopen()
                else:
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

    def enable_steppers(self):
        self.send_gcode("M17")
        time.sleep(0.5)

    def disable_steppers(self):
        self.send_gcode("M18")
        time.sleep(0.5)

    def set_absolute_positioning(self):
        self.send_gcode("G90")
        time.sleep(0.5)

    def set_relative_positioning(self):
        self.send_gcode("G91")
        time.sleep(0.5)

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