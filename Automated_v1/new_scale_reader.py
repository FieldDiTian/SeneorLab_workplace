import serial, time

def probe_protocol(port="COM5", baud=9600):
    ser = serial.Serial(port, baud, timeout=0.5)
    ser.reset_input_buffer()
    print("Sending ENQ...")
    ser.write(b'\x05')
    time.sleep(0.1)
    ser.write(b'SI\r\n')  # 再发一次 SI
    time.sleep(0.5)
    buffer = ser.read(200)
    print("Raw response bytes:", list(buffer))
    try:
        print("As ASCII:", buffer.decode('ascii', errors='replace'))
    except:
        pass
    ser.close()

if __name__ == "__main__":
    probe_protocol()
