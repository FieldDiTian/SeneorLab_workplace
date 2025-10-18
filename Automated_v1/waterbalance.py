import serial
import time

# Adjust port to match your system (e.g. 'COM3' on Windows or '/dev/ttyUSB0' on Linux)
arduino = serial.Serial('COM6', 9600, timeout=2)
time.sleep(2)  # Wait for Arduino to initialize

def send_command(cmd):
    print(f">> Sending: {cmd}")
    arduino.write((cmd + '\n').encode())
    time.sleep(0.1)

def add_water():
    send_command("CW")       # Set direction to clockwise
    send_command("STEP20000")
    send_command("STEP20000")
    send_command("STEP20000")
    send_command("STEP4655")  # Move 200 steps

    time.sleep(5)

    #send_command("CCW")      # Set direction to counterclockwise
    #send_command("STEP2000")  # Move 200 steps

add_water()
arduino.close()