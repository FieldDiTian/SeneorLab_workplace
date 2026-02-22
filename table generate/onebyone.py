import pandas as pd
from datetime import datetime
from pathlib import Path

COLUMNS = ["NaCl", "KCl", "Urea", "Na_lactate", "NH4Cl", "CaCl2", "Glucose"]
V_TOTAL = 30
MAX_SUM_PER_TABLE = 200

def split_values_by_sum(v_start: int, v_end: int, max_sum: int):
    """
    把连续整数区间 [v_start, v_end] 拆成若干段，每段的和 <= max_sum。
    返回：[(a,b), (c,d), ...]
    """
    segs = []
    cur_a = v_start
    cur_sum = 0
    prev = v_start - 1

    for v in range(v_start, v_end + 1):
        if cur_sum + v > max_sum:
            # 结束上一段
            segs.append((cur_a, prev))
            # 开新段
            cur_a = v
            cur_sum = v
        else:
            cur_sum += v
        prev = v

    if cur_a <= v_end:
        segs.append((cur_a, v_end))
    return segs

def build_single_sheet_range(v_start: int, v_end: int, v_total: int = 30) -> pd.DataFrame:
    """
    单个文件/单个sheet：按化学物质依次追加行
      - 该化学物质列：v_start..v_end
      - 其他列：0
      - Water = v_total - v
      - Experiment 从1开始
    """
    rows = []
    exp_id = 1
    for chem in COLUMNS:
        for v in range(v_start, v_end + 1):
            row = {"Experiment": exp_id, **{c: 0 for c in COLUMNS}}
            row[chem] = int(v)
            row["Water"] = int(v_total - v)
            rows.append(row)
            exp_id += 1
    return pd.DataFrame(rows, columns=["Experiment", *COLUMNS, "Water"])

def save_xlsx(df: pd.DataFrame, out_path: Path):
    # 需要：pip install xlsxwriter
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Table")

def generate_20_30_split_tables(out_dir=".", date_fmt="%d-%m-%Y"):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime(date_fmt)

    segments = split_values_by_sum(20, 30, MAX_SUM_PER_TABLE)
    # 对 20-30，默认会拆成：20-26（和=161），27-30（和=114）
    for idx, (a, b) in enumerate(segments, start=1):
        df = build_single_sheet_range(a, b, v_total=V_TOTAL)
        out_path = out_dir / f"{date_str}_20-30_part{idx}_{a}-{b}.xlsx"
        save_xlsx(df, out_path)
        print("Saved:", out_path)

if __name__ == "__main__":
    generate_20_30_split_tables(out_dir=".")