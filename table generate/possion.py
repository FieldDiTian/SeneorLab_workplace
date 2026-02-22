import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

COLUMNS = ["NaCl", "KCl", "Urea", "Na_lactate", "NH4Cl", "CaCl2", "Glucose"]

def sample_row_poisson(rng: np.random.Generator,
                       lam_vec: np.ndarray,
                       V_total: int = 30,
                       min_nonzero: int = 3,
                       max_tries: int = 20000):
    """
    生成单行注入体积（mL），满足：
      - 每列：0 或 >= min_nonzero
      - sum(7列) <= V_total
      - Water = V_total - sum(7列)
    """
    for _ in range(max_tries):
        raw = rng.poisson(lam=lam_vec).astype(int)
        vols = np.where(raw == 0, 0, np.maximum(raw, min_nonzero))
        vols = np.minimum(vols, V_total)
        s = int(vols.sum())
        if s <= V_total:
            return vols, int(V_total - s)
    raise RuntimeError("重采样失败：请减小 lambdas 或减少列数/增大 V_total（你这里 V_total 最大 30）。")

def generate_table_use_stock(n_experiments: int,
                             target_per_col: int = 200,
                             V_total: int = 30,
                             min_nonzero: int = 3,
                             seed: int = 42,
                             max_outer_iters: int = 80,
                             tol_ml: int = 5):
    """
    目标：生成 n_experiments 行，使每一列的累计用量尽量接近 target_per_col（例如 200 mL）。
    方法：迭代调整每列的泊松 lambda，使列总和逼近 target。
    """
    rng = np.random.default_rng(seed)

    # 初始 lambda：目标每列总量 / 行数
    base = target_per_col / n_experiments
    lambdas = np.full(len(COLUMNS), base, dtype=float)

    best_df = None
    best_score = float("inf")

    for _ in range(max_outer_iters):
        rows = []
        for exp_id in range(1, n_experiments + 1):  # 实验组号从 1 开始
            vols, water = sample_row_poisson(rng, lambdas, V_total=V_total, min_nonzero=min_nonzero)
            row = {"Experiment": exp_id, **{c: int(v) for c, v in zip(COLUMNS, vols)}, "Water": int(water)}
            rows.append(row)

        df = pd.DataFrame(rows, columns=["Experiment", *COLUMNS, "Water"])
        col_sums = df[COLUMNS].sum()

        # score 越小越好：各列总量与 target 的偏差之和
        score = float(np.abs(col_sums - target_per_col).sum())
        if score < best_score:
            best_score = score
            best_df = df.copy()

        # 全列都在容忍范围内就停止
        if (np.abs(col_sums - target_per_col) <= tol_ml).all():
            break

        # 按“目标/当前”比例温和更新 lambda，避免发散
        ratios = (target_per_col / col_sums.replace(0, np.nan)).to_numpy(dtype=float)
        ratios = np.nan_to_num(ratios, nan=1.0, posinf=1.0, neginf=1.0)
        ratios = np.clip(ratios, 0.6, 1.6)
        lambdas = np.clip(lambdas * ratios, 0.2, 20.0)

    totals = best_df[COLUMNS].sum().to_frame(name="Total_mL")
    totals["Target_mL"] = target_per_col
    totals["Delta_mL"] = totals["Total_mL"] - target_per_col
    return best_df, totals, best_score

def save_xlsx_with_date(df: pd.DataFrame,
                        totals: pd.DataFrame,
                        out_dir: str = ".",
                        date_fmt: str = "%d-%m-%Y"):
    """
    输出文件名：日-月-年.xlsx，例如 21-02-2026.xlsx
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fname = datetime.now().strftime(date_fmt) + ".xlsx"
    out_path = out_dir / fname

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Table")
        totals.to_excel(writer, sheet_name="Totals")

    return out_path

if __name__ == "__main__":
    # 重要：要让“每列尽量接近 200 mL”，行数至少要足够大。
    # 由于每行总量 <=30 mL，7 列平均每行每列最多也就 ~4 mL。
    # 经验上 n_experiments=50 左右比较合适（200/50=4 mL/行/列）。
    n_experiments = 50

    df, totals, score = generate_table_use_stock(
        n_experiments=n_experiments,
        target_per_col=200,
        V_total=30,
        min_nonzero=3,
        seed=20260221,
        max_outer_iters=80,
        tol_ml=5
    )

    out_path = save_xlsx_with_date(df, totals, out_dir=".", date_fmt="%d-%m-%Y")
    print(f"Saved: {out_path}")
    print("Column totals:\n", totals)
    print("Score (sum abs deltas):", score)