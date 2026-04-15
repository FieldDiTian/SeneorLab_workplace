import sys
import os
import time
import numpy as np
import matplotlib.pyplot as plt
import dwfpy as dwf
from datetime import datetime
import pytz

# Set to True if testing without Analog Discovery connected
SIMULATION_MODE = False

def measure_impedance(device, freq, amp, r_series,
                      cycles=10, oversample=20, v_range=0.5,
                      settle_cycles=5,
                      return_waveform=False):
    """
    测量单频阻抗。
    默认接线假设:
        CH0 -> 激励端/串联电阻输入端 Vin
        CH1 -> 样品节点 Vs
    因此串联电阻电压为 Vr = Vin - Vs，电流为 I = Vr / R_series。
    当 return_waveform=True 时，额外返回时域波形 (t, v_sample, i_t)。
    """
    scope = device.analog_input
    wavegen = device.analog_output

    fs = freq * oversample
    total_cycles = cycles + settle_cycles
    duration = total_cycles / freq

    wavegen[0].setup(
        "sine",
        frequency=freq,
        amplitude=amp,
        offset=0,
        start=True
    )

    # 给波形发生器一点时间进入稳定输出，避免启动瞬态直接进入记录。
    time.sleep(min(0.05, max(0.0, 1.0 / fs)))

    scope[0].setup(range=v_range)
    scope[1].setup(range=v_range)
    recorder = scope.record(
        sample_rate=fs,
        length=duration,
        configure=True,
        start=True
    )

    v_in = np.array(recorder.channels[0].data_samples)
    v_sample = np.array(recorder.channels[1].data_samples)
    n_discard = min(len(v_in) // 2, int(round(settle_cycles * oversample)))
    if n_discard > 0:
        v_in = v_in[n_discard:]
        v_sample = v_sample[n_discard:]

    v_r = v_in - v_sample
    N = len(v_r)
    t = np.arange(N) / fs

    i_t = v_r / r_series
    v_sample_ac = v_sample - np.mean(v_sample)
    i_t_ac = i_t - np.mean(i_t)
    ph_v = np.sum(v_sample_ac * np.exp(-1j * 2 * np.pi * freq * t)) / N
    ph_i = np.sum(i_t_ac * np.exp(-1j * 2 * np.pi * freq * t)) / N

    Z = ph_v / ph_i

    if return_waveform:
        return Z, t, v_sample, i_t
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
        return f"{freq/1e6:.0f}MHZ"
    elif freq >= 1e3:
        return f"{freq/1e3:.0f}kHZ"
    else:
        return f"{freq:.0f}HZ"


def build_waveform_filename(freq):
    """
    为时域图生成带数值前缀的文件名，便于资源管理器按频率从小到大排序。
    例如: UI_0000001HZ_1HZ.png, UI_0001000HZ_1kHZ.png
    """
    return f"UI_{int(round(freq)):07d}HZ_{format_freq_label(freq)}.png"

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

def plot_time_domain(waveform_data, save_dir, oversample=80, cycles=30):
    """
        绘制每个频率点的 U(t) 和 I(t) 合并波形图。
        物理定义:
            - V(t): 样品两端电压 v_sample (CH1)
            - I(t): 串联电阻推算电流 i_t = (Vin - Vs) / R_series
    waveform_data: list of (freq, t, v_sample, i_t) 元组
    每个频率生成一张图：UI_频率.png
    """
    for freq, t, v_c, i_t in waveform_data:
        # 显示最后 5 个稳态周期，而不是起始瞬态。
        n_show = min(len(t), 5 * oversample)
        start_idx = max(0, len(t) - n_show)

        # 计算统计信息
        v_c_rms = np.sqrt(np.mean(v_c**2))
        v_c_peak = np.max(np.abs(v_c))
        i_t_rms = np.sqrt(np.mean(i_t**2))
        i_t_peak = np.max(np.abs(i_t))

        # 根据频率选择合适的时间单位
        t_window = t[start_idx:start_idx + n_show] - t[start_idx]
        total_time = t_window[-1] if n_show > 0 else t[-1]
        if total_time < 1e-3:
            t_plot = t_window * 1e6
            t_unit = 'μs'
        elif total_time < 1:
            t_plot = t_window * 1e3
            t_unit = 'ms'
        else:
            t_plot = t_window
            t_unit = 's'

        freq_label = format_freq_label(freq)

        i_plot_ua = i_t[start_idx:start_idx + n_show] * 1e6
        fig, (ax_v, ax_i) = plt.subplots(
            2, 1, figsize=(10, 8), sharex=True,
            gridspec_kw={'hspace': 0.28}
        )

        ax_v.plot(t_plot, v_c[start_idx:start_idx + n_show], color='#1f77b4', linewidth=0.8)
        ax_v.set_ylabel('Voltage (V)')
        ax_v.set_title(f'U(t) Sample @ {freq_label} [CH1, steady-state]\nRMS={v_c_rms:.4f}V, Peak={v_c_peak:.4f}V')
        ax_v.grid(True, alpha=0.3)

        ax_i.plot(t_plot, i_plot_ua, color='#d62728', linewidth=0.8)
        ax_i.set_xlabel(f'Time ({t_unit})')
        ax_i.set_ylabel('Current (uA)')
        ax_i.set_title(f'I(t) @ {freq_label} [(CH0-CH1)/Rs, steady-state]\nRMS={i_t_rms*1e6:.2f}uA, Peak={i_t_peak*1e6:.2f}uA')
        ax_i.grid(True, alpha=0.3)

        fig.tight_layout(h_pad=2.0)
        fig.savefig(os.path.join(save_dir, build_waveform_filename(freq)), dpi=300)
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
    oversample = 80
    
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
                f_text.write("Actual measured mass (g):\n")
                f_text.write(f"  NaCl={mass_dict.get('NaCl', 0):.4f}, KCl={mass_dict.get('KCl', 0):.4f}, Urea={mass_dict.get('Urea', 0):.4f}\n")
                f_text.write(f"  Lac={mass_dict.get('Na_lactate', 0):.4f}, NH4Cl={mass_dict.get('NH4Cl', 0):.4f}, CaCl2={mass_dict.get('CaCl2', 0):.4f}, Glu={mass_dict.get('Glucose', 0):.4f}\n")
                f_text.write(f"  Water={mass_dict.get('WATER', 0):.4f}\n")
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
            plot_time_domain(waveform_data, save_dir, oversample=oversample, cycles=cycles)
            print(f"    ✓ Saved {len(waveform_data)} combined waveform plots (U & I)")
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
