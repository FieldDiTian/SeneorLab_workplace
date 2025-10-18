# scale_reader.py

import serial
import time
import re  # 导入正则表达式模块

def open_scale(port='COM5',
               baudrate=9600,
               timeout=1):
    """
    Open and return a configured serial.Serial instance for the scale.
    """
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout
        )
        # Give the scale time to initialize/reset
        time.sleep(2)
        print(f"Reading......")
        return ser
    except serial.SerialException as e:
        print(f"Error opening {port}: {e}")
        raise

def read_weight(ser):
    """
    Read one line of ASCII data from the scale serial port,
    extract the first number it contains, and return it as a float in grams.
    """
    raw = ser.readline()
    try:
        line = raw.decode('ascii').strip()
    except UnicodeDecodeError:
        line = raw.decode('latin-1', errors='replace').strip()

    # 正则表达式提取第一个浮点数（包含可选的正负号）
    match = re.search(r"[-+]?\d*\.\d+|\d+", line)
    if match:
        return float(match.group(0))

    raise ValueError(f"Cannot parse weight from '{line}'")

def main():
    """
    Continuously read and print weight readings until Ctrl-C.
    """
    ser = open_scale()
    print("Reading weight. Press Ctrl-C to exit.")
    try:
        while True:
            try:
                w = read_weight(ser)
                print(f"Weight: {w:.4f} g")
            except ValueError as ve:
                print(f"Warning: {ve}")
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        ser.close()
        print("Serial port closed.")
 
if __name__ == "__main__":
    main()
