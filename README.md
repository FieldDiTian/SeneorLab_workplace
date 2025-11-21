# 10-Axis Automated Lab System

## Overview

本项目是一个基于Python的自动化平台，用于精确配制化学溶液并对其进行电化学阻抗谱（EIS）分析。它使用10轴电机控制器精确分配多种溶液，通过电子秤进行闭环反馈，并利用Analog Discovery设备进行EIS测量。整个过程由一个简单的Excel文件驱动，可实现全自动的批量测试实验。

## 新手快速上手指南 (Quick Start for New Users)

作为新用户，你只需要完成以下三步即可运行整个系统。

### 第1步：准备实验计划表格

1.  在项目文件夹中，创建一个Excel文件（例如 `my_experiments.xlsx`）。
2.  打开文件，**不要添加任何表头或标题**。
3.  从 **第一行第一列** 开始，填入你希望配制的溶液中各种化学物质的 **最终浓度 (单位 mM)**。
4.  每一行代表一个独立的实验。
5.  **列的顺序必须固定**，如下所示：
    *   `A列`: NaCl 浓度
    *   `B列`: KCl 浓度
    *   `C列`: Urea 浓度
    *   `D列`: Na_lactate 浓度
    *   `E列`: NH4Cl 浓度
    *   `F列`: CaCl2 浓度
    *   `G列`: Glucose 浓度

**示例 `my_experiments.xlsx` 内容：**
```
20,4,20.5,10,0,0,0
50,5,10,0,2,0.5,0.1
```
*第一行代表系统将自动配制一个含有 20mM NaCl, 4mM KCl, 20.5mM Urea 和 10mM Na_lactate 的溶液。*

### 第2步：运行主程序

打开你的终端（Terminal 或命令行），确保你位于本项目的文件夹内，然后运行以下命令：
```bash
python3 central_control.py
```

### 第3步：获取结果

*   程序启动后，系统将全自动运行，你可以在终端窗口看到每一步的实时日志。
*   实验完成后，所有的数据和图表都会被保存在项目根目录下的 `Data/` 文件夹中。
*   文件名会自动包含浓度信息，方便你查找对应的结果。

## System Workflow

系统被设计为按顺序执行一个Excel表格中定义的一系列实验。

1.  **启动系统**: 在终端中执行主控制脚本来启动整个流程：
    ```bash
    python3 central_control.py
    ```

2.  **扫描与读取实验计划**:
    *   `central_control.py` 脚本会自动扫描项目根目录，寻找所有 `.xlsx` 格式的Excel文件。
    *   它会逐一打开找到的文件，并从第一行开始读取数据（文件不应包含表头）。
    *   每一行代表一个独立的实验。脚本会按预设的 `CHEMICAL_ORDER` 顺序（NaCl, KCl, Urea...）读取该行每一列的数值，这些数值代表了各种化学物质在最终溶液中的 **目标浓度 (mM)**。

3.  **执行单个实验流程 (`automated_pipeline.py`)**:
    对于从Excel中读取的每一组有效的目标浓度，系统会执行以下全自动流程：

    *   **a. 体积计算**: 根据目标浓度、母液浓度 (`CONC_INIT`) 和最终目标体积 (`FINAL_VOLUME`)，计算出需要分配的每种化学品母液的精确体积 (mL)。

    *   **b. 排空与去皮**:
        *   启动废液泵 (`EXTRACT`)，排空反应容器。
        *   调用 `scale_reader.py` 等待电子秤读数稳定，并将此重量记录为初始基准重量（去皮）。

    *   **c. 依次加液**:
        *   根据计算出的体积，按顺序驱动对应的化学品泵 (`NaCl`, `KCl` 等) 进行加液。
        *   `motorcontroller.py` 将体积(mL)转换为电机步数，并发送G-code指令精确移动电机。
        *   每加完一种液体，系统会暂停并等待电子秤读数稳定，以监控当前总重，并检查是否超出安全上限。

    *   **d. 加水补足 (闭环反馈)**:
        *   在所有化学品添加完毕后，系统会再次读取总重量。
        *   通过 `(当前总重 - 初始基准重量)` 计算出已添加溶液的实际重量。
        *   假设溶液密度接近1g/mL，系统会计算出需要添加多少去离子水才能达到最终目标体积 (`FINAL_VOLUME`)。
        *   驱动水泵 (`WATER`) 加入计算出的水量，完成最终定容。

    *   **e. 混合**: 驱动混合泵 (`MIX`，通常为空气泵) 一段时间，使溶液充分混匀。

    *   **f. EIS测量**:
        *   调用 `eis_module.py` 模块。
        *   `eis_module.py` 控制Analog Discovery设备，在预设的频率范围内进行扫描，测量并计算溶液的阻抗。

    *   **g. 保存数据**:
        *   测量完成后，`eis_module.py` 会在 `Data/` 目录下创建一个以当天日期命名的子文件夹。
        *   一个包含原始频率和阻抗数据的 `.txt` 文件被保存。
        *   两张分析图（Nyquist图和Bode图）以 `.png` 格式被保存。
        *   文件名会自动包含该次实验的各组分浓度，方便后续追溯。

    *   **h. 自动清洗**:
        *   系统进入清洗循环，重复多次“加水-混合-排空”的流程，以彻底清洗反应容器和电极，为下一次实验做准备。

4.  **循环与结束**:
    *   完成一次完整的实验（包括清洗）后，系统会暂停几秒钟，然后继续从Excel文件中读取下一行，重复步骤3。
    *   当所有文件中的所有行都被执行完毕后，程序结束。

## File Descriptions

*   `README.md`
    *   This documentation file.

*   `central_control.py`
    *   The main entry point for the system. It reads experiment definitions from an Excel file (`.xlsx`) and iterates through them, calling the `automated_pipeline` for each one.

*   `automated_pipeline.py`
    *   The core logic for a single experiment. It manages the entire sequence, from calculating volumes to dispensing, weighing, mixing, triggering the EIS test, and finally cleaning. It integrates all the hardware modules.

*   `motorcontroller.py`
    *   A low-level driver for the 10-axis Marlin-based motor control board. It handles serial communication, G-code commands, and provides a simple Python API to move each axis (e.g., `move_x()`, `move_y()`).

*   `scale_reader.py`
    *   A module for communicating with the electronic scale via a serial port. It provides functions to get stable weight readings, which are critical for the closed-loop feedback mechanism.

*   `eis_module.py`
    *   This module controls the Analog Discovery 2 to perform EIS measurements. It sweeps through a range of frequencies, records impedance, and then saves the raw data and generated plots (`Nyquist`, `Bode`) to a results folder.

## Setup & Dependencies

Ensure you have the required Python libraries installed. You can install them using pip:

```bash
pip install pandas pyserial numpy matplotlib pytz dwfpy
```
You also need to have the Digilent WaveForms SDK correctly installed for `dwfpy` to function.
