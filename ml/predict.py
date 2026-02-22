"""
EIS 1D-CNN 预测/推理脚本
用于加载已训练好的模型，对新的 EIS 数据文件进行化学物质质量预测。
"""
import os
import sys
import argparse
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.config import (
    MODEL_CONFIG, CHECKPOINT_DIR, BEST_MODEL_FILE, TARGET_CHEMICALS,
    NUM_FREQ_POINTS
)
from ml.dataset import parse_eis_file, load_scalers
from ml.model import EIS_1DCNN


def predict_single_file(filepath: str, model, x_scaler, y_scaler, device):
    """
    对单个 EIS 文件进行预测。
    
    返回:
        pred_dict: dict, 化学物质名称 → 预测质量 (g)
        actual_dict: dict, 化学物质名称 → 实际质量 (g) （从文件头解析，如有）
    """
    eis_data, labels = parse_eis_file(filepath)
    if eis_data is None or eis_data.shape[0] != NUM_FREQ_POINTS:
        raise ValueError(f"文件数据无效或频率点数不符: {filepath}")

    # 标准化
    X = eis_data.copy()  # (101, 5)
    N, C = X.shape
    if x_scaler is not None:
        X = x_scaler.transform(X)

    # 转为张量: (1, 5, 101)
    X_tensor = torch.from_numpy(X).float().permute(1, 0).unsqueeze(0).to(device)

    model.eval()
    with torch.no_grad():
        pred = model(X_tensor).cpu().numpy()  # (1, 7)

    # 反标准化
    if y_scaler is not None:
        pred = y_scaler.inverse_transform(pred)

    pred = pred.flatten()
    pred_dict = {chem: round(float(pred[i]), 4) for i, chem in enumerate(TARGET_CHEMICALS)}

    actual_dict = None
    if labels is not None:
        actual_dict = {chem: round(float(labels[i]), 4) for i, chem in enumerate(TARGET_CHEMICALS)}

    return pred_dict, actual_dict


def main():
    parser = argparse.ArgumentParser(description="EIS 1D-CNN 预测")
    parser.add_argument("input", type=str,
                        help="单个 EIS .txt 文件路径，或包含多个 .txt 的文件夹路径")
    parser.add_argument("--model", type=str, default=None,
                        help="模型检查点路径（默认使用 best_model.pth）")
    args = parser.parse_args()

    # 加载模型
    model_path = args.model or os.path.join(CHECKPOINT_DIR, BEST_MODEL_FILE)
    if not os.path.exists(model_path):
        print(f"❌ 模型文件不存在: {model_path}")
        print("   请先运行训练: python ml/train.py")
        sys.exit(1)

    device = torch.device("cuda" if torch.cuda.is_available() else
                          "mps" if torch.backends.mps.is_available() else "cpu")
    model = EIS_1DCNN(MODEL_CONFIG).to(device)
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    print(f"✅ 模型已加载: {model_path} (epoch {checkpoint.get('epoch', '?')})")

    # 加载 scalers
    x_scaler, y_scaler = load_scalers()
    if x_scaler is None:
        print("⚠️ 未找到 scaler 文件，预测结果可能不准确")

    # 收集待预测文件
    input_path = args.input
    if os.path.isfile(input_path):
        files = [input_path]
    elif os.path.isdir(input_path):
        files = sorted([
            os.path.join(input_path, f) for f in os.listdir(input_path)
            if f.endswith(".txt") and f.startswith("EIS_Data_")
        ])
    else:
        print(f"❌ 路径不存在: {input_path}")
        sys.exit(1)

    if not files:
        print("未找到 EIS 数据文件")
        sys.exit(1)

    # 预测
    print(f"\n📊 预测 {len(files)} 个文件:\n")
    print("-" * 90)
    header = f"{'文件':<45s}"
    for chem in TARGET_CHEMICALS:
        header += f" {chem:>8s}"
    print(header)
    print("-" * 90)

    for fpath in files:
        fname = os.path.basename(fpath)
        try:
            pred_dict, actual_dict = predict_single_file(fpath, model, x_scaler, y_scaler, device)
            line = f"{fname[:44]:<45s}"
            for chem in TARGET_CHEMICALS:
                line += f" {pred_dict[chem]:8.4f}"
            print(line)

            if actual_dict is not None:
                actual_line = f"{'  (实际值)':<45s}"
                for chem in TARGET_CHEMICALS:
                    actual_line += f" {actual_dict[chem]:8.4f}"
                print(actual_line)

                err_line = f"{'  (误差)':<45s}"
                for chem in TARGET_CHEMICALS:
                    err = abs(pred_dict[chem] - actual_dict[chem])
                    err_line += f" {err:8.4f}"
                print(err_line)
            print()

        except Exception as e:
            print(f"  ❌ 预测失败: {fname} — {e}")

    print("预测完成 ✅")


if __name__ == "__main__":
    main()
