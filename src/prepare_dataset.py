"""Prepare traceable transaction and provisional purchase CSVs."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from inspect_dataset import DEFAULT_WORKBOOK, read_worksheets, show_count


OUTPUT_DIRECTORY = DEFAULT_WORKBOOK.parents[1] / "processed"
COLUMNS = {
    "Invoice": "invoice_id",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_timestamp",
    "Price": "unit_price_gbp",
    "Customer ID": "customer_id",
    "Country": "country",
}


def prepare_transactions(workbook):
    sheets = []
    for name, rows in read_worksheets(workbook):
        rows = rows[list(COLUMNS)].copy()
        rows["source_sheet"] = name
        rows["source_row"] = rows.index + 2
        sheets.append(rows)
    transactions = pd.concat(sheets, ignore_index=True)
    raw_columns = list(COLUMNS)
    transactions["exact_match_candidate"] = transactions.duplicated(raw_columns, keep=False)

    # Match copies across sheets one by one. Extra copies within a sheet remain visible.
    occurrence = transactions.groupby(["source_sheet", *raw_columns], sort=False,
                                      dropna=False).cumcount()
    transactions["cross_sheet_overlap"] = (
        transactions.assign(occurrence=occurrence).duplicated([*raw_columns, "occurrence"])
    )
    transactions = transactions.rename(columns=COLUMNS)
    for column in ("invoice_id", "stock_code", "description", "customer_id", "country"):
        values = transactions[column].astype("string").str.strip()
        transactions[column] = values.mask(values.eq(""))
    for column in ("invoice_id", "stock_code"):
        transactions[column] = transactions[column].str.upper()
    for column in ("quantity", "unit_price_gbp"):
        values = pd.to_numeric(transactions[column], errors="coerce")
        transactions[column] = values.replace([float("inf"), float("-inf")], float("nan"))
    timestamp = pd.to_datetime(transactions["invoice_timestamp"], errors="coerce")
    transactions["invoice_timestamp"] = timestamp
    transactions["invoice_date"] = timestamp.dt.strftime("%Y-%m-%d")
    transactions["invoice_month"] = timestamp.dt.strftime("%Y-%m")
    transactions["signed_line_value_gbp"] = (
        transactions["quantity"] * transactions["unit_price_gbp"]
    )

    invoice = transactions["invoice_id"]
    quantity = transactions["quantity"]
    price = transactions["unit_price_gbp"]
    transactions["missing_customer_id"] = transactions["customer_id"].isna()
    transactions["cancellation_prefix"] = invoice.str.startswith("C", na=False)
    transactions["negative_quantity"] = quantity.lt(0)
    transactions["non_positive_price"] = price.le(0)
    transactions["standard_stock_code"] = transactions["stock_code"].str.fullmatch(
        r"[0-9]{5}[A-Z]*", na=False
    )
    transactions["purchase_candidate"] = (
        invoice.str.fullmatch(r"[0-9]{6}", na=False)
        & timestamp.notna()
        & quantity.gt(0)
        & price.gt(0)
        & transactions["standard_stock_code"]
        & ~transactions["cross_sheet_overlap"]
    )
    return transactions


def export_tables(transactions, output):
    output.mkdir(parents=True, exist_ok=True)
    purchases = transactions.loc[transactions["purchase_candidate"]]
    with TemporaryDirectory(dir=output) as directory:
        staging = Path(directory)
        transactions.to_csv(staging / "transactions.csv", index=False, chunksize=50_000)
        purchases.to_csv(staging / "purchase_lines.csv", index=False, chunksize=50_000)
        for name in ("transactions.csv", "purchase_lines.csv"):
            (staging / name).replace(output / name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", nargs="?", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIRECTORY)
    args = parser.parse_args()
    if not args.workbook.is_file():
        parser.error(f"Workbook not found: {args.workbook}")
    try:
        transactions = prepare_transactions(args.workbook)
        export_tables(transactions, args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Preparation failed: {error}\n")

    total = len(transactions)
    print(f"Transaction rows retained: {total:,}")
    for column in ("missing_customer_id", "cancellation_prefix", "exact_match_candidate",
                   "cross_sheet_overlap", "purchase_candidate"):
        show_count(column.replace("_", " ").capitalize(), int(transactions[column].sum()), total)
    print(f"CSV files written to {args.output.resolve()}")


if __name__ == "__main__":
    main()
