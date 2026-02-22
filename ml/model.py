"""
1D CNN 模型定义
用于从 EIS 频谱数据回归预测 7 种化学物质的实际称重质量。
"""
import torch
import torch.nn as nn


class EIS_1DCNN(nn.Module):
    """
    1D 卷积神经网络，用于 EIS 频谱 → 化学物质质量回归。

    网络结构:
        Conv1d Block × 3 (Conv → BatchNorm → ReLU → Dropout)
        → AdaptiveAvgPool1d
        → Flatten
        → FC → ReLU → Dropout
        → FC → 输出 (7 个化学物质质量)

    输入: (batch, 5, 100) — 5 个特征通道, 100 个频率点
    输出: (batch, 7)      — 7 种化学物质预测质量
    """

    def __init__(self, config: dict):
        super().__init__()

        in_channels = config["input_channels"]      # 5
        conv_channels = config["conv_channels"]      # [32, 64, 128]
        kernel_sizes = config["kernel_sizes"]         # [5, 5, 3]
        dropout = config["dropout"]                   # 0.3
        fc_hidden = config["fc_hidden"]               # 128
        num_targets = config["num_targets"]           # 7

        # 构建卷积层
        conv_layers = []
        prev_ch = in_channels
        for ch, ks in zip(conv_channels, kernel_sizes):
            conv_layers.extend([
                nn.Conv1d(prev_ch, ch, kernel_size=ks, padding=ks // 2),
                nn.BatchNorm1d(ch),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
            ])
            prev_ch = ch

        self.conv_block = nn.Sequential(*conv_layers)

        # 自适应池化 → 固定输出长度为 1
        self.pool = nn.AdaptiveAvgPool1d(1)

        # 全连接回归头
        self.fc = nn.Sequential(
            nn.Linear(conv_channels[-1], fc_hidden),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(fc_hidden, num_targets),
        )

    def forward(self, x):
        """
        Args:
            x: Tensor, shape=(batch, 5, 101)
        Returns:
            Tensor, shape=(batch, 7)
        """
        x = self.conv_block(x)   # (batch, 128, 101)
        x = self.pool(x)         # (batch, 128, 1)
        x = x.squeeze(-1)        # (batch, 128)
        x = self.fc(x)           # (batch, 7)
        return x


def build_model(config: dict, device: torch.device = None):
    """创建模型并移动到指定设备"""
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else
                              "mps" if torch.backends.mps.is_available() else "cpu")
    model = EIS_1DCNN(config).to(device)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"🧠 模型参数量: {total_params:,}")
    print(f"🖥️  设备: {device}")
    return model, device


def load_checkpoint(model, optimizer=None, scheduler=None, path=None):
    """
    加载模型检查点（用于续训）。
    
    返回:
        start_epoch:  从哪个 epoch 继续
        best_val_loss: 历史最佳验证损失
    """
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    if optimizer is not None and "optimizer_state_dict" in checkpoint:
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    if scheduler is not None and "scheduler_state_dict" in checkpoint:
        scheduler.load_state_dict(checkpoint["scheduler_state_dict"])

    start_epoch = checkpoint.get("epoch", 0) + 1
    best_val_loss = checkpoint.get("best_val_loss", float("inf"))
    print(f"📦 已加载检查点: epoch={start_epoch - 1}, best_val_loss={best_val_loss:.6f}")
    return start_epoch, best_val_loss


def save_checkpoint(model, optimizer, scheduler, epoch, best_val_loss, path):
    """保存模型检查点"""
    torch.save({
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict() if scheduler else None,
        "best_val_loss": best_val_loss,
    }, path)
