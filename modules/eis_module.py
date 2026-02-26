import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import dwfpy as dwf
from datetime import datetime
import pytz

# Set to True if testing without Analog Discovery connected
SIMULATION_MODE = False

def measure_impedance(device, freq, amp, r_series,
                      cycles=10, oversample=20, v_range=5.0,
                      return_waveform=False):
    """
    测量单频阻抗。
    当 return_waveform=True 时，额外返回时域波形 (t, v_c, i_t)。
    """
    scope = device.analog_input
    wavegen = device.analog_output

    fs = freq * oversample
    duration = cycles / freq

    wavegen[0].setup(
        "sine",
        frequency=freq,
        amplitude=amp,
        offset=0,
        start=True
    )

    for ch in (0, 1):
        scope[ch].setup(range=v_range)
    recorder = scope.record(
        sample_rate=fs,
        length=duration,
        configure=True,
        start=True
    )

    wavegen[0].setup(
        "sine",
        frequency=freq,
        amplitude=amp,
        offset=amp,
        start=False
    )

    v_r = np.array(recorder.channels[0].data_samples)
    v_c = np.array(recorder.channels[1].data_samples)
    N = len(v_r)
    t = np.arange(N) / fs

    i_t = v_r / r_series
    ph_v = np.sum(v_c * np.exp(-1j * 2 * np.pi * freq * t)) / N
    ph_i = np.sum(i_t * np.exp(-1j * 2 * np.pi * freq * t)) / N

    Z = ph_v / ph_i

    if return_waveform:
        return Z, t, v_c, i_t
    return Z

def plot_impedance(freqs, Z_list, save_dir, base_filename):
    Z_magnitude = np.abs(Z_list)
    Z_phase = np.angle(Z_list, deg=True)
    Z_real = np.real(Z_list)
    Z_imag = np.imag(Z_list)

    # 1. Nyquist Plot
    plt.figure(figsize=(6, 5))
    plt.plot(Z_real, -Z_imag, marker='o')
    plt.xlabel('Real(Z) (Ohm)')
    plt.ylabel('-Imag(Z) (Ohm)')
    plt.title('Nyquist Plot')
    plt.grid(True)
    plt.axis('equal')
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, f"{base_filename}_Nyquist Plot.png"), dpi=300)
    plt.close()

    # 2. Bode Magnitude Plot
    plt.figure(figsize=(6, 5))
    plt.semilogx(freqs, Z_magnitude, marker='o')
    plt.gca().invert_xaxis()
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('|Z| (Ohm)')
    plt.title('Bode Plot - Magnitude')
    plt.grid(True, which="both", linestyle="--")
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, f"{base_filename}_Bode Plot - Magnitude.png"), dpi=300)
    plt.close()

    # 3. Bode Phase Plot
    plt.figure(figsize=(6, 5))
    plt.semilogx(freqs, Z_phase, marker='o')
    plt.gca().invert_xaxis()
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Phase (degrees)')
    plt.title('Bode Plot - Phase')
    plt.grid(True, which="both", linestyle="--")
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, f"{base_filename}_Bode Plot - Phase.png"), dpi=300)
    plt.close()

def generate_freq_list():
    """
    生成频率列表：
    1,2,3,...,10, 20,30,...,100, 200,300,...,1000, ..., 200000,300000,...,1000000
    每个decade内取 base*1 ~ base*10，去重后共55个点，从高频到低频排列。
    """
    freqs = []
    for k in range(6):  # 10^0 到 10^5
        base = 10 ** k
        for m in range(1, 11):
            freqs.append(base * m)
    freqs = sorted(set(freqs), reverse=True)
    return np.array(freqs, dtype=float)

def format_freq_label(freq):
    """将频率数值格式化为可读标签，用于文件名"""
    if freq >= 1e6:
        return f"{freq/1e6:.0f}MHz"
    elif freq >= 1e3:
        return f"{freq/1e3:.0f}kHz"
    else:
        return f"{freq:.0f}Hz"

def build_composition_folder_name(mass_dict):
    """根据化学物质组成构建文件夹名"""
    parts = []
    parts.append(f"NaCl_{mass_dict.get('NaCl', 0):.4f}g")
    parts.append(f"KCl_{mass_dict.get('KCl', 0):.4f}g")
    parts.append(f"Urea_{mass_dict.get('Urea', 0):.4f}g")
    parts.append(f"Lac_{mass_dict.get('Na_lactate', 0):.4f}g")
    parts.append(f"NH4Cl_{mass_dict.get('NH4Cl', 0):.4f}g")
    parts.append(f"CaCl2_{mass_dict.get('CaCl2', 0):.4f}g")
    parts.append(f"Glu_{mass_dict.get('Glucose', 0):.4f}g")
    parts.append(f"Water_{mass_dict.get('WATER', 0):.4f}g")
    return "_".join(parts)

def plot_time_domain(waveform_data, save_dir):
    """
    绘制每个频率点的 V(t) 和 i(t) 波形图，分开保存。
    waveform_data: list of (freq, t, v_c, i_t) 元组
    每个频率生成两张图：V_频率.png 和 I_频率.png
    """
    for freq, t, v_c, i_t in waveform_data:
        # 只显示前5个周期
        samples_per_cycle = int(len(t) / (len(t) * freq / (len(t) / (freq * 20))) ) if freq > 0 else len(t)
        n_show = min(len(t), int(5 * 20))  # 5个周期 × oversample(20)
        if n_show < 10 or n_show > len(t):
            n_show = len(t)

        # 根据频率选择合适的时间单位
        total_time = t[n_show - 1] if n_show > 0 else t[-1]
        if total_time < 1e-3:
            t_plot = t[:n_show] * 1e6
            t_unit = 'μs'
        elif total_time < 1:
            t_plot = t[:n_show] * 1e3
            t_unit = 'ms'
        else:
            t_plot = t[:n_show]
            t_unit = 's'

        freq_label = format_freq_label(freq)

        # --- V(t) 图 ---
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(t_plot, v_c[:n_show], color='#1f77b4', linewidth=0.8)
        ax.set_xlabel(f'Time ({t_unit})')
        ax.set_ylabel('Voltage (V)')
        ax.set_title(f'V(t) @ {freq_label}')
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(save_dir, f"V_{freq_label}.png"), dpi=300)
        plt.close(fig)

        # --- I(t) 图 ---
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(t_plot, i_t[:n_show] * 1e3, color='#d62728', linewidth=0.8)
        ax.set_xlabel(f'Time ({t_unit})')
        ax.set_ylabel('Current (mA)')
        ax.set_title(f'I(t) @ {freq_label}')
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(save_dir, f"I_{freq_label}.png"), dpi=300)
        plt.close(fig)

def main(mass_dict=None, target_concentrations=None, output_folder=None, experiment_num=None):
    """
    运行EIS测量
    
    Args:
        mass_dict: 实际称重质量字典 {'NaCl': 0.0234, 'KCl': 0.0189, ...} (g)
        target_concentrations: 目标浓度字典 {'NaCl': 10, 'KCl': 5, ...} (mM)
        output_folder: 自定义输出文件夹，如果为None则使用默认路径
        experiment_num: 实验编号，如果为None则自动编号
    """
    
    # 兼容旧版本直接传浓度的方式
    if mass_dict is None:
        mass_dict = {}
    if target_concentrations is None:
        target_concentrations = {}
    
    # 使用线性decade频率列表: 1-10, 10-100, ..., 100k-1M
    freqs = generate_freq_list()

    amplitude = 0.5
    r_series = 1e3
    cycles = 30
    oversample = 20
    
    # 构建文件夹: Data/化学物质组成/    (或 output_folder/化学物质组成/)
    composition_name = build_composition_folder_name(mass_dict)
    if output_folder:
        save_dir = os.path.join(output_folder, composition_name)
    else:
        base_folder = os.path.join(os.getcwd(), "Data")
        save_dir = os.path.join(base_folder, composition_name)
    
    os.makedirs(save_dir, exist_ok=True)

    # 实验编号
    if experiment_num is not None:
        n = experiment_num
    else:
        existing_txt_files = [f for f in os.listdir(save_dir) if f.endswith('.txt')]
        n = len(existing_txt_files) + 1
    
    # txt 数据文件放在同一文件夹内
    text_filename = os.path.join(save_dir, f"EIS_Data_{n}.txt")
    print(f"    Saving to folder: {composition_name}/")
    print(f"    Data file: EIS_Data_{n}.txt")

    if SIMULATION_MODE:
        Z_list = [1000 for _ in freqs]
        with open(text_filename, 'w') as f: 
            f.write("Simulation Mode\n")
        print("    Simulation mode - no actual measurement")
        return Z_list

    # Import dwfpy only when actually needed (not in simulation mode)
    import dwfpy as dwf

    try:
        with open(text_filename, 'w', encoding='utf-8') as f_text:
            with dwf.Device() as dev:
                info_line = f"✅ Opened: {dev.name} ({dev.serial_number})"
                print(info_line)
                f_text.write(info_line + '\n')
                f_text.write("实际称重质量 (g):\n")
                f_text.write(f"  NaCl={mass_dict.get('NaCl', 0):.4f}, KCl={mass_dict.get('KCl', 0):.4f}, Urea={mass_dict.get('Urea', 0):.4f}\n")
                f_text.write(f"  Lac={mass_dict.get('Na_lactate', 0):.4f}, NH4Cl={mass_dict.get('NH4Cl', 0):.4f}, CaCl2={mass_dict.get('CaCl2', 0):.4f}, Glu={mass_dict.get('Glucose', 0):.4f}\n")
                f_text.write(f"  Water={mass_dict.get('WATER', 0):.4f}\n")
                f_text.write("目标体积 (mL):\n")
                f_text.write(f"  NaCl={target_concentrations.get('NaCl', 0)}, KCl={target_concentrations.get('KCl', 0)}, Urea={target_concentrations.get('Urea', 0)}\n")
                f_text.write(f"  Lac={target_concentrations.get('Na_lactate', 0)}, NH4Cl={target_concentrations.get('NH4Cl', 0)}, CaCl2={target_concentrations.get('CaCl2', 0)}, Glu={target_concentrations.get('Glucose', 0)}\n")
                f_text.write(f"  Water={target_concentrations.get('WATER', 0)}\n")
                f_text.write("-" * 50 + "\n")
                
                Z_list = []
                waveform_data = []

                for idx, f in enumerate(freqs):
                    result = measure_impedance(dev, f,
                                          amp=amplitude,
                                          r_series=r_series,
                                          cycles=cycles,
                                          oversample=oversample,
                                          return_waveform=True)
                    Z, t_wave, v_c_wave, i_t_wave = result
                    waveform_data.append((f, t_wave, v_c_wave, i_t_wave))
                    Z_list.append(Z)
                    # 保存数值格式：频率, 实部, 虚部, 模, 相位
                    f_text.write(f"{f:.4f}, {Z.real:.4f}, {Z.imag:.4f}, {abs(Z):.4f}, {np.angle(Z, deg=True):.4f}\n")
                    # 打印可读格式
                    line = f"→ {f:8.1f} Hz: |Z|={abs(Z):7.2f} Ω, ∦Z={np.angle(Z,deg=True):6.2f}°"
                    print(line)

        if waveform_data:
            plot_time_domain(waveform_data, save_dir)
            print(f"    ✓ Saved {len(waveform_data) * 2} waveform plots (V & I)")
        print(f"    ✓ Measurement complete!")
        return Z_list

    except Exception as e:
        print(f"    EIS Error: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    print("Starting EIS test with zero mass...")
    test_mass = {'NaCl': 0, 'KCl': 0, 'Urea': 0, 'Na_lactate': 0, 'NH4Cl': 0, 'CaCl2': 0, 'Glucose': 0}
    test_target = {'NaCl': 0, 'KCl': 0, 'Urea': 0, 'Na_lactate': 0, 'NH4Cl': 0, 'CaCl2': 0, 'Glucose': 0}
    result = main(mass_dict=test_mass, target_concentrations=test_target)
    print(f"Test complete. Measured {len(result)} frequency points.")