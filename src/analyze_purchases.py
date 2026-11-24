"""Build provisional monthly KPIs and first-observed purchase cohorts."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd


PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"


def monthly_coverage(transaction_dates):
    dates = pd.to_datetime(transaction_dates, format="%Y-%m-%d").dropna()
    if dates.empty:
        raise ValueError("The transaction export has no dated rows.")

    first, last = dates.min(), dates.max()
    months = pd.period_range(first, last, freq="M", name="month")
    counts = dates.dt.to_period("M").value_counts().reindex(months, fill_value=0)
    coverage = pd.DataFrame({"dated_source_lines": counts, "coverage": "observed"})
    coverage.loc[counts.eq(0), "coverage"] = "no_dated_lines"
    if first.day != 1:
        coverage.loc[months[0], "coverage"] = "partial"
    if not last.is_month_end:
        coverage.loc[months[-1], "coverage"] = "partial"
    return coverage


def summarize(purchases, coverage):
    if purchases.empty or purchases[["invoice_id", "invoice_date"]].isna().any().any():
        raise ValueError("Purchase lines must contain an invoice ID and date.")
    invoice_groups = purchases.groupby("invoice_id", sort=False)
    invoice_fields = ["invoice_date", "country", "customer_id"]
    if invoice_groups[invoice_fields].nunique().gt(1).any().any():
        raise ValueError("A purchase invoice has conflicting dates, countries, or known IDs.")
    # GroupBy.first supplies the identified ID when some lines lack one.
    orders = invoice_groups[invoice_fields].first().reset_index()
    orders["month"] = orders["invoice_date"].dt.to_period("M")
    purchases["month"] = purchases["invoice_date"].dt.to_period("M")

    monthly = coverage.join(
        purchases.groupby("month")["signed_line_value_gbp"].agg(
            purchase_lines="size", gross_sales_gbp="sum"
        )
    )
    monthly = monthly.join(orders.groupby("month").size().rename("purchase_orders"))
    known_orders = orders.dropna(subset=["customer_id"])
    customer_orders = known_orders.groupby(["month", "customer_id"]).size()
    monthly = monthly.join(customer_orders.groupby(level="month").agg(
        identified_customers="size",
        repeat_customers=lambda counts: counts.ge(2).sum(),
    ))
    counts = ["purchase_lines", "purchase_orders", "identified_customers", "repeat_customers"]
    monthly[counts] = monthly[counts].fillna(0).astype(int)
    monthly["gross_sales_gbp"] = monthly["gross_sales_gbp"].fillna(0).round(2)
    monthly["average_order_value_gbp"] = (
        monthly["gross_sales_gbp"] / monthly["purchase_orders"].replace(0, float("nan"))
    ).round(2)
    monthly["repeat_customer_rate"] = (
        monthly["repeat_customers"] / monthly["identified_customers"].replace(0, float("nan"))
    )
    return monthly, orders, known_orders


def cohort_retention(known_orders, coverage):
    activity = known_orders[["customer_id", "month"]].drop_duplicates().copy()
    activity["cohort_month"] = activity.groupby("customer_id")["month"].transform("min")
    sizes = activity.loc[activity["month"].eq(activity["cohort_month"])].groupby(
        "cohort_month"
    ).size()
    active_counts = activity.groupby(["cohort_month", "month"]).size()

    grid = pd.MultiIndex.from_product(
        [sizes.index, coverage.index], names=["cohort_month", "month"]
    ).to_frame(index=False)
    grid = grid.loc[grid["month"].ge(grid["cohort_month"])].copy()
    grid["month_offset"] = grid["month"].astype("int64") - grid["cohort_month"].astype("int64")
    grid["observed_cohort_size"] = grid["cohort_month"].map(sizes)
    grid["coverage"] = grid["month"].map(coverage["coverage"])
    grid["cohort_coverage"] = grid["cohort_month"].map(coverage["coverage"])
    comparable = grid["coverage"].eq("observed") & grid["cohort_coverage"].eq("observed")
    grid = grid.join(active_counts.rename("active_customers"), on=["cohort_month", "month"])
    grid["active_customers"] = grid["active_customers"].fillna(0).where(comparable).astype("Int64")
    grid["retention_rate"] = grid["active_customers"] / grid["observed_cohort_size"]
    return grid


def main():
    date_column = pd.read_csv(PROCESSED / "transactions.csv", usecols=["invoice_date"])
    coverage = monthly_coverage(date_column["invoice_date"])
    purchases = pd.read_csv(
        PROCESSED / "purchase_lines.csv",
        usecols=["invoice_id", "invoice_date", "country", "customer_id", "signed_line_value_gbp"],
        dtype={"invoice_id": "string", "country": "string", "customer_id": "string"},
        keep_default_na=False,
        na_values=[""],
        parse_dates=["invoice_date"],
    )
    monthly, orders, known_orders = summarize(purchases, coverage)
    retention = cohort_retention(known_orders, coverage)
    with TemporaryDirectory(dir=PROCESSED) as directory:
        staging = Path(directory)
        monthly.to_csv(staging / "monthly_purchase_kpis.csv")
        retention.to_csv(staging / "cohort_retention.csv", index=False)
        for name in ("monthly_purchase_kpis.csv", "cohort_retention.csv"):
            (staging / name).replace(PROCESSED / name)

    customer_orders = known_orders.groupby("customer_id").size()
    print(f"Provisional gross sales: GBP {purchases['signed_line_value_gbp'].sum():,.2f}")
    print(f"Purchase invoices: {len(orders):,}")
    print(f"Identified customers: {len(customer_orders):,}")
    print(f"Identified customers with two or more orders: {customer_orders.ge(2).sum():,}")
    print(f"Wrote {len(monthly)} monthly KPI rows and {len(retention)} cohort-month rows.")


if __name__ == "__main__":
    main()
