import pandas as pd
import random
from datetime import datetime
import os

# 化学物质顺序（与示例表格保持一致）
CHEMICALS = ['NaCl', 'KCl', 'Urea', 'Na_lactate', 'NH4Cl', 'CaCl2', 'Glucose', 'Water']

# 约束条件
MIN_VALUE = 3  # 非零最小值
MAX_ROW_SUM = 25  # 每行最大总和
TARGET_ROW_SUM = 25  # 目标行总和
MAX_COL_SUM = 200  # 每列最大总和
TARGET_COL_SUM = 200  # 目标列总和
NUM_ROWS = 40  # 生成的实验行数

def generate_row_with_constraints(col_sums, max_col_sum):
    """
    生成一行数据，满足行总和约为25，且不超过每列的剩余容量
    """
    row = [0] * len(CHEMICALS)
    remaining = TARGET_ROW_SUM
    
    # 获取可用的列索引（还没超过列限制的）
    available_cols = [i for i in range(len(CHEMICALS)) if col_sums[i] < max_col_sum]
    
    if not available_cols:
        return row
    
    # 随机选择要填充的列数（2-6个化学物质）
    num_to_fill = random.randint(2, min(6, len(available_cols)))
    selected_cols = random.sample(available_cols, num_to_fill)
    
    # 为每个选中的列分配值
    for i, col_idx in enumerate(selected_cols):
        if i == len(selected_cols) - 1:
            # 最后一个，分配剩余值
            available = min(remaining, max_col_sum - col_sums[col_idx])
            if available >= MIN_VALUE:
                value = available
            else:
                value = 0
        else:
            # 随机分配，但保留足够空间给后续
            max_possible = min(
                remaining - (len(selected_cols) - i - 1) * MIN_VALUE,  # 保留后续最小值
                max_col_sum - col_sums[col_idx],  # 不超过列限制
                remaining  # 不超过剩余值
            )
            
            if max_possible >= MIN_VALUE:
                # 生成一个3-max_possible之间的随机整数
                value = random.randint(MIN_VALUE, max_possible)
                # 以一定概率设为0（增加稀疏性）
                if random.random() < 0.3:
                    value = 0
            else:
                value = 0
        
        if value >= MIN_VALUE:
            row[col_idx] = value
            remaining -= value
            col_sums[col_idx] += value
        
        if remaining <= 0:
            break
    
    return row

def generate_table():
    """
    生成符合所有约束的随机实验表格
    """
    data = []
    col_sums = [0] * len(CHEMICALS)
    
    experiment_num = 1
    rows_generated = 0
    max_attempts = NUM_ROWS * 2  # 防止无限循环
    
    while rows_generated < NUM_ROWS and experiment_num < max_attempts:
        # 生成一行
        row = generate_row_with_constraints(col_sums, MAX_COL_SUM)
        
        # 检查行是否有效（至少有一个非零值）
        if sum(row) > 0:
            # 添加实验编号作为第一列
            data.append([experiment_num] + row)
            rows_generated += 1
        
        experiment_num += 1
        
        # 如果所有列都接近满了，停止生成
        if all(s >= TARGET_COL_SUM * 0.95 for s in col_sums):
            break
    
    # 创建DataFrame
    columns = ['Experiment'] + CHEMICALS
    df = pd.DataFrame(data, columns=columns)
    
    return df, col_sums

def main():
    print("开始生成随机实验表格...")
    print(f"约束条件:")
    print(f"  - 非零最小值: {MIN_VALUE} mL")
    print(f"  - 每行目标总和: ~{TARGET_ROW_SUM} mL")
    print(f"  - 每列目标总和: ~{TARGET_COL_SUM} mL")
    print(f"  - 目标生成行数: {NUM_ROWS}")
    
    # 生成表格
    df, col_sums = generate_table()
    
    # 生成文件名（今日日期）
    today = datetime.now().strftime("%Y%m%d")
    filename = f"{today}.xlsx"
    filepath = os.path.join(os.getcwd(), filename)
    
    # 保存到Excel
    df.to_excel(filepath, index=False)
    
    print(f"\n✓ 表格生成完成: {filename}")
    print(f"  生成行数: {len(df)}")
    print(f"  列数: {len(df.columns)}")
    print(f"\n每列总和统计:")
    for i, chem in enumerate(CHEMICALS):
        print(f"  {chem}: {col_sums[i]:.0f} mL ({col_sums[i]/TARGET_COL_SUM*100:.1f}%)")
    
    print(f"\n每行总和统计:")
    row_sums = df[CHEMICALS].sum(axis=1)
    print(f"  平均值: {row_sums.mean():.1f} mL")
    print(f"  最小值: {row_sums.min():.1f} mL")
    print(f"  最大值: {row_sums.max():.1f} mL")
    
    print(f"\n前5行预览:")
    print(df.head())

if __name__ == "__main__":
    main()
