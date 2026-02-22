"""
EIS 1D-CNN 训练脚本
支持：
  - 全新训练（首次）
  - 续训 / 增量训练（自动加载上一次最佳模型 + scaler 重拟合）
  - Early Stopping + 学习率衰减
  - 训练日志记录
"""
import os
import sys
import time
import json
import argparse
import numpy as np
import torch
import torch.nn as nn
from datetime import datetime

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.config import (
    MODEL_CONFIG, TRAIN_CONFIG, CHECKPOINT_DIR, LOG_DIR,
    BEST_MODEL_FILE, LATEST_MODEL_FILE, DATA_DIR, TARGET_CHEMICALS,
    TRAINING_PHASE
)
from ml.dataset import prepare_dataloaders, save_scalers
from ml.model import build_model, load_checkpoint, save_checkpoint


def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0.0
    for X_batch, y_batch in loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)
        optimizer.zero_grad()
        pred = model(X_batch)
        loss = criterion(pred, y_batch)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * X_batch.size(0)
    return total_loss / len(loader.dataset)


@torch.no_grad()
def validate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    all_preds = []
    all_labels = []
    for X_batch, y_batch in loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)
        pred = model(X_batch)
        loss = criterion(pred, y_batch)
        total_loss += loss.item() * X_batch.size(0)
        all_preds.append(pred.cpu().numpy())
        all_labels.append(y_batch.cpu().numpy())
    avg_loss = total_loss / len(loader.dataset)
    all_preds = np.concatenate(all_preds, axis=0)
    all_labels = np.concatenate(all_labels, axis=0)
    return avg_loss, all_preds, all_labels


def main():
    parser = argparse.ArgumentParser(description="EIS 1D-CNN 训练")
    parser.add_argument("--resume", action="store_true",
                        help="从上一次检查点继续训练（增量训练）")
    parser.add_argument("--epochs", type=int, default=None,
                        help="覆盖默认训练轮数")
    parser.add_argument("--lr", type=float, default=None,
                        help="覆盖默认学习率")
    parser.add_argument("--batch_size", type=int, default=None,
                        help="覆盖默认批大小")
    parser.add_argument("--phase", type=str, default=None,
                        choices=["single", "double", "possion", "all"],
                        help="训练阶段: single(单组分)/double(双组分)/possion(多组分)/all(全部)")
    args = parser.parse_args()

    # ---- 创建输出目录 ----
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    epochs = args.epochs or TRAIN_CONFIG["epochs"]
    lr = args.lr or TRAIN_CONFIG["learning_rate"]
    batch_size = args.batch_size or TRAIN_CONFIG["batch_size"]
    phase = args.phase or TRAINING_PHASE

    # ---- 数据准备 ----
    print("=" * 60)
    print("📦 数据加载与预处理...")
    print("=" * 60)
    train_loader, val_loader, full_dataset = prepare_dataloaders(
        data_dir=DATA_DIR, batch_size=batch_size, phase=phase
    )

    # ---- 构建模型 ----
    print("\n" + "=" * 60)
    print("🧠 构建模型...")
    print("=" * 60)
    model, device = build_model(MODEL_CONFIG)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(
        model.parameters(), lr=lr, weight_decay=TRAIN_CONFIG["weight_decay"]
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min",
        factor=TRAIN_CONFIG["scheduler_factor"],
        patience=TRAIN_CONFIG["scheduler_patience"],
    )

    # ---- 如果续训，加载检查点 ----
    start_epoch = 0
    best_val_loss = float("inf")

    latest_path = os.path.join(CHECKPOINT_DIR, LATEST_MODEL_FILE)
    best_path = os.path.join(CHECKPOINT_DIR, BEST_MODEL_FILE)

    if args.resume:
        ckpt_path = latest_path if os.path.exists(latest_path) else best_path
        if os.path.exists(ckpt_path):
            start_epoch, best_val_loss = load_checkpoint(
                model, optimizer, scheduler, ckpt_path
            )
            print(f"🔄 续训模式: 从 epoch {start_epoch} 继续, 历史最佳 val_loss={best_val_loss:.6f}")
        else:
            print("⚠️ 未找到检查点文件，将从头开始训练")

    # ---- 训练循环 ----
    print("\n" + "=" * 60)
    print(f"🚀 开始训练: epochs={epochs}, lr={lr}, batch_size={batch_size}")
    print(f"   阶段: {phase.upper()}")
    print(f"   设备: {device}")
    print("=" * 60)

    patience_counter = 0
    train_log = []

    for epoch in range(start_epoch, start_epoch + epochs):
        t0 = time.time()
        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_preds, val_labels = validate(model, val_loader, criterion, device)
        scheduler.step(val_loss)
        elapsed = time.time() - t0

        current_lr = optimizer.param_groups[0]["lr"]

        # 日志
        log_entry = {
            "epoch": epoch,
            "train_loss": round(train_loss, 6),
            "val_loss": round(val_loss, 6),
            "lr": current_lr,
            "time": round(elapsed, 2),
        }
        train_log.append(log_entry)

        # 打印
        improved = ""
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            save_checkpoint(model, optimizer, scheduler, epoch, best_val_loss, best_path)
            improved = " ✅ (best)"
        else:
            patience_counter += 1

        # 同时保存 latest
        save_checkpoint(model, optimizer, scheduler, epoch, best_val_loss, latest_path)

        print(f"[Epoch {epoch:04d}] "
              f"train_loss={train_loss:.6f} | val_loss={val_loss:.6f} | "
              f"lr={current_lr:.2e} | {elapsed:.1f}s{improved}")

        # Early Stopping
        if patience_counter >= TRAIN_CONFIG["patience"]:
            print(f"\n⏹️ Early stopping: 验证损失 {TRAIN_CONFIG['patience']} 轮未改善, 停止训练")
            break

    # ---- 保存训练日志 ----
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"train_log_{timestamp}.json")
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(train_log, f, indent=2, ensure_ascii=False)
    print(f"\n📝 训练日志已保存到: {log_file}")

    # ---- 最终评估 ----
    print("\n" + "=" * 60)
    print("📊 最终验证集评估 (使用最佳模型)")
    print("=" * 60)

    # 加载最佳模型
    if os.path.exists(best_path):
        load_checkpoint(model, path=best_path)

    val_loss, val_preds, val_labels = validate(model, val_loader, criterion, device)

    # 反标准化后计算误差（还原为原始克数）
    y_scaler = full_dataset.y_scaler
    if y_scaler is not None:
        val_preds_orig = y_scaler.inverse_transform(val_preds)
        val_labels_orig = y_scaler.inverse_transform(val_labels)
    else:
        val_preds_orig = val_preds
        val_labels_orig = val_labels

    mae_per_chem = np.mean(np.abs(val_preds_orig - val_labels_orig), axis=0)
    print(f"\n验证集 MSE Loss (标准化后): {val_loss:.6f}")
    print(f"\n各化学物质 MAE (原始克数):")
    for i, chem in enumerate(TARGET_CHEMICALS):
        print(f"  {chem:>8s}: {mae_per_chem[i]:.4f} g")

    print(f"\n总体平均 MAE: {np.mean(mae_per_chem):.4f} g")
    print(f"\n🎉 训练完成！最佳模型: {best_path}")


if __name__ == "__main__":
    main()
