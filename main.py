import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import filedialog
import os
from datetime import datetime


# Check environment and import visualization libraries
try:
   import matplotlib.pyplot as plt
   import seaborn as sns
   from matplotlib.colors import LinearSegmentedColormap
except ModuleNotFoundError:
   print("\n[ERROR] Please run: pip install matplotlib seaborn")
   exit()




def run_cardiac_analysis_final_v6():
   # --- 1. File Selection ---
   root = tk.Tk()
   root.withdraw()
   root.attributes('-topmost', True)
   file_path = filedialog.askopenfilename(title="Select Cardiac Metrics CSV", filetypes=[("CSV files", "*.csv")])
   if not file_path: return


   # --- 2. Directory Preparation ---
   original_dir = os.path.dirname(file_path)
   base_name = os.path.basename(file_path).replace(".csv", "")
   timestamp = datetime.now().strftime("%Y%m%d_%H%M")
   output_folder = os.path.join(original_dir, f"{timestamp}_{base_name}_Analysis")
   figure_folder = os.path.join(output_folder, "Figures")
   for folder in [output_folder, figure_folder]:
       if not os.path.exists(folder): os.makedirs(folder)


   try:
       # --- 3. Data Reading (Handling ParserError with multi-column support) ---
       # Read the file forcing a large number of columns to accommodate Axion stacking
       df_raw = pd.read_csv(file_path, header=None, names=range(100), engine='python')


       # Metric mapping to precise CSV keys (adjusted for actual file units)
       metrics_map = {
           'Treatment': 'Treatment/ID',
           'Beat_Period': 'Beat Period (s)',
           'FPD': 'FPD (ms)',
           'FPDc': 'FPDc (Fridericia ms)',
           'Spike_Amplitude': 'Spike Amplitude (mV)',
           'Spike_Slope': 'Spike Slope (V/s)',
           'CV': 'Conduction Velocity (mm/ms)'
       }


       # Locate indices for Baseline (0) and After (1) phases via 'Measurement' keyword
       well_indices = df_raw[df_raw[0].astype(str).str.strip() == 'Measurement'].index.tolist()
       if len(well_indices) < 2:
           print("[ERROR] Measurement markers for Baseline/After not found in CSV.")
           return


       well_qc_notes = {}


       def extract_full_phase(p_idx, label):
           start_idx = well_indices[p_idx]
           # Extract Well IDs (A1, A2...)
           wells = df_raw.iloc[start_idx, 1:].dropna().values
           df_phase = pd.DataFrame({'Well ID': wells})


           for col, key in metrics_map.items():
               mask = df_raw[0].astype(str).str.strip() == key
               target_rows = df_raw[mask].index.tolist()


               if len(target_rows) > p_idx:
                   vals_raw = df_raw.iloc[target_rows[p_idx], 1:len(wells) + 1].values


                   if col == 'Treatment':
                       # Ensure Treatment is cleanly read as string
                       df_phase[col] = [str(x).strip() for x in vals_raw]
                   else:
                       # Numeric conversion
                       vals = pd.to_numeric(vals_raw, errors='coerce')


                       # --- CV Core QC: Filter Null/Negative/Zero (Requirement 1) ---
                       if col == 'CV':
                           for i, val in enumerate(vals):
                               w = wells[i]
                               if w not in well_qc_notes: well_qc_notes[w] = []


                               # Check for Empty/NaN (implicit in numeric conversion)
                               if pd.isna(val):
                                   well_qc_notes[w].append(f"{label}_CV_Empty")


                               # Check for Negative or Zero values (Requirement 1)
                               elif val <= 0:
                                   well_qc_notes[w].append(f"{label}_CV_Not Positive")
                                   vals[i] = np.nan  # Force to NaN to halt calculation
                       df_phase[col] = vals
               else:
                   df_phase[col] = np.nan
           return df_phase


       # Extract data for both phases
       print("Extracting Baseline data...")
       df_b = extract_full_phase(0, 'Baseline')
       print("Extracting After data...")
       df_a = extract_full_phase(1, 'After')


       # --- 4. Calculate Percentage Changes and Secondary QC ---
       # Initialize results table with IDs and Treatment from Baseline
       results = df_b[['Well ID', 'Treatment']].copy()


       # Calculate Percentage Changes
       for col_name in metrics_map.keys():
           if col_name == 'Treatment': continue


           # Division by zero protection: replace baseline 0s with NaN
           b_val = df_b[col_name].replace(0, np.nan)
           a_val = df_a[col_name]


           chg_col = f'{col_name}_%_Change'
           results[chg_col] = ((a_val - b_val) / b_val) * 100


           # --- CV Change Rate QC (Requirements 2 & 3) ---
           if col_name == 'CV':
               for idx, row in results.iterrows():
                   well = row['Well ID']
                   chg = row[chg_col]
                   if not pd.isna(chg):
                       # Requirement 2: Exclude extreme outliers absolute change > 300%
                       if abs(chg) > 300:
                           if well not in well_qc_notes: well_qc_notes[well] = []
                           well_qc_notes[well].append("Extreme_CV_Change_>300%_Excluded")
                           results.at[idx, chg_col] = np.nan  # Nullify data point
                       # Requirement 3: Flag high fluctuation > 75% for check
                       elif chg > 75:
                           if well not in well_qc_notes: well_qc_notes[well] = []
                           well_qc_notes[well].append("CV_Increase_>75%_Manual_Check_Required")


       # Compile and deduplicate QC notes into a single column
       results['Quality_Control_Notes'] = results['Well ID'].map(
           lambda x: "; ".join(dict.fromkeys(well_qc_notes.get(x, []))))


       # --- 5. Save Results ---
       results.to_csv(os.path.join(output_folder, "1_Individual_Well_Data_and_QC.csv"), index=False,
                      encoding='utf-8-sig')
       chg_cols = [c for c in results.columns if '%_Change' in c]
       summary = results.groupby('Treatment')[chg_cols].agg(['mean', 'std', 'count'])
       summary.to_csv(os.path.join(output_folder, "2_Statistical_Summary.csv"), encoding='utf-8-sig')


       # --- 6. Academic Visualization (Refined Aesthetics v6) ---
       print("Generating harmonized academic charts...")


       # Define a professional, colorblind-friendly palette
       academic_colors = sns.color_palette("colorblind")  # Seaborn's optimized professional palette


       # Setup consistent seaborn style (academic, clean)
       sns.set_theme(style="ticks", font="sans-serif")


       # Ensure Treatment order puts 'Control' first, then sort concentrations numerically
       t_order = results['Treatment'].unique().tolist()
       if 'Control' in t_order:
           t_order.remove('Control')
           t_order = ['Control'] + sorted(t_order)


       # Map each Treatment group to a fixed color for consistency across all plots
       color_mapping = dict(zip(t_order, academic_colors))


       for metric in chg_cols:
           # Filter NaN to avoid seaborn warning and map remaining data
           plot_data = results.dropna(subset=[metric]).copy()
           if not plot_data.empty:
               plt.figure(figsize=(7.5, 5))


               # BAR PLOT: Professional palette, high transparency (alpha=0.75)
               # Capsize added to match academic look
               sns.barplot(data=plot_data, x='Treatment', y=metric, order=t_order, hue='Treatment',
                           legend=False, palette=color_mapping, errorbar='sd', alpha=0.75, capsize=0.1)


               # STRIP PLOT (Points): Darker grey, slightly smaller size, high contrast against bar colors
               sns.stripplot(data=plot_data, x='Treatment', y=metric, order=t_order, color=".25", size=4, jitter=True)


               # Baseline reference line: Very light red, dashed, present but unobtrusive
               plt.axhline(0, color='red', linestyle='--', linewidth=1, alpha=0.3)


               # Title and Label Styling
               plt.title(f"{metric.replace('_', ' ')}", fontsize=14, fontweight='bold', pad=15)
               plt.ylabel("Percentage Change (%)", fontsize=12)
               plt.xlabel("")  # X-axis label removed as treatments define the categories


               # X-axis ticks: 45 degree rotation, right alignment
               plt.xticks(rotation=45, ha='right')


               # Despine (Remove top and right spines)
               sns.despine()


               plt.tight_layout()
               plt.savefig(os.path.join(figure_folder, f"{metric.replace('%', 'pct')}.png"), dpi=300)
               plt.close()


       print(f"\n" + "=" * 50)
       print(f"SUCCESS: Harmonized Analysis v6 Completed.")
       print(f"Directory: {output_folder}")
       print(f"Plots generated with harmonious academic colors.")
       print("=" * 50)


   except Exception as e:
       print(f"[CRITICAL ERROR] {e}")
       import traceback
       traceback.print_exc()




if __name__ == "__main__":
   run_cardiac_analysis_final_v6()
