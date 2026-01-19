# Automated Chemical Control System

## Quick Start
Read sections 3, 5, and 7 of this document to get started.

## 1. System Overview
This system is an automated control platform for chemical experiments, designed to precisely control the addition of various chemical reagents, weighing, mixing, and Electrochemical Impedance Spectroscopy (EIS) detection.
The system integrates a ten-axis motor control system, high-precision electronic scale reading, and Digilent Analog Discovery (EIS) module.
The system adopts a distributed design. The main control program is only responsible for executing the control loop according to the table content. The specific functions in the control loop are encapsulated in modules (weighing, motor drive, EIS measurement). Experimenters need to design the experimental parameter table for each experiment. See section 7 for table design instructions.

## 2. Hardware Architecture
The system is based on a custom 10-axis motion control board (COM8) controlled by Marlin firmware.

### Axis Mapping

| Axis | Function | Chemical | Notes |
| :--- | :--- | :--- | :--- |
| **X** | Stepper Motor 1 | NaCl (Sodium Chloride) | Solution pumping |
| **Y** | Stepper Motor 2 | KCl (Potassium Chloride) | Solution pumping |
| **Z** | Stepper Motor 3 | Urea | Solution pumping |
| **U** | Stepper Motor 4 | Na_lactate (Sodium Lactate) | Solution pumping |
| **V** | Stepper Motor 5 | NH4Cl (Ammonium Chloride) | Solution pumping |
| **W** | Stepper Motor 6 | CaCl2 (Calcium Chloride) | Solution pumping |
| **I** | Stepper Motor 7 | Glucose | Solution pumping |
| **J** | Water Pump | WATER (Distilled Water) | Cleaning and water supply |
| **K** | Water Pump | EXTRACT (Waste Liquid) | Extract waste liquid, high flow rate |
| **E** | Water Pump | MIX (Gas Mixing) | Gas stirring or mechanical stirring |

### Sensors
- **Electronic Scale**: Connected via serial port (COM5) to read beaker weight in real-time.
- **EIS Device**: Digilent Analog Discovery 2/3 for electrochemical measurements.

## 3. Software Architecture
File structure:
```
SeneorLab_workplace/
├── central_control.py      # [Main Control] Main control program, calls module functions, implements control loop, reads/writes tables, outputs and saves EIS data
├── motor_test.py           # [Debug] Debug motors independently, includes independent control for all ten axes
├── refill_syringe.py       # [Tool] Refill function, repeatedly executes forward/backward 100 steps after selecting motor and task until user presses Enter
├── modules/                # [Module Library] Encapsulates control system module functions
│   ├── motorcontroller.py  # Stepper motor and water pump control (G-code communication)
│   ├── eis_module.py       # EIS measurement module
│   └── scale_reader.py     # Electronic scale serial port reading module
├── Data/                   # [Data] EIS images and data, stored by date classification
├── log/                    # [Log] Workspace changes and daily work records
├── Tables/                 # [Configuration] Test tables for each experiment and table generation program
└── __pycache__/            # [Ignore] Python runtime cache files
```

### Program Function Description
*** VERY IMPORTANT: Before running any program, ensure it is the only program running on the system, meaning no other program is occupying the serial port. If another program is occupying serial port 8 when another program accesses serial port 8, it will cause the mainboard to crash. ***
*** VERY IMPORTANT: Please run the stepper motor by calling motor_controller. Di Tian has written protection programs. Directly controlling the mainboard with G-code is very easy to cause the mainboard to crash (for example, when the previous command on the mainboard has not been processed yet and the user inputs the next command). ***
*** The red indicator light in the center of the mainboard should remain constantly on, with a bright red status. If it is dark red, it means the mainboard has crashed and entered DFU mode. ***

1.  **`central_control.py` (Main Control Program)**
    - Calls various module functions to implement the control loop.
    - Reads and parses experimental parameters from Excel tables.
    - Coordinates the workflow of motors, electronic scale, and EIS modules.
    - Outputs and saves EIS data and experiment logs.

Usage Instructions: After running the program, it will automatically add substances and measure according to the existing table in the workspace, line by line, until the last line of the table is completed. Experimental data will be stored in the data folder with the same name as the table.

2.  **`motor_test.py` (Motor Debug)**
    - Debug motor functions independently.
    - Includes independent control interfaces for all ten axes.
    - Used to test and verify the running status of each axis motor.

Usage Instructions: Run the program directly, and it will ask you to select the axis to debug. Enter the number of steps.

3.  **`refill_syringe.py` (Refill Tool)**
    - Refill and cleaning functions.
    - Repeatedly executes forward/backward 100 steps after selecting motor and task.
    - Press Enter to terminate the program.

Usage Instructions: Run the program directly. The program will ask which motor to execute. After entering the number, the program will ask whether to aspirate or dispense. After confirmation, the program will continuously send instructions to the motor to step 100 units **until the user presses Enter to terminate the program**.

### Module Description

1.  **`modules/motorcontroller.py` (Motor Control)**
    - Encapsulates low-level control of stepper motors and water pumps.
    - Handles G-code instruction communication (G1, G90/G91, etc.).
    - Provides motion interfaces and waiting logic for each axis.
    - Directly sending G-code to the motor without calling motorcontroller may cause mainboard crashes.

2.  **`modules/scale_reader.py` (Weighing Module)**
    - Reads serial port data from the electronic scale.
    - Implements `wait_for_stable_weight()` function to ensure stable readings before recording.
    - Provides real-time weight monitoring function.

3.  **`modules/eis_module.py` (EIS Measurement)**
    - Calls `dwfpy` to control Digilent Analog Discovery device.
    - Executes electrochemical impedance spectroscopy frequency scanning.
    - Generates and saves `.txt` data files and `.png` charts.

---

## 4. Automated Workflow

The main program (`central_control.py`) strictly follows the following 9-step process:

1.  **Extract (Clear Waste Liquid)**
    - Waste liquid pump runs at full speed (30,000 steps) to ensure the workbench residual liquid is drained.
2.  **Wash Cycles (Clean Workbench)**
    - Execute 3 cycles: pump in 30mL of water -> drain waste liquid.
3.  **Read Config (Read Configuration)**
    - Read 8 data points from the current experiment row in Excel (7 chemical substances + water).
    - Data directly represents **volume (mL)**.
4.  **Tare (Initial Weighing)**
    - Record empty cup weight as baseline.
5.  **Dispense Loop (Liquid Addition Loop)**
    - Add liquids in order (NaCl -> ... -> Glucose -> Water).
    - Unified conversion standard: **1000 steps/mL**.
6.  **Weighing (Weight Recording)**
    - After adding each liquid, wait for stable readings and record the actual increased mass (g).
7.  **Mixing**
    - Start mixing motor (E-axis) for stirring.
8.  **EIS Test (Measurement)**
    - Scan and record impedance data.
    - Save detailed logs containing "target volume" and "actual mass".
9.  **Loop (Next Experiment)**
    - Complete current experiment and prepare for the next row of data.

---

## 5. Usage Guide / Quick Start

1. According to the instructions in Tables, prepare the table file and configure the solutions.
2. Use the refill function to fill the syringes. Remember: ***If the user does not press Enter, the program will not stop.***
3. Name the table with today's date and place it in the workspace (in the same path as central_controller). Ensure there is only one table in the workspace. If there is someone else's table in the workspace, please help them put the table in the Tables folder.
4. Ensure all syringes are filled with liquid, the water tank connected to the water pump has sufficient volume, the waste water discharge tube is placed in the waste water tank, the 7-holes bracket is aligned with the test area, all chemical substance water pipes are firmly connected, and the mixing water pump tube is aimed at the center of the measurement module.
5. Run central_control.py directly, observe the test bench working status. You can leave when the data corresponding to your table appears in the Data folder.
6. If you modify the program or test data using the workstation, please leave a work trace in the log file.

## 6. Parameter Configuration

Key parameters can be adjusted at the beginning of `central_control.py`:
The current parameters were tested by Di Tian and can be used normally, but it is uncertain whether there will be changes in the future.

```python
STEPS_PER_ML = -20      # Global step conversion ratio
SPEED = { ... }          # Running speed of each motor
CONFIG = {
    'WASH_VOLUME': 30.0,    # Cleaning water volume
    'EXTRACT_STEPS': 3000,  # Waste liquid extraction intensity
    'WASH_CYCLES': 3,       # Number of cleaning cycles
    ...
}
```

## 7. Table Configuration Instructions

Before calling the main control program, ensure there is only one table file in the workspace. If there is a table from the previous experimenter, please help them move the table into Tables.

- Name the table with today's date. The data corresponding to the table will be stored in a folder with the same name in the Data folder.
- Do not change the order of chemical substances in the sample table. The program reads table data from left to right in order. Changing the order will cause program control errors.
- Cell values should be either 0, or if not 0, at least 3mL and an integer. Control instructions less than 3mL will cause the motor to barely move, and no substance will be added to the system.
- Each row of cells should not exceed 25mL but should be as close to 25mL as possible, because exceeding 25mL will cause the test bench to leak.
- Each column of cells should not exceed 200mL but should be as close to 200mL as possible, because the maximum capacity of the syringe is 200mL.
- Table rows can be extended, but columns must not be extended.
- The first column of the table is the experimental group number, and from the second column onwards are chemical substances, in the same order as the sample table.
- The generate_random_table.py in Tables will generate random tables that meet program requirements. You can also copy and paste the above configuration instructions to generative AI to help you create tables.

---

**Last Updated**: January 16, 2026
**Maintainer**: Di Tian
