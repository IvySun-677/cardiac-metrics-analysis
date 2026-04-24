import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import tkinter as tk
from tkinter import filedialog
import os
from datetime import datetime


def run_cardiac_analysis_v21_Full_QC():
    """
    Performs automated cardiac metric analysis including data extraction,
    quality control (QC) for conduction velocity, and statistical normalization.
    """
    # --- 1. Initialization and File Selection ---
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    # Prompt user for file selection
    file_path = filedialog.askopenfilename(
        title="Select Cardiac Metrics CSV File",
        filetypes=[("CSV files", "*.csv")]
    )
    if not file_path:
        return

    orig_filename = os.path.basename(file_path)
    base_name = os.path.splitext(orig_filename)[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    # Define output directory structure
    output_dir = os.path.join(os.path.dirname(file_path), f"{base_name}_{timestamp}_v21_Final")
    folders = {
        "png": os.path.join(output_dir, "1_PNG"),
        "vector": os.path.join(output_dir, "2_Vector"),
        "data": output_dir
    }

    for f in folders.values():
        os.makedirs(f, exist_ok=True)

    try:
        # --- 2. Data Parsing and Initial Quality Control (QC) ---
        # Load raw data from multi-segment CSV format
        df_raw = pd.read_csv(file_path, header=None, names=range(100), engine='python')

        metrics_map = {
            'Treatment': 'Treatment/ID',
            'Beat_Period': 'Beat Period (s)',
            'FPD': 'FPD (ms)',
            'FPDc': 'FPDc (Fridericia ms)',
            'Spike_Amplitude': 'Spike Amplitude (mV)',
            'Spike_Slope': 'Spike Slope (V/s)',
            'CV': 'Conduction Velocity (mm/ms)'
        }

        # Locate indices for Baseline and Post-Treatment measurements
        well_indices = df_raw[df_raw[0].astype(str).str.strip() == 'Measurement'].index.tolist()
        cv_qc_notes = {}

        def extract_phase(p_idx, label):
            """Extracts specific experimental phases (Baseline/After) from raw data."""
            start_idx = well_indices[p_idx]
            wells = df_raw.iloc[start_idx, 1:].dropna().values
            df_p = pd.DataFrame({'Well ID': wells})

            for col, key in metrics_map.items():
                mask = df_raw[0].astype(str).str.strip() == key
                target_rows = df_raw[mask].index.tolist()

                if len(target_rows) > p_idx:
                    raw_data = df_raw.iloc[target_rows[p_idx], 1:len(wells) + 1].values
                    if col == 'Treatment':
                        df_p[col] = [str(x).strip() for x in raw_data]
                    else:
                        vals = pd.to_numeric(raw_data, errors='coerce')

                        # Data validation: identify missing or invalid numerical entries
                        if col == 'CV':
                            for i, v in enumerate(vals):
                                w = wells[i]
                                if pd.isna(v):
                                    cv_qc_notes[w] = cv_qc_notes.get(w, []) + [f"{label}_CV_Missing"]
                                elif v <= 0:
                                    cv_qc_notes[w] = cv_qc_notes.get(w, []) + [f"{label}_CV_Invalid_Value"]
                        df_p[col] = vals
            return df_p

        df_b = extract_phase(0, "Baseline")
        df_a = extract_phase(1, "After")

        # --- 3. Calculation of Percentage Changes and Advanced QC ---
        results = df_b[['Well ID', 'Treatment']].copy()
        chg_cols = []

        for col in metrics_map.keys():
            if col == 'Treatment': continue
            b_val = df_b[col].replace(0, np.nan)
            chg_col = f'{col}_%_Change'
            results[chg_col] = ((df_a[col] - b_val) / b_val) * 100
            chg_cols.append(chg_col)

            # CV-Specific QC Logic:
            # - Changes > 75% are flagged for manual review but retained.
            # - Changes > 300% are flagged as extreme outliers for exclusion.
            if col == 'CV':
                for i, row in results.iterrows():
                    val = row[chg_col]
                    w = row['Well ID']
                    if not pd.isna(val):
                        if val > 75:
                            cv_qc_notes[w] = cv_qc_notes.get(w, []) + ["CV_Increase_>75%_Manual_Check_Required"]
                        if abs(val) > 300:
                            cv_qc_notes[w] = cv_qc_notes.get(w, []) + ["Extreme_CV_Change_>300%"]

        # Map QC notes back to the main results dataframe
        results['CV_QC_Notes'] = results['Well ID'].map(lambda x: "; ".join(dict.fromkeys(cv_qc_notes.get(x, []))))

        # --- 4. Statistical Adjustment (Normalization to Control) ---
        clean_results = results.copy()
        # Exclude extreme CV outliers (>300%) from statistical calculations
        for i, row in clean_results.iterrows():
            if "Extreme_CV_Change_>300%" in str(row['CV_QC_Notes']):
                clean_results.loc[i, 'CV_%_Change'] = np.nan

        # Calculate mean of 'Control' group for normalization
        control_means = clean_results[clean_results['Treatment'] == 'Control'][chg_cols].mean()

        # Adjust results by subtracting control mean (Baseline Correction)
        results_adj = clean_results[clean_results['Treatment'] != 'Control'].copy()
        for col in chg_cols:
            results_adj[col] = results_adj[col] - control_means[col]

        # Generate aggregated summary table
        combined_summary = pd.concat([
            results.groupby('Treatment')[chg_cols].agg(['mean', 'std', 'count']),
            results_adj.groupby('Treatment')[chg_cols].agg(['mean', 'std', 'count'])
        ], axis=1)

        # --- 5. Exporting Data ---
        def save_final(df, suffix):
            """Exports dataframes to CSV with standardized headers."""
            fpath = os.path.join(output_dir, f"{base_name}_{suffix}.csv")
            with open(fpath, 'w', encoding='utf-8-sig', newline='') as f:
                f.write(f"SOURCE: {orig_filename} | QC_LOG: Missing/Invalid/Extreme_>300%/Manual_Check_>75%\n")
                df.to_csv(f, index=('Summary' in suffix))

        save_final(combined_summary, "Summary_Statistics")
        save_final(results, "Detailed_Original_with_QC")
        save_final(results_adj, "Detailed_Adjusted_to_Control")

        # --- 6. Data Visualization ---
        sns.set_theme(style="ticks", font="sans-serif")
        all_t = sorted(results['Treatment'].unique().tolist())
        if 'Control' in all_t:
            all_t.remove('Control')
            all_t = ['Control'] + all_t

        cmap = dict(zip(all_t, sns.color_palette("colorblind", len(all_t))))

        def do_plots(df, is_adj):
            """Generates bar plots with individual data points overlayed."""
            order = [t for t in all_t if t in df['Treatment'].unique()]
            tag = "ADJUSTED" if is_adj else "ORIGINAL"

            for m in chg_cols:
                data_plot = df.dropna(subset=[m]).copy()
                if data_plot.empty: continue

                plt.figure(figsize=(8, 5))
                # Create bar plot with error bars (SD)
                sns.barplot(data=data_plot, x='Treatment', y=m, order=order, hue='Treatment', palette=cmap,
                            errorbar='sd', alpha=0.7, capsize=0.1)
                # Overlay individual data points
                sns.stripplot(data=data_plot, x='Treatment', y=m, order=order, color=".25", size=4, jitter=True)

                plt.axhline(0, color='red', lw=1, ls='--')
                plt.title(f"{m.replace('_', ' ')} ({tag})\nSource: {base_name}", fontsize=10)
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()

                # Save as Raster (PNG) and Vector (SVG, EPS)
                fn = f"{base_name}_{m}_{tag}"
                plt.savefig(os.path.join(folders["png"], f"{fn}.png"), dpi=300)
                plt.savefig(os.path.join(folders["vector"], f"{fn}.svg"), format='svg', transparent=True)

                plt.clf()
                # Secondary save for EPS format (for high-end publication use)
                sns.barplot(data=data_plot, x='Treatment', y=m, order=order, hue='Treatment', palette=cmap,
                            errorbar='sd', alpha=1.0, capsize=0.1)
                sns.stripplot(data=data_plot, x='Treatment', y=m, order=order, color=".25", size=4, jitter=True)
                plt.axhline(0, color='red', lw=1)
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                plt.savefig(os.path.join(folders["vector"], f"{fn}.eps"), format='eps')
                plt.close()

        do_plots(results, False)
        do_plots(results_adj, True)

        print(f"\n[Analysis Complete]")
        print(f"Notes: CV > 75% flagged for manual review. Extreme outliers (> 300%) excluded from summary statistics.")
        print(f"Output Directory: {output_dir}")

    except Exception as e:
        print(f"Critical Error during analysis: {e}")


if __name__ == "__main__":
    run_cardiac_analysis_v21_Full_QC()
