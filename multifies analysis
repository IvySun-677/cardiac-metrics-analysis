import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import tkinter as tk
from tkinter import filedialog
import os
import re
from datetime import datetime
import warnings
import logging


# Suppress system warnings for plot consistency
logging.getLogger('matplotlib.backends.backend_ps').setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*PostScript backend does not support transparency.*")




def run_cardiac_analysis_v32_HardClean():
   """
   Analyzes cardiac metric files (D1, D3, D7) and calculates percentage changes.
   Performs automated Quality Control (QC) to remove invalid or extreme CV data.
   """
   root = tk.Tk()
   root.withdraw()
   root.attributes('-topmost', True)


   # Prompt user to select data files
   file_paths = filedialog.askopenfilenames(
       title="Select Cardiac Metric Files (D1/D3/D7)",
       filetypes=[("CSV files", "*.csv")]
   )
   if not file_paths: return
   file_paths = list(file_paths)


   # Initialize output directory structure
   timestamp = datetime.now().strftime("%Y%m%d_%H%M")
   output_dir = os.path.join(os.path.dirname(file_paths[0]), f"Cardiac_Analysis_Report_{timestamp}")
   sub_dirs = [
       "1_Individual_Full_Data",
       "2_Comparison_Plots_ORIG/PNG", "2_Comparison_Plots_ORIG/Vector_Format",
       "3_Comparison_Plots_ADJ/PNG", "3_Comparison_Plots_ADJ/Vector_Format",
       "4_Master_Data",
       "5_Statistics_Summary"
   ]
   paths = {d: os.path.join(output_dir, d) for d in sub_dirs}
   for p in paths.values(): os.makedirs(p, exist_ok=True)


   all_data_list = []


   for path in file_paths:
       fname = os.path.basename(path)
       day_tag = re.search(r'D\d+', fname, re.IGNORECASE)
       day_label = day_tag.group(0).upper() if day_tag else fname.split('.')[0]


       try:
           # Data extraction mapping
           df_raw = pd.read_csv(path, header=None, names=range(100), engine='python')
           metrics_map = {
               'Treatment': 'Treatment/ID', 'Beat_Period': 'Beat Period (s)', 'FPD': 'FPD (ms)',
               'FPDc': 'FPDc (Fridericia ms)', 'Spike_Amplitude': 'Spike Amplitude (mV)',
               'Spike_Slope': 'Spike Slope (V/s)', 'CV': 'Conduction Velocity (mm/ms)'
           }


           well_indices = df_raw[df_raw[0].astype(str).str.strip() == 'Measurement'].index.tolist()
           if len(well_indices) < 2: continue


           def extract_data(p_idx):
               start = well_indices[p_idx]
               wells = df_raw.iloc[start, 1:].dropna().values
               df = pd.DataFrame({'Well ID': wells})
               for col, key in metrics_map.items():
                   mask = df_raw[0].astype(str).str.strip() == key
                   rows = df_raw[mask].index.tolist()
                   if len(rows) > p_idx:
                       vals = df_raw.iloc[rows[p_idx], 1:len(wells) + 1].values
                       df[col] = [str(x).strip() if col == 'Treatment' else pd.to_numeric(x, errors='coerce') for x in
                                  vals]
               return df


           # Baseline (0) and post-treatment (1) data extraction
           df_b = extract_data(0)
           df_a = extract_data(1)
           res = df_b[['Well ID', 'Treatment']].copy()


           # 1. Calculate percentage changes relative to baseline
           for m in ['Beat_Period', 'FPD', 'FPDc', 'Spike_Amplitude', 'Spike_Slope', 'CV']:
               res[f'{m}_%_Change'] = ((df_a[m] - df_b[m]) / df_b[m].replace(0, np.nan)) * 100


           # 2. Quality Control: Detect and exclude invalid Conduction Velocity (CV) records
           final_notes = []
           for i, row in res.iterrows():
               notes = []
               cv_b = df_b.loc[i, 'CV']
               cv_a = df_a.loc[i, 'CV']
               is_invalid = False


               # Identify empty or non-positive baseline/treatment CV
               if pd.isna(cv_b):
                   notes.append("Baseline_CV_Empty")
                   is_invalid = True
               elif cv_b <= 0:
                   notes.append(f"Baseline_CV_Invalid({cv_b})")
                   is_invalid = True


               if pd.isna(cv_a):
                   notes.append("PostTreatment_CV_Empty")
                   is_invalid = True
               elif cv_a <= 0:
                   notes.append(f"PostTreatment_CV_Invalid/Block({cv_a})")
                   is_invalid = True


               # Exclude invalid data and outliers from analysis
               if is_invalid:
                   res.at[i, 'CV_%_Change'] = np.nan
               else:
                   # Filter extreme outliers (e.g., > 300% change)
                   if abs(row['CV_%_Change']) > 300:
                       notes.append("Excluded_Extreme_CV_Change_>300%")
                       res.at[i, 'CV_%_Change'] = np.nan
                   elif row['CV_%_Change'] > 75:
                       notes.append("Flag_CV_Increase_>75%")


               final_notes.append("; ".join(notes))


           res['QC_Notes'] = final_notes
           res['Day'] = day_label
           res.to_csv(os.path.join(paths["1_Individual_Full_Data"], f"{day_label}_Processed_Data.csv"), index=False,
                      encoding='utf-8-sig')
           all_data_list.append(res)


       except Exception as e:
           print(f"Error processing file {fname}: {e}")


   if not all_data_list: return
   full_df = pd.concat(all_data_list, ignore_index=True)
   full_df['Treatment'] = full_df['Treatment'].str.strip()
   day_order = sorted(full_df['Day'].unique())


   # 3. Control Normalization: Adjust treatment values by subtracting Control group mean per day
   adj_data_list = []
   for day in day_order:
       day_data = full_df[full_df['Day'] == day].copy()
       day_ctrl = day_data[day_data['Treatment'].str.contains('ctrl|control', case=False, na=False)]
       if not day_ctrl.empty:
           ctrl_means = day_ctrl[[c for c in full_df.columns if '%_Change' in c]].mean()
           day_adj = day_data[~day_data['Treatment'].str.contains('ctrl|control', case=False, na=False)].copy()
           for c in ctrl_means.index:
               day_adj[c] = day_adj[c] - ctrl_means[c]
           adj_data_list.append(day_adj)
   adj_df = pd.concat(adj_data_list) if adj_data_list else pd.DataFrame()


   # Visualization Function
   def plot_final(df, png_p, vec_p, title_suffix):
       sns.set_theme(style="whitegrid")
       metrics = [c for c in df.columns if '%_Change' in c]
       treat_order = sorted(df['Treatment'].unique().tolist())
       if 'Control' in treat_order:
           treat_order.remove('Control')
           treat_order = ['Control'] + treat_order


       for m in metrics:
           plot_sub = df.dropna(subset=[m]).copy()
           if plot_sub.empty: continue
           plt.figure(figsize=(12, 7))


           # Bar plot with standard deviation error bars
           sns.barplot(data=plot_sub, x='Treatment', y=m, hue='Day', hue_order=day_order, order=treat_order,
                       palette="viridis", errorbar='sd', capsize=0.05, alpha=0.85)
           # Individual data point overlay
           sns.stripplot(data=plot_sub, x='Treatment', y=m, hue='Day', hue_order=day_order, order=treat_order,
                         palette="viridis", dodge=True, size=4, jitter=True, legend=False)


           plt.axhline(0, color='red', lw=1.2, ls='--')
           plt.title(f"{m.replace('_', ' ')} - {title_suffix}", fontsize=14)
           plt.xticks(rotation=35, ha='right')
           plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left')
           plt.tight_layout()


           # Export in multiple formats
           plt.savefig(os.path.join(png_p, f"Compare_{m}.png"), dpi=300)
           plt.savefig(os.path.join(vec_p, f"Compare_{m}.svg"), format='svg')
           plt.savefig(os.path.join(vec_p, f"Compare_{m}.eps"), format='eps')
           plt.close()


   print("\n[Processing Visualization Reports...]")
   plot_final(full_df, paths["2_Comparison_Plots_ORIG/PNG"], paths["2_Comparison_Plots_ORIG/Vector_Format"],
              "Original")
   if not adj_df.empty:
       plot_final(adj_df, paths["3_Comparison_Plots_ADJ/PNG"], paths["3_Comparison_Plots_ADJ/Vector_Format"],
                  "Control_Adjusted")


   # Generate and export Statistical Summary
   chg_cols = [c for c in full_df.columns if '%_Change' in c]
   summary_stats = full_df.groupby(['Day', 'Treatment'])[chg_cols].agg(['mean', 'std', 'count'])
   summary_stats.to_csv(os.path.join(paths["5_Statistics_Summary"], "Statistical_Summary_Report.csv"),
                        encoding='utf-8-sig')
   full_df.to_csv(os.path.join(paths["4_Master_Data"], "Combined_Raw_Data_Final.csv"), index=False,
                  encoding='utf-8-sig')


   print(f"\n[Analysis Complete] Cleaned data and reports saved to:\n{output_dir}")




if __name__ == "__main__":
   run_cardiac_analysis_v32_HardClean()
