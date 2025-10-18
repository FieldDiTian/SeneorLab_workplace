import os
import pandas as pd
from automated_eis_pipeline_updated import automated_pipeline
from motorcontroller import MotorController
import serial
import time

# Adjust port to match your system (e.g. 'COM3' on Windows or '/dev/ttyUSB0' on Linux)
#arduino = serial.Serial('COM6', 9600, timeout=2)
#time.sleep(2)  # Wait for Arduino to initialize


#def send_command(cmd):
#    print(f">> Sending: {cmd}")
#    arduino.write((cmd + '\n').encode())
#    time.sleep(0.1)

#def add_water():
#    send_command("CW")       # Set direction to clockwise
#    send_command("STEP20000")
#    send_command("STEP20000")
#    send_command("STEP20000")
#    send_command("STEP4655")  

# Set the folder where the Excel files are located
excel_folder = r"c:/Users/pmut/Desktop/Kang/Automated_v1"
print("Looking for Excel files in:", excel_folder)

# List all .xlsx files, excluding temporary files like '~$filename.xlsx'
excel_files = [
    f for f in os.listdir(excel_folder)
    if f.endswith('.xlsx') and not f.startswith('~$')
]

print("Excel files found:", excel_files)

#sample test

print(automated_pipeline(80, 8, 40))
#add_water()

# Loop through each Excel file
for file in excel_files:
    file_path = os.path.join(excel_folder, file)
    print(f"\nReading file: {file_path}")
    df = pd.read_excel(file_path)
    i = 1
    # Loop through each row in the Excel file
    for index, row in df.iterrows():

        if len(row) >= 3:
            # Use iloc to access values by position, not label
            print(f"---------- Cycle {i} ----------")
            a, b, c = row.iloc[0], row.iloc[1], row.iloc[2]
            print(automated_pipeline(a, b, c))
            #add_water()
            #print(f"The water balance of Cycle {i} finished!")
        else:
            print(f"Row {index + 1} has less than 3 columns. Skipped.")
        i = i + 1

arduino.close()
print("\n✅ Finished all cycles!")
