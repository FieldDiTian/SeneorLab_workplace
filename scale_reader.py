import serial
import time
import re
from statistics import mean

def open_scale(port='COM5', baudrate=9600, timeout=1):
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout
        )
        time.sleep(0.5)
        return ser
    except serial.SerialException as e:
        print(f"Scale Connection Error ({port}): {e}")
        raise

def read_weight(ser):
    if not ser.is_open: return 0.0
    ser.reset_input_buffer()
    lines = ser.readlines()
    if not lines: return None
    
    for raw in reversed(lines):
        try:
            line = raw.decode('ascii', errors='ignore').strip()
            match = re.search(r"[-+]?\d*\.\d+|\d+", line)
            if match: return float(match.group(0))
        except: continue
    return None

def wait_for_stable_weight(port='COM5', window=5, threshold=0.005, timeout=10):
    try:
        ser = open_scale(port)
    except Exception as e:
        print(f"Warning: Scale not found ({e}). Using 0.0g")
        return 0.0

    readings = []
    start_time = time.time()
    
    try:
        while (time.time() - start_time) < timeout:
            w = read_weight(ser)
            if w is not None:
                readings.append(w)
                if len(readings) > window:
                    readings.pop(0)
                    if (max(readings) - min(readings)) < threshold:
                        return mean(readings)
            time.sleep(0.1)
        return mean(readings) if readings else 0.0
    finally:
        ser.close()

if __name__ == "__main__":
    print("Testing Scale...")
    w = wait_for_stable_weight()
    print(f"Result: {w} g")