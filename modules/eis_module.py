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

def plot_time_domain(waveform_data, save_dir, base_filename):
    """
    绘制选定频率点的时域 V(t) 和 i(t) 波形图。
    waveform_data: list of (freq, t, v_c, i_t) 元组
    每个频率生成一张双轴图：左轴电压，右轴电流。
    """
    for freq, t, v_c, i_t in waveform_data:
        # 只显示前几个周期，避免图太密
        show_cycles = min(5, len(t))
        n_show = min(len(t), int(5 / freq * (freq * 20)))  # 5个周期的采样点数
        if n_show < 10:
            n_show = len(t)
        
        t_ms = t[:n_show] * 1e3  # 转为毫秒 (高频) 或保持秒
        v_show = v_c[:n_show]
        i_show = i_t[:n_show]

        # 根据频率选择合适的时间单位
        total_time = t[n_show - 1] if n_show > 0 else t[-1]
        if total_time < 1e-3:
            t_plot = t[:n_show] * 1e6  # μs
            t_unit = 'μs'
        elif total_time < 1:
            t_plot = t[:n_show] * 1e3  # ms
            t_unit = 'ms'
        else:
            t_plot = t[:n_show]        # s
            t_unit = 's'

        # 格式化频率标签
        if freq >= 1e6:
            freq_label = f"{freq/1e6:.1f} MHz"
        elif freq >= 1e3:
            freq_label = f"{freq/1e3:.1f} kHz"
        else:
            freq_label = f"{freq:.1f} Hz"

        fig, ax1 = plt.subplots(figsize=(8, 4))

        color_v = '#1f77b4'
        color_i = '#d62728'

        ax1.plot(t_plot, v_show, color=color_v, linewidth=0.8, label='V(t)')
        ax1.set_xlabel(f'Time ({t_unit})')
        ax1.set_ylabel('Voltage V(t) (V)', color=color_v)
        ax1.tick_params(axis='y', labelcolor=color_v)

        ax2 = ax1.twinx()
        ax2.plot(t_plot, i_show * 1e3, color=color_i, linewidth=0.8, label='i(t)')  # mA
        ax2.set_ylabel('Current i(t) (mA)', color=color_i)
        ax2.tick_params(axis='y', labelcolor=color_i)

        fig.suptitle(f'Time-Domain Waveform @ {freq_label}', fontsize=12)
        ax1.grid(True, alpha=0.3)

        # 合并图例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

        fig.tight_layout()
        safe_freq = freq_label.replace(' ', '_')
        fig.savefig(os.path.join(save_dir, f"{base_filename}_Waveform_{safe_freq}.png"), dpi=300)
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
    
    f_start = 1e6       # 1 MHz
    f_stop = 1.0        # 1 Hz
    points = 60         # 6 decades × 10 points/decade = 60
    freqs = np.logspace(np.log10(f_start), np.log10(f_stop), num=points)

    amplitude = 0.5
    r_series = 1e3
    cycles = 30
    oversample = 20
    
    # 如果指定了output_folder，则使用该文件夹
    if output_folder:
        save_dir = output_folder
    else:
        # 使用默认路径
        base_folder = os.path.join(os.getcwd(), "Data") 
        tz = pytz.timezone('America/Los_Angeles')
        now = datetime.now(tz)
        date_str = now.strftime('%m%d%Y')
        today_folder_name = f"{date_str}_EIS_Data"
        save_dir = os.path.join(base_folder, today_folder_name)
    
    os.makedirs(save_dir, exist_ok=True)

    # 如果指定了experiment_num，则使用该编号，否则自动编号
    if experiment_num is not None:
        n = experiment_num
    else:
        existing_txt_files = [f for f in os.listdir(save_dir) if f.endswith('.txt')]
        n = len(existing_txt_files) + 1
    
    # 构建文件名 - 使用实际称重质量 (g)
    fname_parts = [f"EIS_Data", f"{n}"]
    fname_parts.append(f"NaCl_{mass_dict.get('NaCl', 0):.4f}g")
    fname_parts.append(f"KCl_{mass_dict.get('KCl', 0):.4f}g")
    fname_parts.append(f"Urea_{mass_dict.get('Urea', 0):.4f}g")
    fname_parts.append(f"Lac_{mass_dict.get('Na_lactate', 0):.4f}g")
    fname_parts.append(f"NH4Cl_{mass_dict.get('NH4Cl', 0):.4f}g")
    fname_parts.append(f"CaCl2_{mass_dict.get('CaCl2', 0):.4f}g")
    fname_parts.append(f"Glu_{mass_dict.get('Glucose', 0):.4f}g")
    fname_parts.append(f"Water_{mass_dict.get('WATER', 0):.4f}g")

    base_filename = "_".join(fname_parts)
    text_filename = os.path.join(save_dir, base_filename + ".txt")
    print(f"    Saving Data: {base_filename}.txt")

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
            plot_time_domain(waveform_data, save_dir, base_filename)
            print(f"    ✓ Saved {len(waveform_data)} time-domain waveform plots")
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