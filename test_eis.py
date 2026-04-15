import argparse
import os
import sys


WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import modules.eis_module as eis_module


def build_zero_dicts():
    mass_dict = {
        "NaCl": 0.0,
        "KCl": 0.0,
        "Urea": 0.0,
        "Na_lactate": 0.0,
        "NH4Cl": 0.0,
        "CaCl2": 0.0,
        "Glucose": 0.0,
        "WATER": 0.0,
    }
    target_dict = {
        "NaCl": 0.0,
        "KCl": 0.0,
        "Urea": 0.0,
        "Na_lactate": 0.0,
        "NH4Cl": 0.0,
        "CaCl2": 0.0,
        "Glucose": 0.0,
        "WATER": 0.0,
    }
    return mass_dict, target_dict


def main():
    parser = argparse.ArgumentParser(
        description="Only run EIS waveform test and save u_t/i_t images to Data/test"
    )
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Run without hardware (no real waveforms)",
    )
    parser.add_argument(
        "--exp-num",
        type=int,
        default=1,
        help="Experiment number used in output txt name",
    )
    args = parser.parse_args()

    output_dir = os.path.join(WORKSPACE_ROOT, "Data", "test")
    os.makedirs(output_dir, exist_ok=True)

    mass_dict, target_dict = build_zero_dicts()
    eis_module.SIMULATION_MODE = args.simulation

    print("=== EIS Waveform Test ===")
    print(f"Output folder: {output_dir}")
    print(f"Mode: {'SIMULATION' if args.simulation else 'HARDWARE'}")
    print("Expected images: V_*.png and I_*.png (u_t / i_t)")

    try:
        z_values = eis_module.main(
            mass_dict=mass_dict,
            target_concentrations=target_dict,
            output_folder=output_dir,
            experiment_num=args.exp_num,
        )
    except Exception as exc:
        print(f"\nEIS test failed: {exc}")
        return 2

    if z_values:
        print(f"\nEIS waveform test finished, collected {len(z_values)} points")
        print("Check Data/test/*/ for V_*.png and I_*.png")
        return 0

    print("\nEIS test finished but no data points were collected")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
