import itertools
from pathlib import Path
import pandas as pd

CHEMS = ["NaCl", "KCl", "Urea", "Na_lactate", "NH4Cl", "CaCl2", "Glucose"]

V_TOTAL = 30
STOCK_LIMIT = 200

# 只做 3-30（不生成0）
LEVELS = list(range(3, V_TOTAL + 1))  # 3..30

OUT_DIR = Path("./B1_pairs")
FILE_BASENAME = "2_pair"  # 输出：2_pair_part1.xlsx, 2_pair_part2.xlsx ...

def generate_all_B1_rows():
    """
    生成两两组合行（B1网格）：
    - 两个化学物质都在 3..30（不允许0）
    - 仅保留 a+b<=30（保证Water>=0）
    - 其他5列=0
    """
    rows = []
    for a, b in itertools.combinations(CHEMS, 2):
        for va in LEVELS:
            for vb in LEVELS:
                if va + vb <= V_TOTAL:
                    r = {c: 0 for c in CHEMS}
                    r[a] = int(va)
                    r[b] = int(vb)
                    r["Water"] = int(V_TOTAL - va - vb)
                    rows.append(r)
    return rows

def can_place(row, sums):
    for c in CHEMS:
        if sums[c] + row[c] > STOCK_LIMIT:
            return False
    return True

def placement_score(row, sums):
    """
    贪心装箱打分：优先填补“剩余最小”的列，让7列尽量一起接近200。
    """
    rem_after = []
    used = 0
    for c in CHEMS:
        if row[c] > 0:
            used += row[c]
            rem_after.append(STOCK_LIMIT - (sums[c] + row[c]))
    # 这里rem_after一定非空，因为两列都>=3
    return (min(rem_after), -used)

def pack_rows_into_files(rows):
    """
    将所有行重排并装入多个xlsx：
    约束：每个xlsx内任意单列累计<=200
    目标：让7列共同尽量填满（更接近 7*200 的“总容量”）
    """
    remaining = rows[:]
    files = []

    while remaining:
        sums = {c: 0 for c in CHEMS}
        block = []

        while True:
            best_idx = None
            best_sc = None

            for i, r in enumerate(remaining):
                if can_place(r, sums):
                    sc = placement_score(r, sums)
                    if best_sc is None or sc < best_sc:
                        best_sc = sc
                        best_idx = i

            if best_idx is None:
                break

            r = remaining.pop(best_idx)
            block.append(r)
            for c in CHEMS:
                sums[c] += r[c]

            if all(sums[c] == STOCK_LIMIT for c in CHEMS):
                break

        files.append((block, sums))

    return files

def save_files(files):
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for part_idx, (block, sums) in enumerate(files, start=1):
        df_rows = []
        for exp_id, r in enumerate(block, start=1):
            df_rows.append({"Experiment": exp_id, **{c: r[c] for c in CHEMS}, "Water": r["Water"]})
        df = pd.DataFrame(df_rows, columns=["Experiment", *CHEMS, "Water"])

        path = OUT_DIR / f"{FILE_BASENAME}_part{part_idx}.xlsx"
        with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Table")

        # 校验：每列<=200
        col_sums = df[CHEMS].sum().to_dict()
        ok = all(col_sums[c] <= STOCK_LIMIT for c in CHEMS)
        print(f"Saved: {path} | rows={len(df)} | ok={ok} | col_sums={col_sums}")

def main():
    # 依赖：pip install pandas xlsxwriter
    rows = generate_all_B1_rows()
    files = pack_rows_into_files(rows)
    save_files(files)

if __name__ == "__main__":
    main()