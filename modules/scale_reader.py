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
    """
    读取电子秤重量值
    返回: float (重量克数) 或 None (读取失败)
    """
    if not ser.is_open: 
        return None
    
    try:
        # 只读取一行，避免阻塞
        if ser.in_waiting > 0:
            line_bytes = ser.readline()
            if line_bytes:
                line = line_bytes.decode('ascii', errors='ignore').strip()
                # 匹配数字（包括负数和小数）
                match = re.search(r"[-+]?\d*\.?\d+", line)
                if match:
                    return float(match.group(0))
        return None
    except Exception as e:
        print(f"    读取错误: {e}")
        return None

def wait_for_stable_weight(port='COM5', stable_duration=5, threshold=0.1, timeout=20):
    """
    等待电子秤读数稳定
    参数:
        stable_duration: 需要保持稳定的时间(秒)，默认5秒
        threshold: 相邻读数变化阈值(克)，默认0.1g
        timeout: 超时时间(秒)，默认20秒
    """
    try:
        print(f"    正在连接电子秤 ({port})...")
        ser = open_scale(port)
        print(f"    电子秤已连接")
    except Exception as e:
        print(f"Warning: Scale not found ({e}). Using 0.0g")
        return 0.0

    stable_readings = []  # 稳定期间的读数
    last_reading = None
    stable_start_time = None
    start_time = time.time()
    
    try:
        print(f"    等待读数稳定 (连续{stable_duration}秒变化<{threshold}g)...")
        while (time.time() - start_time) < timeout:
            w = read_weight(ser)
            if w is not None:
                # 检查与上一次读数的变化
                if last_reading is not None:
                    change = abs(w - last_reading)
                    
                    if change <= threshold:
                        # 读数变化在阈值内，视为稳定
                        if stable_start_time is None:
                            # 刚开始稳定
                            stable_start_time = time.time()
                            stable_readings = [last_reading, w]
                            print(f"    开始稳定: {w:.2f}g")
                        else:
                            # 继续稳定
                            stable_readings.append(w)
                            elapsed = time.time() - stable_start_time
                            print(f"    稳定中: {w:.2f}g (已稳定 {elapsed:.1f}/{stable_duration}s)", end='\r')
                            
                            # 检查是否已经稳定足够长时间
                            if elapsed >= stable_duration:
                                avg = mean(stable_readings)
                                print(f"\n    ✓ 稳定读数: {avg:.2f}g (基于{len(stable_readings)}个读数)")
                                return avg
                    else:
                        # 读数变化超过阈值，重置稳定状态
                        if stable_start_time is not None:
                            print(f"\n    不稳定: {w:.2f}g (变化{change:.2f}g > {threshold}g)，重新开始")
                        stable_start_time = None
                        stable_readings = []
                else:
                    print(f"    首次读数: {w:.2f}g")
                
                last_reading = w
            
            time.sleep(0.2)  # 每0.2秒读取一次
        
        # 超时处理
        if stable_readings:
            avg = mean(stable_readings)
            print(f"\n    ⚠ 超时，使用稳定期间的平均值: {avg:.2f}g (基于{len(stable_readings)}个读数)")
            return avg
        elif last_reading is not None:
            print(f"\n    ⚠ 超时，使用最后读数: {last_reading:.2f}g")
            return last_reading
        else:
            print(f"\n    ⚠ 超时且无读数，返回0.0g")
            return 0.0
    finally:
        ser.close()

def calculate_mass_change(previous_weight, current_weight, min_threshold=0.05):
    """
    计算质量变化，如果变化小于阈值则记为0
    参数:
        previous_weight: 之前的重量(g)
        current_weight: 当前重量(g)
        min_threshold: 最小变化阈值(g)，默认0.05g
    返回:
        float: 质量变化(g)，小于阈值时返回0.0
    """
    mass_change = current_weight - previous_weight
    
    if abs(mass_change) < min_threshold:
        print(f"     质量变化过小 ({mass_change:.4f}g < {min_threshold}g)，记为0.0g")
        return 0.0
    else:
        return mass_change

if __name__ == "__main__":
    print("Testing Scale...")
    w = wait_for_stable_weight()
    print(f"Result: {w} g")