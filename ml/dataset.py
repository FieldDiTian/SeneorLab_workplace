"""
EIS 数据集加载与预处理模块
自动扫描 Data/ 下所有日期子文件夹，解析每个 .txt 文件的头部标签和 EIS 频谱数据。
"""
import os
import re
import glob
import numpy as np
import pickle
import torch
from torch.utils.data import Dataset, DataLoader, random_split
from sklearn.preprocessing import StandardScaler

from ml.config import (
    DATA_DIR, TARGET_CHEMICALS, NUM_FREQ_POINTS, NUM_EIS_FEATURES,
    CHECKPOINT_DIR, SCALER_FILE, TRAIN_CONFIG, TRAINING_PHASE, PHASE_FILTER
)


def parse_eis_file(filepath: str):
    """
    解析单个 EIS 数据 txt 文件。
    
    返回:
        eis_data: np.ndarray, shape=(NUM_FREQ_POINTS, NUM_EIS_FEATURES)
                  列依次为 [Frequency, Re(Z), Im(Z), |Z|, Phase]
        labels:   dict, 键为化学物质名称，值为实际称重质量 (float, g)
    """
    labels = {}
    eis_rows = []
    header_done = False
    in_actual_mass = False  # 是否正在解析"实际称重质量"块

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # 分隔线标记头部结束
            if line.startswith("---"):
                header_done = True
                continue
            
            if not header_done:
                # 检测"实际称重质量"块开始
                if "实际称重质量" in line:
                    in_actual_mass = True
                    continue
                # 检测"目标体积"块开始 → 停止解析标签
                if "目标体积" in line:
                    in_actual_mass = False
                    continue
                
                # 仅在"实际称重质量"块内提取标签
                if in_actual_mass:
                    matches = re.findall(r'(\w+)=([-\d.]+)', line)
                    for name, value in matches:
                        if name in TARGET_CHEMICALS:
                            labels[name] = float(value)
            else:
                # 解析 EIS 数据行
                parts = line.split(",")
                if len(parts) == 5:
                    try:
                        row = [float(x.strip()) for x in parts]
                        eis_rows.append(row)
                    except ValueError:
                        continue

    if len(eis_rows) == 0:
        return None, None

    eis_data = np.array(eis_rows, dtype=np.float32)
    
    # 确保所有 7 种化学物质都有值
    label_array = np.array(
        [labels.get(chem, 0.0) for chem in TARGET_CHEMICALS],
        dtype=np.float32
    )

    return eis_data, label_array


def scan_all_data(data_dir: str = DATA_DIR):
    """
    扫描 Data/ 目录下所有子文件夹中的 .txt EIS 数据文件。
    
    返回:
        all_eis:    list of np.ndarray, 每个 shape=(N_freq, 5)
        all_labels: list of np.ndarray, 每个 shape=(7,)
        all_files:  list of str, 对应文件路径
    """
    all_eis = []
    all_labels = []
    all_files = []

    # 遍历 Data/ 下所有子文件夹（日期文件夹）
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"数据目录不存在: {data_dir}")

    date_folders = sorted([
        d for d in os.listdir(data_dir)
        if os.path.isdir(os.path.join(data_dir, d))
    ])

    if len(date_folders) == 0:
        raise FileNotFoundError(f"数据目录下没有子文件夹: {data_dir}")

    print(f"📂 发现 {len(date_folders)} 个日期文件夹: {date_folders}")

    for folder in date_folders:
        folder_path = os.path.join(data_dir, folder)
        txt_files = sorted(glob.glob(os.path.join(folder_path, "EIS_Data_*.txt")))
        print(f"  📄 {folder}: {len(txt_files)} 个 EIS 数据文件")

        for fpath in txt_files:
            eis_data, label_array = parse_eis_file(fpath)
            if eis_data is not None and eis_data.shape[0] == NUM_FREQ_POINTS:
                all_eis.append(eis_data)
                all_labels.append(label_array)
                all_files.append(fpath)
            else:
                print(f"  ⚠️ 跳过（数据点数不符或解析失败）: {os.path.basename(fpath)}")

    print(f"✅ 共加载 {len(all_eis)} 个有效样本")
    return all_eis, all_labels, all_files


def filter_by_phase(all_eis, all_labels, all_files, phase: str = None):
    """
    根据训练阶段过滤样本。
    
    过滤逻辑基于每条数据中非零目标化学物质的数量：
      - single:  仅保留恰好 1 种化学物质 > 0 的样本
      - double:  保留 1-2 种化学物质 > 0 的样本
      - possion: 保留所有样本（含 3+ 组分的 Poisson 随机配比）
      - all:     不过滤，使用全部数据
    
    Args:
        phase: 训练阶段名称，默认使用 config.TRAINING_PHASE
    
    返回:
        过滤后的 (eis_list, labels_list, files_list)
    """
    if phase is None:
        phase = TRAINING_PHASE
    
    if phase == "all":
        print(f"📋 训练阶段: ALL（使用全部 {len(all_eis)} 个样本）")
        return all_eis, all_labels, all_files
    
    phase_fn = PHASE_FILTER.get(phase)
    if phase_fn is None:
        print(f"⚠️ 未知阶段 '{phase}'，使用全部数据")
        return all_eis, all_labels, all_files
    
    filtered_eis = []
    filtered_labels = []
    filtered_files = []
    
    for eis, labels, fpath in zip(all_eis, all_labels, all_files):
        # 统计非零化学物质数量（排除 Water，只看 7 种目标物质）
        n_nonzero = int(np.sum(labels > 0.01))  # 阈值 0.01g 排除称重噪声
        if phase_fn(n_nonzero):
            filtered_eis.append(eis)
            filtered_labels.append(labels)
            filtered_files.append(fpath)
    
    print(f"📋 训练阶段: {phase.upper()}")
    print(f"   过滤前: {len(all_eis)} 样本 → 过滤后: {len(filtered_eis)} 样本")
    
    if len(filtered_eis) == 0:
        raise ValueError(f"阶段 '{phase}' 过滤后没有剩余样本！请检查数据或切换阶段。")
    
    return filtered_eis, filtered_labels, filtered_files


class EISDataset(Dataset):
    """
    PyTorch Dataset，用于加载 EIS 频谱数据。
    
    输入 X: shape=(NUM_EIS_FEATURES, NUM_FREQ_POINTS)  — 通道优先（Conv1d 要求）
    标签 y: shape=(7,)  — 7 种化学物质的实际质量
    """
    def __init__(self, eis_list, labels_list, x_scaler=None, y_scaler=None, fit_scalers=False):
        """
        Args:
            eis_list:    list of np.ndarray, shape=(101, 5)
            labels_list: list of np.ndarray, shape=(7,)
            x_scaler:    sklearn StandardScaler for X（传入已有的用于推理/验证）
            y_scaler:    sklearn StandardScaler for y
            fit_scalers: 是否 fit scaler（仅训练集为 True）
        """
        X = np.stack(eis_list)       # (N, 101, 5)
        y = np.stack(labels_list)    # (N, 7)

        # 对 X 做标准化：逐特征列标准化（在频率维度上 flatten 后 fit）
        N, T, C = X.shape
        X_flat = X.reshape(-1, C)  # (N*101, 5)

        if fit_scalers:
            self.x_scaler = StandardScaler()
            X_flat = self.x_scaler.fit_transform(X_flat)
            self.y_scaler = StandardScaler()
            y = self.y_scaler.fit_transform(y)
        else:
            self.x_scaler = x_scaler
            self.y_scaler = y_scaler
            if x_scaler is not None:
                X_flat = x_scaler.transform(X_flat)
            if y_scaler is not None:
                y = y_scaler.transform(y)

        X = X_flat.reshape(N, T, C)

        # 转换为 (N, C, T) —— Conv1d 需要 (batch, channels, length)
        self.X = torch.from_numpy(X).permute(0, 2, 1).float()  # (N, 5, 101)
        self.y = torch.from_numpy(y).float()                    # (N, 7)

    def __len__(self):
        return self.X.shape[0]

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


def save_scalers(x_scaler, y_scaler, path=None):
    """保存标准化器到磁盘"""
    if path is None:
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)
        path = os.path.join(CHECKPOINT_DIR, SCALER_FILE)
    with open(path, "wb") as f:
        pickle.dump({"x_scaler": x_scaler, "y_scaler": y_scaler}, f)
    print(f"💾 Scalers 已保存到: {path}")


def load_scalers(path=None):
    """加载标准化器"""
    if path is None:
        path = os.path.join(CHECKPOINT_DIR, SCALER_FILE)
    if not os.path.exists(path):
        return None, None
    with open(path, "rb") as f:
        data = pickle.load(f)
    return data["x_scaler"], data["y_scaler"]


def prepare_dataloaders(data_dir: str = DATA_DIR, batch_size: int = None,
                        val_ratio: float = None, phase: str = None):
    """
    完整的数据准备流程：扫描 → 阶段过滤 → 构建 Dataset → 拆分训练/验证 → 返回 DataLoader。
    
    Args:
        phase: 训练阶段 ("single"/"double"/"possion"/"all")，默认使用 config 中的设置
    
    返回:
        train_loader, val_loader, train_dataset（包含 scaler 信息）
    """
    if batch_size is None:
        batch_size = TRAIN_CONFIG["batch_size"]
    if val_ratio is None:
        val_ratio = TRAIN_CONFIG["val_ratio"]

    all_eis, all_labels, all_files = scan_all_data(data_dir)

    # 根据训练阶段过滤数据
    all_eis, all_labels, all_files = filter_by_phase(all_eis, all_labels, all_files, phase)

    # 构建完整数据集并 fit scaler
    full_dataset = EISDataset(all_eis, all_labels, fit_scalers=True)

    # 保存 scalers
    save_scalers(full_dataset.x_scaler, full_dataset.y_scaler)

    # 拆分训练/验证
    n_total = len(full_dataset)
    n_val = max(1, int(n_total * val_ratio))
    n_train = n_total - n_val

    generator = torch.Generator().manual_seed(TRAIN_CONFIG["random_seed"])
    train_dataset, val_dataset = random_split(full_dataset, [n_train, n_val], generator=generator)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=TRAIN_CONFIG["num_workers"],
        drop_last=False
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=TRAIN_CONFIG["num_workers"]
    )

    print(f"📊 训练集: {n_train} 样本, 验证集: {n_val} 样本")
    return train_loader, val_loader, full_dataset
