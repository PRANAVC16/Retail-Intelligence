# Retail Customer Retention & Revenue Intelligence

A project using Python for data preparation, statistical analysis, and machine learning, with Power BI Desktop for reporting. The [portfolio report](reports/portfolio_results.md) presents measured revenue, customer segments, and model evaluation. The [Power BI project](powerbi/Retail.pbip) visualizes the results.

## Business questions

- How do recorded sales, cancellations, and net revenue change by month and country?
- What share of identified customers buy again, and how does retention vary by first observed purchase month?
- Which customers are recent, frequent, or high-spending, and which previously active customers have lapsed?
- At a given date, which identified customers are likely to make another qualifying purchase in the next 90 days?

## Data source and attribution

Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning Repository. [DOI 10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D). Licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

UCI describes transaction data from a UK-based online retailer with prices in pounds sterling and a published observation window of 1 December 2009 through 9 December 2011. Treat December 2011 as partial and use the inspection output to verify actual timestamps and monthly row coverage. [UCI dataset page](https://archive.ics.uci.edu/dataset/502/online%2Bretail%2Bii)

## Workflow

| Location | Purpose |
| --- | --- |
| `data/raw/` | Store the original workbook locally and keep it intact. |
| `src/` | Run reusable Python scripts, starting with the raw-data inspection. |
| `notebooks/` | Explore data, evaluate statistical questions, and prototype models. |
| `data/processed/` | Store future documented tables for analysis and Power BI imports. |
| `reports/` | Keep the [project brief](reports/project_brief.md) and reviewed findings. |
| `powerbi/` | Keep [dashboard and data model documentation](powerbi/README.md). |

Inspect the source first. Use the findings to define and document cleaning rules before producing analysis tables. Build the KPI, segmentation, and cohort views from those tables. Evaluate the prediction task separately with chronological validation.

## Run on Windows

If the virtual environment and workbook are already set up, start at step 4. To recreate the environment using the project-local runtime, use `.\.python\python.exe` in place of `py -3.12` in step 2. On a fresh checkout, follow all steps.

1. If needed, install 64-bit Python 3.12. Open PowerShell in the project folder, then check available Python installations.

   ```powershell
   py -0p
   ```

   If the launcher is unavailable but `python --version` reports Python 3.12, use `python` in place of `py -3.12` below. If both commands fail or open the Microsoft Store, install Python and reopen PowerShell. [Python downloads](https://www.python.org/downloads/windows/)

2. Create a project virtual environment and install dependencies. These commands call the environment's Python directly, so PowerShell activation is unnecessary.

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. If `data/raw/online_retail_II.xlsx` is missing, download the dataset from UCI, extract the ZIP, and place the original workbook at that path. Leave both worksheets and headers intact. [UCI download page](https://archive.ics.uci.edu/dataset/502/online%2Bretail%2Bii)

4. Run the inspection. Add a quoted workbook path after the script name if your file is elsewhere.

   ```powershell
   .\.venv\Scripts\python.exe .\src\inspect_dataset.py
   ```

   To display the output and save a local copy, use:

   ```powershell
   .\.venv\Scripts\python.exe .\src\inspect_dataset.py | Tee-Object -FilePath .\reports\raw-inspection.local.txt
   ```

5. Build the analysis tables.

   ```powershell
   .\.venv\Scripts\python.exe .\src\prepare_dataset.py
   ```

   The script writes `transactions.csv` and `purchase_lines.csv` to `data/processed/`. See the [preparation rules](reports/data_preparation.md) for the column meanings and decisions to review before calculating KPIs.

6. Generate the monthly purchase KPIs and cohort retention tables.

   ```powershell
   .\.venv\Scripts\python.exe .\src\analyze_purchases.py
   ```

7. Generate revenue reconciliation, customer segments, and the 90-day model evaluation. Then build the Power BI project.

   ```powershell
   .\.venv\Scripts\python.exe .\src\complete_analysis.py
   .\.venv\Scripts\python.exe .\powerbi\build_report.py
   ```

8. Open [Retail.pbip](powerbi/Retail.pbip) in Power BI Desktop and refresh the model. See the [Power BI guide](powerbi/README.md) for report pages and refresh steps. For further exploration, launch JupyterLab and create notebooks in `notebooks/`.

   ```powershell
   .\.venv\Scripts\python.exe -m jupyterlab
   ```

## How the script works

1. `main()` locates the workbook and explains how to proceed if the file is missing.
2. `inspect_workbook()` reads each worksheet into a pandas DataFrame, an in-memory table, and checks the original Excel headers. It also checks the combined table so it can catch matching rows on different sheets.
3. `inspect_rows()` counts blanks, including missing customer IDs. It flags cancellation invoices using the documented `C` prefix and reports negative quantities separately. It also flags non-positive prices and values it cannot interpret as numbers or dates. Percentages use the number of rows in that worksheet or combined table.
4. The duplicate check compares all source columns and counts both rows in a matching group and extra copies after the first row. Matching invoice numbers alone are normal on orders containing several items. Exact matches are candidates for review.
5. The date check prints the first and last timestamps and monthly row counts, including gaps. It flags months where observed timestamps start after the first day or end before the last day. Those timestamps show recorded activity and cannot establish whether the source captured every transaction.

The script only reads the workbook and prints aggregate diagnostics. It does not clean, delete, or overwrite records.
