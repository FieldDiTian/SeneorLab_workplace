import argparse
import os
import sys

# Ensure workspace root is importable
WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import modules.eis_module as eis_module


def _quick_freq_list(full_freqs, points: int):
    """从完整频率列表中均匀抽取若干点（保留高->低顺序）。"""
    full = full_freqs
    if points <= 0 or points >= len(full):
        return full

    if points == 1:
        return full[:1]

    last_index = len(full) - 1
    idxs = []
    for i in range(points):
        idx = round(i * last_index / (points - 1))
        idxs.append(idx)

    dedup_idxs = []
    seen = set()
    for idx in idxs:
        if idx not in seen:
            dedup_idxs.append(idx)
            seen.add(idx)

    return full[dedup_idxs]


def build_test_dicts():
    mass_dict = {
        "NaCl": 0.0,
        "KCl": 0.0,
        "Urea": 0.0,
        "Na_lactate": 0.0,
        "NH4Cl": 0.0,
        "CaCl2": 0.0,
        "Glucose": 0.0,
        "WATER": 0.0,
    }

    # central_control 传的是目标体积（mL），这里保持同样键名
    target_dict = {
        "NaCl": 0.0,
        "KCl": 0.0,
        "Urea": 0.0,
        "Na_lactate": 0.0,
        "NH4Cl": 0.0,
        "CaCl2": 0.0,
        "Glucose": 0.0,
        "WATER": 0.0,
    }
    return mass_dict, target_dict


def main():
    parser = argparse.ArgumentParser(description="EIS 测试脚本")
    parser.add_argument("--simulation", action="store_true", help="使用仿真模式（无需设备）")
    parser.add_argument("--full", action="store_true", help="完整 55 点频扫")
    parser.add_argument("--points", type=int, default=8, help="快速测试频点数（仅在非 --full 时生效）")
    parser.add_argument("--output", type=str, default=None, help="输出目录（默认由 eis_module 决定）")
    parser.add_argument("--exp-num", type=int, default=1, help="实验编号")
    args = parser.parse_args()

    print("=== EIS Test Script ===")
    print(f"Mode: {'SIMULATION' if args.simulation else 'HARDWARE'}")

    eis_module.SIMULATION_MODE = args.simulation

    # 快速模式：临时替换频率列表生成函数
    original_generate_freq_list = eis_module.generate_freq_list
    full_freqs = original_generate_freq_list()
    if not args.full:
        eis_module.generate_freq_list = lambda: _quick_freq_list(full_freqs, args.points)
        print(f"Quick scan enabled: {args.points} points")
    else:
        print("Full scan enabled: 55 points")

    mass_dict, target_dict = build_test_dicts()

    try:
        z_values = eis_module.main(
            mass_dict=mass_dict,
            target_concentrations=target_dict,
            output_folder=args.output,
            experiment_num=args.exp_num,
        )

        if z_values:
            print(f"\n✅ EIS test finished, collected {len(z_values)} points")
            return 0

        print("\n⚠ EIS test finished but no data points were collected")
        return 1

    except Exception as exc:
        print(f"\n❌ EIS test failed: {exc}")
        return 2

    finally:
        eis_module.generate_freq_list = original_generate_freq_list


if __name__ == "__main__":
    raise SystemExit(main())
