# Cardiac Metrics Analysis Tool

## Overview

This project provides automated analysis workflows for exported cardiac metrics `.csv` files. It is designed to reduce manual processing, standardize percentage-change calculations, apply quality control (QC) rules to conduction velocity (CV) data, and generate both data summary tables and plots.

In the current version, the tool supports two analysis modes.

### 1. Single-file analysis
This mode:
1. Processes one cardiac metrics CSV file containing baseline and post-treatment sections
2. Calculates percentage change for each metric relative to baseline
3. Applies QC to CV values
4. Generates original and control-adjusted outputs

### 2. Multi-file analysis
This mode:
1. Processes multiple CSV files across different time points (for example `D1`, `D3`, `D7`)
2. Performs the same percentage-change calculations and CV QC
3. Combines results across days
4. Generates comparison plots and summary statistics across time points

The cardiac metrics currently supported by this tool include:

- Beat Period
- FPD
- FPDc
- Spike Amplitude
- Spike Slope
- Conduction Velocity (CV)

## Main Functions

- Automatic extraction of baseline and post-treatment measurements from exported CSV files
- Calculation of percentage change relative to baseline
- Automated QC for conduction velocity (CV) data
- Optional normalization to control group mean
- Export of cleaned and processed datasets
- Export of summary statistics
- Automatic generation of plots in both raster and vector formats (`PNG`, `SVG`, `EPS`)

For each file, the script identifies the relevant sections and extracts:

- well IDs
- treatment labels
- baseline values
- post-treatment values

For the multi-file workflow, filenames are also used to infer day labels such as `D1`, `D3`, and `D7`. If no day tag is detected, the script falls back to the filename stem. 

---

## Requirements

This project was written in Python and uses the following packages:

- `pandas`
- `numpy`
- `matplotlib`
- `seaborn`

It also uses some built-in Python modules, including:

- `tkinter`
- `os`
- `re`
- `datetime`
- `warnings`
- `logging`

## How to Install Packages

Before running the script, make sure Python is installed on your computer.

Then install the required external packages with:

```bash
pip install pandas numpy matplotlib seaborn
```

If your system uses pip3, run:
```bash
pip3 install pandas numpy matplotlib seaborn
```
## How to run
### Step 1: Download the script

Clone this repository or download the Python script file(s) to your computer.

### Step 2: Open a terminal

Navigate to the folder containing the script.

Example:
```bash
cd path/to/your/project
```
### Step 3: Run the script

Run the Python file with:
```bash
python singlefile_analysis.py
```
```bash
python multifiles_analysis.py
```
or, if needed:
```bash
python3 singlefile_analysis.py
```
```bash
python3 multifiles_analysis.py
```
### Step 4: Select input file(s)

After running the script, a file dialog window will open.

For single-file analysis, select one cardiac metrics CSV file
For multi-file analysis, select multiple CSV files across time points (for example D1, D3, D7)
The multi-file workflow uses filenames to detect day labels such as D1, D3, and D7.

### Step 5: Check output folder

After the analysis is complete, the script will automatically generate an output folder in the same directory as the input file(s). This folder contains processed data files, summary tables, and plots.
