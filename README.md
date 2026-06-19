# OptiKuh EDA Project

This folder is ready to open in VS Code. It contains the raw OptiKuh Excel files, a fast CSV cache, reproducible EDA scripts, generated tables/figures, and a LaTeX Beamer presentation in the same green/white style as the provided OptiKuh material.

The work here is **EDA only**: structure, missingness, distributions, biomarker availability, health/disease-category summaries, and data-quality checks. No predictive model is trained.

## 1. Open the project in VS Code

1. Unzip this folder.
2. Open VS Code.
3. Choose **File > Open Folder**.
4. Select `optikuh_eda_project`.
5. Install VS Code extensions if prompted: **Python**, **Jupyter**, and **LaTeX Workshop**.

## 2. Create the Python environment

Open a VS Code terminal in the project root.

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 3. Run the EDA

The CSV cache is already included, so this is the only command you normally need:

```bash
python src/02_run_eda.py
```

Outputs are saved here:

```text
outputs/tables/
outputs/figures/
outputs/reports/eda_summary.md
presentation/auto_numbers.tex
```

## 4. Rebuild the CSV cache only when needed

The raw workbook is included at:

```text
data/raw/optikuh.xlsx
```

Only run the converter if `data/interim/optikuh.csv` is missing or you want to rebuild it:

```bash
python src/01_convert_xlsx_to_csv.py --input data/raw/optikuh.xlsx --output data/interim/optikuh.csv
```

## 5. Compile the LaTeX presentation

The compiled PDF is already included at:

```text
presentation/optikuh_eda_presentation.pdf
```

To rebuild it from the LaTeX source:

```bash
cd presentation
latexmk -xelatex optikuh_eda_presentation.tex
```

If `latexmk` is not installed, run XeLaTeX twice:

```bash
xelatex optikuh_eda_presentation.tex
xelatex optikuh_eda_presentation.tex
```

## 6. Important files

```text
src/01_convert_xlsx_to_csv.py       Fast Excel-to-CSV converter
src/02_run_eda.py                   Main EDA script
notebooks/01_optikuh_eda.ipynb      Optional notebook walkthrough
outputs/tables/                     CSV summary tables
outputs/figures/                    EDA figures used in the deck
outputs/reports/eda_summary.md      Short written EDA summary
presentation/optikuh_eda_presentation.tex   LaTeX Beamer source
presentation/optikuh_eda_presentation.pdf   Compiled slide deck
presentation/speaker_notes.md       Short speaking notes for tomorrow
references/                         Uploaded OptiKuh PDF sources
```

## 7. What to say in the first minutes of the presentation

Start with: "This part is exploratory data analysis only. The goal is to understand the longitudinal structure, data coverage, missingness, disease labels, and biomarker availability before any modeling decisions."

Then use the slide order:

1. Project context: biomarkers for dairy cow health monitoring.
2. VS Code workflow: raw Excel -> CSV cache -> EDA script -> tables/figures -> LaTeX slides.
3. Dataset structure: daily animal records, animals, farms, and lactation episodes.
4. Health status: explain daily-record counts versus lactation-episode counts.
5. Missingness: biomarkers are sparse because samples were collected on selected days.
6. Disease categories: event columns are sparse, so count rows, animals, and episodes.
7. Takeaway: the dataset is longitudinal and hierarchical; the unit of analysis must be chosen before modeling.

## 8. Main EDA notes

- Main data unit: **daily animal record**.
- Main outcome grouping: **health status per lactation episode**.
- Biomarker values are not daily measurements; high missingness is expected from the sampling design.
- Disease columns are event labels and are mostly blank on normal daily records.
- Farm IDs are anonymized numbers 1-12.
