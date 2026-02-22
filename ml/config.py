"""
EIS 1D-CNN 训练配置文件
所有超参数和路径集中管理，方便调整。
"""
import os

# ======================== 路径配置 ========================
# 项目根目录（ml/ 的上一级）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据根目录 —— 程序会自动扫描该目录下所有日期子文件夹中的 .txt 文件
DATA_DIR = os.path.join(PROJECT_ROOT, "Data")

# 模型保存目录
CHECKPOINT_DIR = os.path.join(PROJECT_ROOT, "ml", "checkpoints")

# 训练日志目录
LOG_DIR = os.path.join(PROJECT_ROOT, "ml", "logs")

# ======================== 数据配置 ========================
# 7 种目标化学物质（与文件头中的顺序一致）
TARGET_CHEMICALS = ["NaCl", "KCl", "Urea", "Lac", "NH4Cl", "CaCl2", "Glu"]

# EIS 数据每个样本的频率点数（固定 100 个点）
NUM_FREQ_POINTS = 100

# EIS 每行 5 列：Frequency, Re(Z), Im(Z), |Z|, Phase
NUM_EIS_FEATURES = 5

# ======================== 模型配置 ========================
# 1D CNN 架构参数
MODEL_CONFIG = {
    "input_channels": NUM_EIS_FEATURES,   # 输入通道数 = 5（EIS 的 5 个特征列）
    "seq_length": NUM_FREQ_POINTS,        # 序列长度 = 100（频率点）
    "num_targets": len(TARGET_CHEMICALS), # 输出 = 7（7 种化学物质质量）
    "conv_channels": [32, 64, 128],       # 三层卷积的通道数
    "kernel_sizes": [5, 5, 3],            # 每层卷积核大小
    "dropout": 0.3,                       # Dropout 概率
    "fc_hidden": 128,                     # 全连接隐藏层大小
}

# ======================== 训练配置 ========================
TRAIN_CONFIG = {
    "batch_size": 16,
    "learning_rate": 1e-3,
    "weight_decay": 1e-4,
    "epochs": 500,
    "patience": 50,          # Early stopping 耐心值
    "val_ratio": 0.2,        # 验证集比例
    "random_seed": 42,
    "num_workers": 0,        # DataLoader workers（macOS 建议 0）
    "scheduler_factor": 0.5, # 学习率衰减因子
    "scheduler_patience": 20,# 学习率衰减耐心值
}

# ======================== 训练阶段配置（Curriculum Learning） ========================
# Phase 1: 仅使用单组分数据（single 表格生成的数据）
# Phase 2: 加入双组分数据（double 表格生成的数据）
# Phase 3: 加入 Poisson 随机多组分数据（possion 表格生成的数据）
# Phase all: 使用全部数据（不做过滤）
TRAINING_PHASE = "all"  # 可选: "single", "double", "possion", "all"

# 阶段过滤规则：根据每条数据中非零化学物质数量来分类
# single: 只有 1 种化学物质 > 0
# double: 恰好 2 种化学物质 > 0
# possion: 3 种及以上化学物质 > 0（即 Poisson 随机配比）
PHASE_FILTER = {
    "single": lambda n_nonzero: n_nonzero == 1,
    "double": lambda n_nonzero: n_nonzero <= 2,
    "possion": lambda n_nonzero: True,  # 包含所有
    "all": lambda n_nonzero: True,
}

# ======================== 最佳模型文件名 ========================
BEST_MODEL_FILE = "best_model.pth"
LATEST_MODEL_FILE = "latest_model.pth"
SCALER_FILE = "scalers.pkl"
