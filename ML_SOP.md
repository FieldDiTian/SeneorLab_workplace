# EIS 1D-CNN 机器学习训练 —— 标准操作流程 (SOP)

> **目标**: 通过 EIS（电化学阻抗谱）数据，使用 1D 卷积神经网络预测溶液中 7 种化学物质的实际称重质量。
>
> **7 种目标物质**: NaCl, KCl, Urea, Lac (乳酸), NH4Cl, CaCl₂, Glu (葡萄糖)

---

## 📁 项目结构

```
SeneorLab_workplace-main/
├── Tables/                       ← 实验配比表（输入）
│   ├── single/                   ← Phase 1: 单组分配比表
│   │   ├── 3-19.xlsx
│   │   ├── 20-27.xlsx
│   │   └── 28-30.xlsx
│   ├── double/                   ← Phase 2: 双组分配比表
│   │   ├── 2_pair_part1.xlsx
│   │   └── ... (115 个文件)
│   └── possion/                  ← Phase 3: Poisson 随机多组分配比表
│       └── possion-1.xlsx
├── table generate/               ← 配比表生成脚本
│   ├── onebyone.py               ← 生成单组分表
│   ├── 2.py                      ← 生成双组分表
│   └── possion.py                ← 生成 Poisson 随机表
├── central_control.py            ← 实验主控脚本（读表→配液→EIS）
├── Data/                         ← EIS 采集数据（输出）
│   ├── 20260119/                 ← 日期文件夹（自动扫描）
│   │   ├── EIS_Data_1_xxx.txt
│   │   └── ...
│   └── YYYYMMDD/                 ← 新数据会自动生成在新日期文件夹中
├── ml/                           ← 机器学习模块
│   ├── config.py                 ← 超参数配置（含阶段控制）
│   ├── dataset.py                ← 数据加载、预处理、阶段过滤
│   ├── model.py                  ← 1D CNN 模型定义
│   ├── train.py                  ← 训练脚本（支持续训 + 阶段）
│   ├── predict.py                ← 预测脚本
│   ├── requirements.txt          ← Python 依赖
│   ├── checkpoints/              ← 模型检查点（自动创建）
│   │   ├── best_model.pth        ← 最佳模型
│   │   ├── latest_model.pth      ← 最新模型（用于续训）
│   │   └── scalers.pkl           ← 数据标准化参数
│   └── logs/                     ← 训练日志（自动创建）
└── ML_SOP.md                     ← 本文件
```

---

## 🧭 总体工作流程

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  1. 生成表格  │ →  │  2. 运行实验  │ →  │  3. 训练模型  │ →  │  4. 预测验证  │
│  (Tables/)   │    │  (central_   │    │  (ml/train)  │    │  (ml/predict)│
│              │    │   control.py)│    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
   生成配比表 →       按表配液+EIS →       数据喂给CNN →        检验模型效果
```

### 渐进式训练策略（Curriculum Learning）

模型训练分 3 个阶段，让网络从简单到复杂逐步学习：

| 阶段 | 表格来源 | 数据特点 | 训练目标 | 最少样本量 |
|------|---------|---------|---------|-----------|
| **Phase 1: single** | `Tables/single/` | 每次只有 **1 种**化学物质变化 | 学会每种物质的 EIS 频谱"指纹" | 每种 ≥15 个 |
| **Phase 2: double** | `Tables/double/` | **2 种**化学物质同时存在 | 学会两两交互效应 | 每种组合 ≥10 个 |
| **Phase 3: possion** | `Tables/possion/` | **3-7 种**物质随机配比 | 学会真实多组分叠加 | ≥50 个 |

> **关键理念**: 不建议一开始就喂混合配比数据。先用 single 数据让模型学会每种物质的"指纹"，再逐步引入复杂度。

---

## 🔧 第一步：环境准备（仅首次）

### 1.1 激活 Conda 环境

```bash
conda activate DS176
```

### 1.2 安装依赖

```bash
pip install -r ml/requirements.txt
```

确认环境就绪：
```bash
python -c "import torch; import sklearn; import numpy; print('✅ 环境就绪')"
```

---

## 📐 第二步：生成实验配比表

配比表决定了实验时每种化学物质的注入体积（mL），注入总量约束为 30 mL。

### 2.1 生成单组分表（Phase 1）

单组分表：每次只有 1 种化学物质有注入体积，其余为 0，Water 补足。

```bash
cd "table generate"
python onebyone.py
```

- 输出在 `Tables/single/` 目录
- 已有的 3 个文件覆盖 3~30 mL 范围（每种化学物质各 28 个浓度点）

### 2.2 生成双组分表（Phase 2）

双组分表：两种化学物质同时有注入体积（3~30 mL），且总和 ≤30 mL。

```bash
python 2.py
```

- 输出在 `Tables/double/` 目录
- 所有 7 选 2 = 21 种两两组合
- 每个文件受每列累计 ≤200 mL 限制（与 stock 用量对齐）

### 2.3 生成 Poisson 随机表（Phase 3）

7 种化学物质按泊松分布随机配比，模拟真实汗液场景。

```bash
python possion.py
```

- 输出在 `Tables/possion/` 目录
- 每列累计用量逼近 200 mL（一次 stock 的量）
- 每行总和 ≤30 mL，单个非零项 ≥3 mL

### 2.4 表格文件格式

所有 xlsx 表格的列结构一致：

| Experiment | NaCl | KCl | Urea | Na_lactate | NH4Cl | CaCl2 | Glucose | Water |
|------------|------|-----|------|------------|-------|-------|---------|-------|
| 1          | 10   | 0   | 0    | 0          | 0     | 0     | 0       | 20    |
| 2          | 0    | 8   | 0    | 0          | 0     | 0     | 0       | 22    |

> 值为注入体积 (mL)，Water = 30 - 其余列之和

---

## 🧪 第三步：运行实验（采集 EIS 数据）

### 3.1 准备 Stock 溶液

根据 `Chemical.md` 中的配方配制 200 mL stock：
- NaCl 100 mM, KCl 20 mM, Urea 40 mM, Na_lactate 50 mM
- NH4Cl 10 mM, CaCl2 2.0 mM, Glucose 0.20 mM

### 3.2 运行实验主控

将对应阶段的 xlsx 表格放到项目根目录，运行：

```bash
cd /Users/field/Documents/SeneorLab_workplace-main
python central_control.py
```

系统会自动：
1. 读取 xlsx 表格中的配比方案
2. 控制注射泵按体积注入各化学物质
3. 天平记录实际称重质量
4. 运行 EIS 测量
5. 保存数据到 `Data/YYYYMMDD/` 文件夹

### 3.3 EIS 数据文件格式

每个 `.txt` 文件包含：

```
✅ Opened: Analog Discovery 3 (210415BD076B)
实际称重质量 (g):                          ← 训练标签来源
  NaCl=9.4800, KCl=0.0000, Urea=0.0000
  Lac=0.0000, NH4Cl=0.0000, CaCl2=0.0000, Glu=0.0000
  Water=4.3019
目标体积 (mL):
  NaCl=10.0, KCl=0.0, ...
--------------------------------------------------
1000000.0000, 21.1199, -82.5338, 85.1932, -75.6464    ← EIS 数据
869749.0026, 28.2549, -91.7011, 95.9554, -72.8749
...（共 101 行，5 列：频率, Re(Z), Im(Z), |Z|, 相位角）
```

> **训练标签** = `实际称重质量 (g)` 中的 7 种化学物质质量（天平实测值）

---

## 🚀 第四步：训练模型

### 4.1 Phase 1 训练：单组分数据

**前提**: `Data/` 目录中已有 single 表格生成的实验数据。

```bash
cd /Users/field/Documents/SeneorLab_workplace-main

# 首次训练（Phase 1: 仅使用单组分样本）
python ml/train.py --phase single
```

### 4.2 Phase 2 续训：加入双组分数据

**前提**: Phase 1 训练完成 + 已有 double 表格生成的实验数据。

```bash
# 续训（加载 Phase 1 的模型，使用 single+double 数据一起训练）
python ml/train.py --resume --phase double
```

### 4.3 Phase 3 续训：加入 Poisson 多组分数据

**前提**: Phase 2 训练完成 + 已有 possion 表格生成的实验数据。

```bash
# 续训（加载 Phase 2 的模型，使用全部数据训练）
python ml/train.py --resume --phase possion
```

### 4.4 后续持续训练（数据越来越多）

每次添加新的实验数据后，只需：

```bash
python ml/train.py --resume --phase all
```

> `--resume` 参数会自动加载上一次的最佳模型权重，不会从零开始。
> `--phase all` 使用全部数据（新旧数据一起训练），模型会越来越好。

### 4.5 调整训练参数（可选）

```bash
# 增加训练轮数
python ml/train.py --resume --phase all --epochs 1000

# 降低学习率（精细调整时使用）
python ml/train.py --resume --phase all --lr 0.0001

# 增大批大小
python ml/train.py --resume --phase all --batch_size 32
```

### 4.6 阶段过滤逻辑说明

| `--phase` 值 | 使用的数据 | 过滤规则 |
|--------------|-----------|---------|
| `single` | 仅单组分 | 恰好 1 种化学物质 > 0.01g 的样本 |
| `double` | 单组分 + 双组分 | 1~2 种化学物质 > 0.01g 的样本 |
| `possion` | 全部数据 | 不过滤（含 3+ 组分的多配比样本） |
| `all` | 全部数据 | 不过滤 |

> 阶段是**累进包含**的：double 包含 single 数据，possion/all 包含所有数据。

### 4.7 训练输出示例

```
📂 发现 3 个日期文件夹: ['20260119', '20260221', '20260305']
  📄 20260119: 23 个 EIS 数据文件
  📄 20260221: 50 个 EIS 数据文件
  📄 20260305: 30 个 EIS 数据文件
✅ 共加载 103 个有效样本
📋 训练阶段: DOUBLE
   过滤前: 103 样本 → 过滤后: 73 样本
📊 训练集: 58 样本, 验证集: 15 样本

🧠 模型参数量: 36,679
🖥️  设备: mps

🔄 续训模式: 从 epoch 150 继续, 历史最佳 val_loss=0.023456

[Epoch 0150] train_loss=0.018234 | val_loss=0.021345 | lr=1.00e-03 | 0.3s ✅ (best)
...

各化学物质 MAE (原始克数):
     NaCl:   0.0345 g
      KCl:   0.0412 g
     Urea:   0.0289 g
      Lac:   0.0567 g
    NH4Cl:   0.0398 g
    CaCl2:   0.0234 g
      Glu:   0.0156 g
```

---

## 🔍 第五步：预测 / 推理

### 5.1 对单个文件预测

```bash
python ml/predict.py Data/20260119/EIS_Data_1_NaCl_9.4800g_KCl_0.0000g_Urea_0.0000g_Lac_0.0000g_NH4Cl_0.0000g_CaCl2_0.0000g_Glu_0.0000g.txt
```

### 5.2 对整个文件夹预测

```bash
python ml/predict.py Data/20260119/
```

### 5.3 预测输出示例

```
📊 预测 23 个文件:

------------------------------------------------------------------------------------------
文件                                              NaCl      KCl     Urea      Lac    NH4Cl   CaCl2      Glu
------------------------------------------------------------------------------------------
EIS_Data_1_xxx.txt                              9.4512   0.0123   0.0045   0.0032   0.0067   0.0021   0.0011
  (实际值)                                       9.4800   0.0000   0.0000   0.0000   0.0000   0.0000   0.0000
  (误差)                                         0.0288   0.0123   0.0045   0.0032   0.0067   0.0021   0.0011
```

---

## 📋 实验者日常工作流程

```
┌─────────────────────────────────────────────────────────────┐
│  完整周期: 表格 → 实验 → 数据 → 训练 → 验证                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 选择当前阶段对应的 xlsx 表格                              │
│     · Phase 1: Tables/single/ 中的表                        │
│     · Phase 2: Tables/double/ 中的表                        │
│     · Phase 3: Tables/possion/ 中的表                       │
│                                                             │
│  2. 将 xlsx 放到项目根目录，运行 central_control.py          │
│     数据会自动保存到 Data/YYYYMMDD/                          │
│                                                             │
│  3. 实验完成后，训练模型:                                     │
│     conda activate DS176                                    │
│     cd /Users/field/Documents/SeneorLab_workplace-main      │
│     python ml/train.py --resume --phase <阶段>              │
│                                                             │
│  4. 查看 MAE 指标是否改善                                    │
│                                                             │
│  5. （可选）用预测脚本验证:                                   │
│     python ml/predict.py Data/YYYYMMDD/                     │
│                                                             │
│  6. 继续下一批实验，重复以上步骤                              │
│     · 同阶段数据越多 → 模型越准                              │
│     · 当阶段模型表现稳定 → 进入下一阶段                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 阶段晋升建议

| 条件 | 动作 |
|------|------|
| Phase 1 各物质 MAE < 0.5g | 可以进入 Phase 2 |
| Phase 2 各物质 MAE < 0.5g | 可以进入 Phase 3 |
| Phase 3 各物质 MAE < 0.3g | 模型基本可用于真实场景 |
| 持续添加新数据 | 始终用 `--resume --phase all` |

---

## ⚙️ 高级配置说明

### 修改模型超参数

编辑 `ml/config.py` 文件：

| 参数 | 位置 | 说明 | 默认值 |
|------|------|------|--------|
| `TRAINING_PHASE` | 顶层 | 默认训练阶段 | `"all"` |
| `conv_channels` | `MODEL_CONFIG` | 卷积层通道数 | [32, 64, 128] |
| `kernel_sizes` | `MODEL_CONFIG` | 卷积核大小 | [5, 5, 3] |
| `dropout` | `MODEL_CONFIG` | Dropout 比率 | 0.3 |
| `fc_hidden` | `MODEL_CONFIG` | 全连接隐藏层大小 | 128 |
| `batch_size` | `TRAIN_CONFIG` | 批大小 | 16 |
| `learning_rate` | `TRAIN_CONFIG` | 学习率 | 0.001 |
| `epochs` | `TRAIN_CONFIG` | 最大训练轮数 | 500 |
| `patience` | `TRAIN_CONFIG` | Early Stopping 耐心值 | 50 |
| `val_ratio` | `TRAIN_CONFIG` | 验证集比例 | 0.2 |

> ⚠️ 如果修改了 `MODEL_CONFIG` 中的网络结构参数，已有的检查点将不兼容。
> 需要删除 `ml/checkpoints/` 目录后从头训练。

### 修改默认训练阶段

在 `ml/config.py` 中修改 `TRAINING_PHASE`：

```python
TRAINING_PHASE = "single"   # 或 "double", "possion", "all"
```

也可以通过命令行 `--phase` 参数临时覆盖，无需改文件。

### 重置模型（从零开始训练）

```bash
rm -rf ml/checkpoints/ ml/logs/
python ml/train.py --phase single
```

---

## 🔬 模型原理简述

### 输入
- 每个样本 = 101 个频率点 × 5 个特征
  - 频率 (Hz)、实部阻抗 Re(Z)、虚部阻抗 Im(Z)、阻抗模值 |Z|、相位角 (°)

### 网络结构 (1D CNN)
```
输入: (batch, 5, 101)
  ↓
Conv1d(5→32, k=5) → BatchNorm → ReLU → Dropout
  ↓
Conv1d(32→64, k=5) → BatchNorm → ReLU → Dropout
  ↓
Conv1d(64→128, k=3) → BatchNorm → ReLU → Dropout
  ↓
AdaptiveAvgPool1d → (batch, 128, 1)
  ↓
Flatten → Linear(128→128) → ReLU → Dropout
  ↓
Linear(128→7) → 7 种化学物质预测质量
```

### 输出
- 7 个化学物质的预测质量（克）

### 训练策略
- **损失函数**: MSE (均方误差)
- **优化器**: Adam (带权重衰减)
- **学习率调度**: ReduceLROnPlateau（验证损失停滞时自动降低学习率）
- **Early Stopping**: 验证损失 50 轮未改善则停止
- **数据标准化**: StandardScaler 对输入和标签分别标准化
- **渐进式训练**: single → double → possion → all

---

## ❓ 常见问题排查

| 问题 | 解决方案 |
|------|---------|
| `ModuleNotFoundError: No module named 'torch'` | 运行 `pip install -r ml/requirements.txt` |
| `FileNotFoundError: 数据目录不存在` | 确认 `Data/` 目录路径正确 |
| `数据目录下没有子文件夹` | 在 `Data/` 下创建日期文件夹并放入数据 |
| `⚠️ 跳过（数据点数不符）` | 检查该文件是否有完整的 101 行 EIS 数据 |
| `阶段过滤后没有剩余样本` | 当前阶段无对应数据，请切换 `--phase all` 或先采集对应数据 |
| 续训后模型变差 | 可能新数据分布差异大，尝试降低 lr: `--lr 0.0001` |
| `⚠️ 未找到检查点文件` | 需要先做一次全新训练（不加 `--resume`） |
| 要从零重来 | `rm -rf ml/checkpoints/ ml/logs/` 后重新训练 |
