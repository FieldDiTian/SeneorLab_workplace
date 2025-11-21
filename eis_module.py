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
                      cycles=10, oversample=20, v_range=5.0):
    scope = device.analog_input
    wavegen = device.analog_output
    fs = freq * oversample
    duration = cycles / freq

    wavegen[0].setup("sine", frequency=freq, amplitude=amp, offset=0, start=True)
    for ch in (0, 1): scope[ch].setup(range=v_range)
    recorder = scope.record(sample_rate=fs, length=duration, configure=True, start=True)
    wavegen[0].setup("sine", frequency=freq, amplitude=amp, offset=0, start=True)
    recorder.wait()
    
    v_r = np.array(recorder.channels[0].data_samples)
    v_c = np.array(recorder.channels[1].data_samples)
    
    N = len(v_r)
    t = np.arange(N) / fs
    ref_sin = np.exp(-1j * 2 * np.pi * freq * t)
    
    V_r_phasor = np.sum(v_r * ref_sin)
    V_c_phasor = np.sum(v_c * ref_sin)
    I_phasor = V_r_phasor / r_series
    Z = V_c_phasor / I_phasor
    return Z

def plot_impedance(freqs, Z_list, save_dir, base_filename):
    Z_magnitude = np.abs(Z_list)
    Z_phase = np.angle(Z_list, deg=True)
    Z_real = np.real(Z_list)
    Z_imag = np.imag(Z_list)

    # Nyquist
    plt.figure(figsize=(6, 5))
    plt.plot(Z_real, -Z_imag, marker='o')
    plt.title('Nyquist Plot')
    plt.grid(True)
    plt.axis('equal')
    plt.savefig(os.path.join(save_dir, f"{base_filename}_Nyquist.png"), dpi=300)
    plt.close()

    # Bode Mag
    plt.figure(figsize=(6, 5))
    plt.semilogx(freqs, Z_magnitude, marker='o')
    plt.title('Bode Plot - Magnitude')
    plt.grid(True, which="both", linestyle="--")
    plt.savefig(os.path.join(save_dir, f"{base_filename}_Bode_Mag.png"), dpi=300)
    plt.close()

    # Bode Phase
    plt.figure(figsize=(6, 5))
    plt.semilogx(freqs, Z_phase, marker='o')
    plt.title('Bode Plot - Phase')
    plt.grid(True, which="both", linestyle="--")
    plt.savefig(os.path.join(save_dir, f"{base_filename}_Bode_Phase.png"), dpi=300)
    plt.close()

def main(nacl, kcl, urea, 
         na_lactate=0, nh4cl=0, cacl2=0, glucose=0):
    
    f_start = 1000e3
    f_stop = 1.0
    points = 50
    freqs = np.logspace(np.log10(f_start), np.log10(f_stop), num=points)
    amplitude = 0.1
    r_series = 1e3
    
    base_folder = os.path.join(os.getcwd(), "Data") 
    tz = pytz.timezone('America/Los_Angeles')
    now = datetime.now(tz)
    date_str = now.strftime('%m%d%Y')
    today_folder_name = f"{date_str}_EIS_Data"
    save_dir = os.path.join(base_folder, today_folder_name)
    os.makedirs(save_dir, exist_ok=True)

    existing = len([f for f in os.listdir(save_dir) if f.endswith('.txt')]) + 1
    fname_parts = [f"{today_folder_name}", f"{existing}"]
    
    # Dynamic Filename
    fname_parts.append(f"NaCl_{nacl:.2f}")
    fname_parts.append(f"KCl_{kcl:.2f}")
    fname_parts.append(f"Urea_{urea:.2f}")
    
    if na_lactate > 0: fname_parts.append(f"Lac_{na_lactate:.2f}")
    if nh4cl > 0:      fname_parts.append(f"NH4Cl_{nh4cl:.2f}")
    if cacl2 > 0:      fname_parts.append(f"CaCl2_{cacl2:.2f}")
    if glucose > 0:    fname_parts.append(f"Glu_{glucose:.2f}")

    base_filename = "_".join(fname_parts)
    text_filename = os.path.join(save_dir, base_filename + ".txt")
    print(f"    Saving Data: {base_filename}.txt")

    if SIMULATION_MODE:
        Z_list = [1000 for _ in freqs]
        with open(text_filename, 'w') as f: f.write("Simulation")
        return Z_list

    try:
        with open(text_filename, 'w', encoding='utf-8') as f_text:
            with dwf.Device() as dev:
                info = f"Device Open: {dev.name} ({dev.serial_number})"
                print("    " + info)
                f_text.write(info + '\n')
                f_text.write(f"Config: NaCl={nacl}, KCl={kcl}, Urea={urea}, Lac={na_lactate}, NH4Cl={nh4cl}, CaCl2={cacl2}, Glu={glucose}\n")
                f_text.write("-" * 50 + "\n")
                
                Z_list = []
                for f in freqs:
                    Z = measure_impedance(dev, f, amplitude, r_series)
                    Z_list.append(Z)
                    f_text.write(f"{f:.4f}, {Z.real:.4f}, {Z.imag:.4f}, {abs(Z):.4f}, {np.angle(Z, deg=True):.4f}\n")

        plot_impedance(freqs, np.array(Z_list), save_dir, base_filename)
        return Z_list

    except Exception as e:
        print(f"    EIS Error: {e}")
        return []

if __name__ == "__main__":
    main(10, 0, 0)