import os
import pandas as pd
import time
import sys
from datetime import datetime

# 确保能找到同级目录的模块
sys.path.append(os.getcwd())

# 导入模块
try:
    from modules.motorcontroller import MotorController
    from modules.scale_reader import wait_for_stable_weight, calculate_mass_change
    import modules.eis_module as eis_module
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# ================= 配置区域 =================

EXCEL_FOLDER = os.getcwd()

# 轴映射
AXIS_MAP = {
    'NaCl':       'X',
    'KCl':        'Y',
    'Urea':       'Z',
    'Na_lactate': 'U',
    'NH4Cl':      'V',
    'CaCl2':      'W',
    'Glucose':    'I',
    'WATER':      'J',
    'EXTRACT':    'K', # 废液泵
    'MIX':        'E', # 混匀
}

# 统一换算比例 (User: 全部用-20step/ML)
STEPS_PER_ML = -20

# 速度设置 (保持默认值)
SPEED = {
    'DISPENSE': 1000,
    'WATER':    4000,
    'EXTRACT':  4000,
    'MIX':      4000
}

# 实验参数
CONFIG = {
    'WASH_VOLUME': 25.0,     # 清洗用水量 (mL)
    'EXTRACT_STEPS': 2000,   # 抽废液步数 (固定值)
    'MIX_STEPS': 500,       # 混匀步数
    'WASH_CYCLES': 3,        # 清洗次数
    'MAX_WEIGHT_LIMIT': 140.0 # 电子秤安全限重 (g)
}

# 液体添加顺序 (Excel表格列顺序: 7种化学物质 + 水)
FLUID_ORDER = ['NaCl', 'KCl', 'Urea', 'Na_lactate', 'NH4Cl', 'CaCl2', 'Glucose', 'WATER']

# ================= 辅助函数 =================

def ml_to_steps(ml):
    """固定 -20 steps/mL"""
    return int(ml * STEPS_PER_ML)

def create_output_folder(excel_filename):
    """创建数据保存文件夹"""
    data_folder = os.path.join(EXCEL_FOLDER, 'Data')
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
    
    excel_basename = os.path.splitext(excel_filename)[0]
    output_folder = os.path.join(data_folder, excel_basename)
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    return output_folder

# ================= 主控制逻辑 =================

def run_experiment(motor, target_volumes, output_folder, experiment_num):
    """
    执行单次实验的主循环
    """
    print(f"\n=== 开始第 {experiment_num} 组实验 ===")
    print(f"目标体积配置 (mL): {target_volumes}")

    mass_records = {} # 记录每种物质的实际添加质量
    
    # --- 1. 抽出工作站中现有的液体 ---
    print("\n[Step 1] 抽出工作站现有液体 (Cleaning Table)...")
    motor.move_axis(AXIS_MAP['EXTRACT'], CONFIG['EXTRACT_STEPS'], SPEED['EXTRACT'], wait=True)
    
    # --- 2. 清洗工作台 (泵入水 -> 抽出) x Cycles ---
    print(f"\n[Step 2] 清洗工作台 ({CONFIG['WASH_CYCLES']}次)...")
    steps_wash_water = ml_to_steps(CONFIG['WASH_VOLUME'])
    
    for i in range(CONFIG['WASH_CYCLES']):
        print(f"  > Cleaning Cycle {i+1}/{CONFIG['WASH_CYCLES']}")
        # 泵入蒸馏水
        motor.move_axis(AXIS_MAP['WATER'], steps_wash_water, SPEED['WATER'], wait=True)
        # 抽出
        motor.move_axis(AXIS_MAP['EXTRACT'], CONFIG['EXTRACT_STEPS'], SPEED['EXTRACT'], wait=True)
    
    # --- 3. 读取数据 (已在外部Main完成) ---
    # target_volumes 包含了表格中读取的8种物质的体积
    
    # --- 4. 称重 (Tare) ---
    print("\n[Step 4] 初始称重 (Tare)...")
    time.sleep(1)
    current_weight = wait_for_stable_weight()
    print(f"  初始读数: {current_weight:.4f} g")

    # --- 5 & 6. 循环配置溶液 (7种化学物质 + 水) ---
    print("\n[Step 5-6] 配置溶液循环...")
    
    for name in FLUID_ORDER:
        vol = target_volumes.get(name, 0)
        
        # 保护功能：如果表格中数值为0或接近0，直接跳过，质量记为0
        if vol == 0 or abs(vol) < 0.001:
            print(f"  跳过 {name} (表格数值=0，不进行泵入和称重)")
            mass_records[name] = 0.0
            continue
            
        print(f"  -> 正在加入 {name} ({vol:.2f} mL)...")
        
        # 5. 泵入物质
        steps = ml_to_steps(vol)
        motor.move_axis(AXIS_MAP[name], steps, SPEED['DISPENSE'], wait=True)
        
        # 等待液体稳定
        time.sleep(1.5)
        
        # 6. 称重，计算差值
        new_weight = wait_for_stable_weight()
        added_mass = calculate_mass_change(current_weight, new_weight)
        
        # 记录数据
        mass_records[name] = added_mass
        if added_mass > 0:
            print(f"     {name} 实际加入质量: {added_mass:.4f} g")
        
        # 更新当前重量
        current_weight = new_weight
        
        if current_weight > CONFIG['MAX_WEIGHT_LIMIT']:
            print(f"警告: 重量超过安全限制 ({current_weight:.2f} > {CONFIG['MAX_WEIGHT_LIMIT']})")

    # --- 7. 泵入气体混合液体 ---
    print("\n[Step 7] 气体混匀 (Mixing)...")
    motor.move_axis(AXIS_MAP['MIX'], CONFIG['MIX_STEPS'], SPEED['MIX'], wait=True)
    time.sleep(2) # 等待混匀稳定

    # --- 8. EIS扫描，记录数据 ---
    print("\n[Step 8] EIS 扫描 & 数据记录...")
    # 注意：为了兼容 eis_module，我们将 target_volumes 传给 target_concentrations 参数
    # eis_module 可能会显示 "浓度(mM)"，但实际上记录的是我们表格里的 mL 数值
    try:
        eis_module.main(
            mass_dict=mass_records,
            target_concentrations=target_volumes,
            output_folder=output_folder,
            experiment_num=experiment_num
        )
    except Exception as e:
        print(f"EIS Error: {e}")

    # --- 9. 回到起始点 (循环在外部控制) ---
    print(f"=== 实验 {experiment_num} 完成 ===\n")


def main():
    print(f"启动中央控制系统 (Central Control) - 直读体积模式")
    print(f"扫描目录: {EXCEL_FOLDER}")
    print(f"全局换算比例: {STEPS_PER_ML} steps/mL")
    
    excel_files = [f for f in os.listdir(EXCEL_FOLDER) if f.endswith('.xlsx') and not f.startswith('~$')]

    if not excel_files:
        print("未找到 .xlsx 实验文件。")
        return

    # 初始化电机控制器
    try:
        print("正在初始化电机控制器...")
        motor = MotorController(auto_enable=True)
    except Exception as e:
        print(f"无法连接电机控制器: {e}")
        return

    try:
        for file in excel_files:
            file_path = os.path.join(EXCEL_FOLDER, file)
            print(f"\n处理文件: {file}")
            output_folder = create_output_folder(file)
            
            try:
                # 读取Excel，第一行作为表头
                df = pd.read_excel(file_path, header=0)
            except Exception as e:
                print(f"读取Excel失败: {e}")
                continue

            # 判断第一列是否为实验编号列
            first_col_name = df.columns[0] if len(df.columns) > 0 else ""
            has_exp_num_col = False
            data_start_col = 0
            
            # 检查第一列是否为编号列（列名可能是"编号"、"Experiment"、"No"等，或者全是数字）
            if first_col_name in ['编号', 'Experiment', 'No', 'ID', 'Exp']:
                has_exp_num_col = True
                data_start_col = 1
                print(f"检测到实验编号列: {first_col_name}")
            elif len(df) > 0:
                # 检查第一列数据是否全是数字（作为编号）
                try:
                    first_col_data = pd.to_numeric(df.iloc[:, 0], errors='coerce')
                    if first_col_data.notna().sum() / len(first_col_data) > 0.8:  # 80%以上是数字
                        has_exp_num_col = True
                        data_start_col = 1
                        print(f"检测到第一列为实验编号列")
                except:
                    pass

            # 遍历每一行
            for index, row in df.iterrows():
                # 获取实验编号
                if has_exp_num_col:
                    # 使用第一列的值作为实验编号
                    try:
                        experiment_num = int(row.iloc[0])
                    except (ValueError, TypeError):
                        experiment_num = index + 1
                else:
                    # 使用行索引作为实验编号（数据从第1行开始，表头已被跳过）
                    experiment_num = index + 1
                
                # 读取化学物质数据（从data_start_col开始的8列）
                target_volumes = {}
                row_valid = False
                
                for i, fluid_name in enumerate(FLUID_ORDER):
                    col_idx = data_start_col + i
                    if col_idx < len(row):
                        val = row.iloc[col_idx]
                        if pd.notna(val):
                            try:
                                vol = float(val)
                                target_volumes[fluid_name] = vol
                                if vol > 0:
                                    row_valid = True
                            except ValueError:
                                target_volumes[fluid_name] = 0.0
                        else:
                            target_volumes[fluid_name] = 0.0
                    else:
                        target_volumes[fluid_name] = 0.0
                
                # 如果全行为空或0，跳过
                if not row_valid:
                     print(f"跳过空行 {experiment_num}")
                     continue

                # 执行实验
                run_experiment(motor, target_volumes, output_folder, experiment_num)
                
                time.sleep(2)

    except KeyboardInterrupt:
        print("\n用户中断实验。")
    except Exception as e:
        print(f"\n发生未知错误: {e}")
    finally:
        print("关闭电机连接...")
        motor.close()
        print("程序结束。")

if __name__ == "__main__":
    main()