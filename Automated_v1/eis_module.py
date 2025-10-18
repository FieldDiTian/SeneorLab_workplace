import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import dwfpy as dwf
from datetime import datetime
import pytz

def measure_impedance(device, freq, amp, r_series,
                      cycles=10, oversample=10, v_range=5.0):
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

    i = v_r / r_series
    ph_v = np.sum(v_c * np.exp(-1j * 2 * np.pi * freq * t)) / N
    ph_i = np.sum(i * np.exp(-1j * 2 * np.pi * freq * t)) / N

    return ph_v / ph_i

def plot_impedance(freqs, Z_list, save_dir, base_filename):
    Z_magnitude = np.abs(Z_list)
    Z_phase = np.angle(Z_list, deg=True)
    Z_real = np.real(Z_list)
    Z_imag = np.imag(Z_list)

    # 1. Nyquist Plot
    plt.figure(figsize=(6, 5))
    plt.plot(Z_real, -Z_imag, marker='o')  # Flip Y-axis by plotting +Imag instead of -Imag; now change back to -Imag
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
    # plt.show()

def main():
    f_start = 1000e3
    f_stop = 1.0
    points = 150
    freqs = np.logspace(np.log10(f_start), np.log10(f_stop), num=points)

    amplitude = 0.05
    r_series = 1e3
    cycles = 30
    oversample = 20

    # Time and folder management
    tz = pytz.timezone('America/Los_Angeles')
    now = datetime.now(tz)
    date_str = now.strftime('%m%d%Y')
    base_folder = r"C:\\Users\\pmut\\Desktop\\Kang\\Data"
    today_folder_name = f"{date_str}_EIS_Data"
    save_dir = os.path.join(base_folder, today_folder_name)
    os.makedirs(save_dir, exist_ok=True)

    # Find how many text files already exist
    existing_txt_files = [f for f in os.listdir(save_dir) if f.endswith('.txt')]
    n = len(existing_txt_files) + 1

    text_filename = os.path.join(save_dir, f"{today_folder_name}_{n}.txt")
    base_filename = f"{today_folder_name}_{n}"

    with open(text_filename, 'w', encoding='utf-8') as f_text:
        with dwf.Device() as dev:
            info_line = f"✅ Opened: {dev.name} ({dev.serial_number})"
            print(info_line)
            f_text.write(info_line + '\n')

            Z_list = []
            for f in freqs:
                Z = measure_impedance(dev, f,
                                      amp=amplitude,
                                      r_series=r_series,
                                      cycles=cycles,
                                      oversample=oversample)
                Z_list.append(Z)
                line = f"→ {f:8.1f} Hz: |Z|={abs(Z):7.2f} Ω, ∦Z={np.angle(Z,deg=True):6.2f}°"
                print(line)
                f_text.write(line + '\n')

            f_text.write("\n—— Impedance Results List ——\n")
            f_text.write(str(Z_list) + '\n')

    plot_impedance(freqs, Z_list, save_dir, base_filename)

    return Z_list

if __name__ == "__main__":
    main()
