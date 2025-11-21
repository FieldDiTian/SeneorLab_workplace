import os
import pandas as pd
import time
import sys

# Ensure imports work
sys.path.append(os.getcwd())

try:
    from automated_pipeline import automated_pipeline
except ImportError:
    print("Error: Cannot find automated_pipeline.py")
    sys.exit(1)

EXCEL_FOLDER = os.getcwd()

# Define the order of chemicals corresponding to Excel columns
CHEMICAL_ORDER = [
    'NaCl', 'KCl', 'Urea', 'Na_lactate', 'NH4Cl', 'CaCl2', 'Glucose'
]

def main():
    print(f"Scanning folder: {EXCEL_FOLDER}")
    
    excel_files = [f for f in os.listdir(EXCEL_FOLDER) if f.endswith('.xlsx') and not f.startswith('~$')]

    if not excel_files:
        print("No .xlsx files found.")
        return

    print(f"Found files: {excel_files}")

    for file in excel_files:
        file_path = os.path.join(EXCEL_FOLDER, file)
        print(f"\nProcessing: {file}")
        
        try:
            # Read all columns, don't assume a header
            df = pd.read_excel(file_path, header=None)
        except Exception as e:
            print(f"Read error: {e}")
            continue

        for index, row in df.iterrows():
            print(f"\n--- Reading Row {index+1} ---")
            
            target_concentrations = {}
            # Iterate through the expected chemical columns
            for i, chemical_name in enumerate(CHEMICAL_ORDER):
                # Check if the row has this many columns and the value is not null
                if i < len(row) and pd.notna(row.iloc[i]):
                    try:
                        conc = float(row.iloc[i])
                        if conc > 0:
                            target_concentrations[chemical_name] = conc
                    except (ValueError, TypeError):
                        # Ignore columns with non-numeric data
                        continue
            
            if not target_concentrations:
                print(f"Skipping row {index+1} (No valid concentrations found)")
                continue

            # Call the pipeline with the dictionary of concentrations
            result = automated_pipeline(target_concentrations)
            
            if "Error" in result:
                print("Error occurred during pipeline execution. Pausing for 10 seconds...")
                time.sleep(10)
            
            # Wait a moment before starting the next run
            time.sleep(3)

    print("\nAll tasks finished!")

if __name__ == "__main__":
    main()