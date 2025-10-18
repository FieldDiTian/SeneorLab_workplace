import serial
import time

class MotorController:
    def __init__(self, port='COM4', baudrate=115200):
        self.ser = serial.Serial(port, baudrate, timeout=2)
        time.sleep(2)  # Wait for board to initialize

        # Track positions for all motors
        self.current_position = {'X': 0, 'Y': 0, 'Z': 0}
        for i in range(5):
            self.current_position[f'E{i}'] = 0

        # Steps per mm configuration
        self.steps_per_mm = {
            'X': 80,
            'Y': 80,
            'Z': 400,
            **{f'E{i}': 500 for i in range(5)}  # E0-E4
        }

    def send_gcode(self, cmd):
        # print(f">> {cmd}")
        self.ser.write((cmd + "\n").encode())
        self.ser.flush()
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
            if line.lower().startswith("ok"):
                break
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

    def set_current_position(self, x=0, y=0, z=0, e_values=None):
        cmd = f"G92 X{x} Y{y} Z{z}"
        if e_values is None:
            e_values = {f'E{i}': 0 for i in range(5)}
        for i in range(5):
            cmd += f" E{e_values.get(f'E{i}', 0)}"
        self.send_gcode(cmd)
        time.sleep(0.5)
        self.get_position()

    def get_position(self):
        self.send_gcode("M114")
        #print("Current position:")
        #for axis, value in self.current_position.items():
            #print(f"  {axis}: {value:.2f}")
        return self.current_position

    def select_extruder(self, index):
        if not (0 <= index <= 4):
            raise ValueError("Extruder index must be between 0 and 4.")
        self.send_gcode(f"T{index}")
        time.sleep(0.2)

    def move_motor_by_steps(self, motor_name, step_count, feedrate=1000):
        """Move a specified motor by step count."""
        valid_motors = ['X', 'Y', 'Z'] + [f'E{i}' for i in range(5)]
        if motor_name not in valid_motors:
            raise ValueError(f"Invalid motor: {motor_name}. Must be one of: {', '.join(valid_motors)}")

        mm = step_count / self.steps_per_mm[motor_name]

        if motor_name.startswith("E"):
            index = int(motor_name[1])
            self.select_extruder(index)
            axis = "E"
        else:
            axis = motor_name

        self.set_relative_positioning()
        gcode = f"G1 {axis}{mm:.4f} F{feedrate}"
        print(f"\nMoving {motor_name} by {step_count} steps ({mm:.3f} mm)...")
        self.send_gcode(gcode)
        time.sleep(1)
        # return self.get_position()

    def move_to(self, x=None, y=None, z=None, e=None, feedrate=1000):
        cmd = "G1"
        if x is not None: cmd += f" X{x}"
        if y is not None: cmd += f" Y{y}"
        if z is not None: cmd += f" Z{z}"
        if e is not None: cmd += f" E{e}"
        cmd += f" F{feedrate}"
        print(f"\nExecuting move command: {cmd}")
        self.send_gcode(cmd)
        time.sleep(1)
        # return self.get_position()

    def close(self):
        self.ser.close()


def main():
    controller = MotorController()
    try:
        print("\nInitializing...")
        controller.enable_steppers()
        controller.send_gcode("M211 S0")  # Disable software endstops
        controller.set_absolute_positioning()
        controller.set_current_position(0, 0, 0, {f'E{i}': 0 for i in range(5)})

        # Move core axes
        #controller.select_extruder(3)  
        #print("11111111111111111111111111111111111111111111111111")
        #controller.move_to(x=0, y=0, z=-1000000)
        #print("22222222222222222222222222222222222222222222222222")
        #controller.move_to(e=-8000)
        #controller.move_motor_by_steps('Y', 800)
        #time.sleep(3)
        #controller.move_motor_by_steps('Y', 2000)
        #for i in range(6):            controller.move_motor_by_steps('E1', 300000, 2000);            controller.move_motor_by_steps('E3', -150000, 2000)

        #controller.move_motor_by_steps('Z', 5000, 2000)
        #controller.move_motor_by_steps('E2', 10000, 1000) #test the volume of the new
        #time.sleep(3)
        controller.move_motor_by_steps('E1', 400000, 2000)
        #controller.move_motor_by_steps('Z', -500000, 2000)
        controller.move_motor_by_steps('E3', -150000, 2000)
        controller.move_motor_by_steps('E1', 300000, 1000)
        #controller.move_motor_by_steps('Z', -500000, 2000)
        controller.move_motor_by_steps('E3', -150000, 2000)
        controller.move_motor_by_steps('E1', 300000, 2000)
        #controller.move_motor_by_steps('Z', -500000, 2000)
        controller.move_motor_by_steps('E3', -150000, 2000)
        controller.move_motor_by_steps('E1', 300000, 2000)
        #controller.move_motor_by_steps('Z', -500000, 2000)
        controller.move_motor_by_steps('E3', -150000, 2000)
        controller.move_motor_by_steps('E1', 300000, 2000)
        #controller.move_motor_by_steps('Z', -500000, 2000)
        controller.move_motor_by_steps('E3', -150000, 2000)

        #controller.move_motor_by_steps('Y', 1053, 2000)
        #time.sleep(20)
        
        #time.sleep(3)       
        #controller.move_motor_by_steps('Y', 2000)
        #time.sleep(3)
        
        #time.sleep(1)
        #controller.move_motor_by_steps('E2', 150000, 2500)
        #controller.move_motor_by_steps('Y', -1000)

        # Return to origin
        #controller.select_extruder(4)        # 选中 E4
        #controller.set_absolute_positioning()
        #controller.move_to(x=0, y=0, z=0)
        #controller.move_to(e=0)

    finally:
        print("\nDisabling steppers and closing connection...")
        controller.disable_steppers()
        controller.close()


if __name__ == "__main__":
    main()