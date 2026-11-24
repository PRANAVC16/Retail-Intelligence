"""Report data quality from the original UCI Online Retail II workbook."""

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_WORKBOOK = (
    Path(__file__).resolve().parents[1] / "data" / "raw" / "online_retail_II.xlsx"
)
REQUIRED_COLUMNS = {
    "Invoice", "StockCode", "Description", "Quantity",
    "InvoiceDate", "Price", "Customer ID", "Country",
}


def missing_values(column):
    """Count Excel blanks and cells containing only whitespace as missing."""
    return column.astype("string").fillna("").str.strip().eq("")


def show_count(label, count, total):
    percentage = f"{count / total:.2%}" if total else "n/a"
    print(f"  {label}: {count:,} ({percentage})")


def inspect_rows(label, rows):
    """Calculate flags on temporary series while keeping original rows intact."""
    total = len(rows)
    print(f"\n{label} | {total:,} rows")
    print("Missing cells by column")
    for column in rows.columns:
        show_count(column, int(missing_values(rows[column]).sum()), total)

    invoice = rows["Invoice"].astype("string").str.strip().str.upper()
    cancelled = invoice.str.startswith("C", na=False)
    quantity = pd.to_numeric(rows["Quantity"], errors="coerce")
    price = pd.to_numeric(rows["Price"], errors="coerce")
    dates = pd.to_datetime(rows["InvoiceDate"], errors="coerce")

    print("Quality flags (a row can trigger several flags)")
    show_count("Cancellation prefix C", int(cancelled.sum()), total)
    show_count("Negative quantity", int(quantity.lt(0).sum()), total)
    show_count("Negative quantity without C prefix",
               int((quantity.lt(0) & ~cancelled).sum()), total)
    show_count("Zero quantity", int(quantity.eq(0).sum()), total)
    show_count("Non-positive price", int(price.le(0).sum()), total)
    for column, parsed in [("Quantity", quantity), ("Price", price), ("InvoiceDate", dates)]:
        invalid = parsed.isna() & ~missing_values(rows[column])
        show_count(f"Nonblank {column} values that could not be parsed",
                   int(invalid.sum()), total)
    show_count("Rows in exact duplicate groups",
               int(rows.duplicated(keep=False).sum()), total)
    show_count("Exact duplicate rows beyond first occurrence",
               int(rows.duplicated().sum()), total)

    valid_dates = dates.dropna()
    print("Observation coverage")
    if valid_dates.empty:
        print("  No valid invoice dates.")
        return
    first, last = valid_dates.min(), valid_dates.max()
    print(f"  First timestamp: {first}")
    print(f"  Last timestamp:  {last}")
    if first.day != 1:
        print(f"  Opening month {first:%Y-%m} starts after day 1.")
    if not last.is_month_end:
        print(f"  Closing month {last:%Y-%m} ends before its final day.")
    monthly = valid_dates.dt.to_period("M").value_counts()
    for month in pd.period_range(first, last, freq="M"):
        print(f"  {month}: {monthly.get(month, 0):,} dated rows")
    print("  Dates show observed activity. Monthly counts cannot establish full capture.")


def read_worksheets(path, *, show_names=False):
    """Yield each worksheet with the original column names and cell values."""
    with pd.ExcelFile(path, engine="openpyxl") as workbook:
        if show_names:
            print(f"Worksheets: {', '.join(workbook.sheet_names)}")
        for name in workbook.sheet_names:
            # Read all values, preserving literal strings such as 'NA'.
            rows = workbook.parse(name, dtype=object, keep_default_na=False)
            missing_columns = REQUIRED_COLUMNS.difference(rows.columns)
            if missing_columns:
                names = ", ".join(sorted(missing_columns))
                raise ValueError(f"Worksheet {name!r} lacks expected columns: {names}")
            yield name, rows


def inspect_workbook(path):
    print(f"Workbook: {path.resolve()}")
    sheets = []
    for name, rows in read_worksheets(path, show_names=True):
        sheets.append(rows)
        inspect_rows(name, rows)
    # A combined view can find matching lines across worksheet boundaries.
    inspect_rows("All worksheets", pd.concat(sheets, ignore_index=True))
    print("\nInspection complete. The workbook was opened read-only and left unchanged.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", nargs="?", type=Path, default=DEFAULT_WORKBOOK)
    args = parser.parse_args()
    if not args.workbook.is_file():
        parser.error(f"Workbook not found: {args.workbook}. Download and extract it from UCI.")
    try:
        inspect_workbook(args.workbook)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Inspection failed: {error}\n")


if __name__ == "__main__":
    main()
