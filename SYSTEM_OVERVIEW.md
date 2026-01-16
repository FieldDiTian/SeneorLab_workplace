# 自动化化学控制系统 (Automated Chemical Control System)

## 1. 系统概述 (System Overview)

本系统是一个用于自动化化学实验的控制平台，旨在精确控制多种化学试剂的添加、称重、混匀及电化学阻抗谱 (EIS) 检测。
系统集成了十轴电机控制系统、高精度电子秤读取以及 Digilent Analog Discovery (EIS) 模块。

核心功能：
- **自动配液**：控制7种化学物质 + 水的精确添加。
- **闭环反馈**：通过电子秤实时读取添加质量。
- **自动清洗**：实验前后的自动化工作台清洗流程。
- **EIS检测**：全自动电化学数据采集与绘图。
- **数据记录**：自动保存详细的质量数据和阻抗谱数据。

---

## 2. 硬件架构 (Hardware Architecture)

系统基于 Marlin 固件控制的定制 10 轴运动控制板。

### 轴映射 (Axis Mapping)

| 轴 (Axis) | 功能 (Function) | 对应物质 (Chemical) | 备注 (Notes) |
| :--- | :--- | :--- | :--- |
| **X** | 蠕动泵 1 | NaCl (氯化钠) | 溶液泵入 |
| **Y** | 蠕动泵 2 | KCl (氯化钾) | 溶液泵入 |
| **Z** | 蠕动泵 3 | Urea (尿素) | 溶液泵入 |
| **U** | 蠕动泵 4 | Na_lactate (乳酸钠) | 溶液泵入 |
| **V** | 蠕动泵 5 | NH4Cl (氯化铵) | 溶液泵入 |
| **W** | 蠕动泵 6 | CaCl2 (氯化钙) | 溶液泵入 |
| **I** | 蠕动泵 7 | Glucose (葡萄糖) | 溶液泵入 |
| **J** | 水泵 | WATER (蒸馏水) | 清洗与补水 |
| **K** | 废液泵 | EXTRACT (废液) | 抽出废液，高流速 |
| **E** | 搅拌电机 | MIX (气体混匀) | 气体搅拌或机械搅拌 |

### 传感器
- **电子秤**: 通过串口 (COM5) 连接，实时读取烧杯重量。
- **EIS设备**: Digilent Analog Discovery 2/3，用于电化学测量。

---

## 3. 软件架构 (Software Architecture)

文件结构如下：

```
SeneorLab_workplace/
├── central_control.py      # [入口] 主控制程序，包含9步工作流逻辑
├── refill_syringe.py       # [工具] 手动控制各泵进行填充/清洗调试
├── modules/                # [模块库]
│   ├── motorcontroller.py  # 电机底层控制类 (G-code通信)
│   ├── eis_module.py       # EIS 测量与数据处理模块
│   └── scale_reader.py     # 电子秤串口读取模块
├── Data/                   # [数据] 实验数据自动保存目录
├── log/                    # [日志] 系统变更与运行日志
└── test_experiments.xlsx   # [输入] 实验参数配置文件
```

### 关键模块说明

1.  **`central_control.py` (核心)**
    - 程序的入口点。
    - 负责协调电机、电子秤和EIS模块。
    - 实现了**9步自动化工作流**。
    - 读取 Excel 表格并解析实验参数。

2.  **`modules/motorcontroller.py`**
    - 封装了 G-code 指令 (G1, G90/G91 等)。
    - 处理串口通信和运动等待逻辑。
    - 提供 `move_x`, `move_y`... 及通用的 `move_axis` 接口。

3.  **`modules/scale_reader.py`**
    - 读取电子秤的串口数据。
    - 实现了 `wait_for_stable_weight()` 函数，确保读数稳定后再记录。

4.  **`modules/eis_module.py`**
    - 调用 `dwfpy` 控制 AD2 设备。
    - 执行频率扫描 (Bode/Nyquist)。
    - 生成并保存 `.txt` 数据文件和 `.png` 图表。

---

## 4. 自动化工作流 (Workflow)

主程序 (`central_control.py`) 严格遵循以下 9 步流程：

1.  **清空废液 (Extract)**
    - 废液泵满速运行 (30000步)，确保工作台残留液体排空。
2.  **清洗工作台 (Wash Cycles)**
    - 循环执行 3 次：泵入 30mL 水 -> 抽干废液。
3.  **读取配置 (Read Config)**
    - 从 Excel 读取当前实验行的 8 个数据（7种化学物质 + 水）。
    - 数据直接代表**体积 (mL)**。
4.  **初始称重 (Tare)**
    - 记录空杯重量作为基准。
5.  **加液循环 (Dispense Loop)**
    - 按顺序 (NaCl -> ... -> Glucose -> Water) 加入液体。
    - 统一换算标准：**1000 steps/mL**。
6.  **称重记录 (Weighing)**
    - 每加入一种液体后，等待读数稳定，记录实际增加的质量 (g)。
7.  **混匀 (Mixin)**
    - 启动混合电机 (E轴) 进行搅拌。
8.  **EIS 测试 (Measurement)**
    - 扫描并记录阻抗数据。
    - 保存包含“目标体积”和“实际质量”的详细日志。
9.  **循环 (Next Experiment)**
    - 完成当前实验，准备下一行数据。

---

## 5. 使用指南 (Usage Guide)

### 环境准备
确保已安装 Python 3.13+ (Anaconda推荐) 及依赖库：
```bash
pip install pandas openpyxl pyserial numpy matplotlib dwfpy
```
*注意：`dwfpy` 需要 Digilent WaveForms Runtime 支持。*

### 运行实验
1.  编辑 `test_experiments.xlsx`，填写实验参数（8列数据，单位mL）。
2.  连接所有硬件（控制板 USB、电子秤串口、AD2 设备）。
3.  运行主程序：
    ```bash
    python central_control.py
    ```
    ```
    *(或者指定 python 路径: `/opt/anaconda3/bin/python3 central_control.py`)*

### 注意事项 (Constraints)
> [!WARNING]
> **器材容量限制 (Equipment Capacity)**: 
> 单个化学物质的容器/针管容量上限为 **200mL**。
> 因此，在一个 Excel 表单中，任意一种化学物质（如 NaCl, KCl 等）在所有实验组中的**累计使用量总和**不得超过 200mL。
> 请在设计实验表格时务必注意此限制。

### 调试工具
- 如果需要手动控制泵（例如填充管路或清洗单个通道），请运行：
  ```bash
  python refill_syringe.py
  ```

---

## 6. 参数配置 (Configuration)

在 `central_control.py` 头部可以调整关键参数：

```python
STEPS_PER_ML = 100      # 全局步数转换比例
SPEED = { ... }          # 各电机的运行速度
CONFIG = {
    'WASH_VOLUME': 30.0,    # 清洗水量
    'EXTRACT_STEPS': 3000, # 抽废液强度
    'WASH_CYCLES': 3,       # 清洗次数
    ...
}
```

---

**最后更新**: 2026-01-12
**维护者**: Di Tian
