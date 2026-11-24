"""Build revenue reconciliation, customer segments, and a temporal model evaluation."""

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from analyze_purchases import PROCESSED


ID_TYPES = {column: "string" for column in ("customer_id", "invoice_id", "stock_code")}
FEATURES = ["recency_days", "order_count", "gross_spend_gbp", "tenure_days"]
TRAIN_DATES = ["2010-06-30", "2010-09-30", "2010-12-31"]
VALIDATION_DATE = "2011-04-30"
TEST_DATE = "2011-08-31"
SEGMENT_DATE = "2011-11-30"


def read_table(name, columns):
    return pd.read_csv(
        PROCESSED / name, usecols=columns,
        dtype={column: dtype for column, dtype in ID_TYPES.items() if column in columns},
        keep_default_na=False, na_values=[""], parse_dates=["invoice_date"],
    )


def reconcile_revenue(lines, purchases):
    keys = ["customer_id", "stock_code", "country", "unit_price_gbp", "quantity"]
    eligible = (
        lines["cancellation_prefix"] & lines["negative_quantity"]
        & lines["unit_price_gbp"].gt(0) & ~lines["cross_sheet_overlap"]
    )
    reversals = lines.loc[eligible].copy()
    reversals["quantity"] = -reversals["quantity"]
    # Require an unambiguous one-for-one match and a strictly earlier purchase date.
    known_sales = purchases.dropna(subset=keys)
    known_reversals = reversals.dropna(subset=keys)
    unique_sales = known_sales.loc[~known_sales.duplicated(keys, keep=False)]
    unique_reversals = known_reversals.loc[~known_reversals.duplicated(keys, keep=False)]
    linked = unique_reversals.merge(
        unique_sales[keys + ["invoice_date", "invoice_id"]],
        on=keys, suffixes=("", "_sale"), validate="one_to_one",
    )
    linked = linked.loc[linked["invoice_date"].gt(linked["invoice_date_sale"])]
    monthly = pd.read_csv(PROCESSED / "monthly_purchase_kpis.csv", dtype={"month": "string"})
    linked_month = linked["invoice_date"].dt.strftime("%Y-%m")
    reversal_month = reversals["invoice_date"].dt.strftime("%Y-%m")
    monthly["matched_reversal_gbp"] = (
        monthly["month"].map(-linked.groupby(linked_month)["signed_line_value_gbp"].sum())
        .fillna(0).round(2)
    )
    monthly["matched_reversal_lines"] = (
        monthly["month"].map(linked_month.value_counts()).fillna(0).astype(int)
    )
    monthly["unmatched_cancellation_lines"] = (
        monthly["month"].map(reversal_month.value_counts()).fillna(0).astype(int)
        - monthly["matched_reversal_lines"]
    )
    monthly["provisional_net_gbp"] = (
        monthly["gross_sales_gbp"] - monthly["matched_reversal_gbp"]
    ).round(2)
    return monthly, linked


def customer_snapshot(orders, cutoff):
    history = orders.loc[orders["invoice_date"].le(cutoff)]
    first = history.groupby("customer_id")["invoice_date"].min()
    recent = history.loc[history["invoice_date"].gt(cutoff - timedelta(days=180))]
    features = history.groupby("customer_id")["invoice_date"].max().to_frame("last_purchase")
    features["recency_days"] = (cutoff - features["last_purchase"]).dt.days
    features["tenure_days"] = (cutoff - first).dt.days
    features["order_count"] = recent.groupby("customer_id").size().reindex(features.index, fill_value=0)
    features["gross_spend_gbp"] = (
        recent.groupby("customer_id")["gross_spend_gbp"].sum().reindex(features.index, fill_value=0)
    ).round(2)
    return features.reset_index()


def segment_customers(orders):
    cutoff = pd.Timestamp(SEGMENT_DATE)
    segments = customer_snapshot(orders, cutoff)
    active = segments["order_count"].gt(0)
    high_spend = segments.loc[active, "gross_spend_gbp"].quantile(0.75)
    segments["segment"] = "Other active"
    segments.loc[~active, "segment"] = "Lapsed"
    segments.loc[active & segments["recency_days"].gt(90), "segment"] = "At risk"
    recent = segments["recency_days"].le(90)
    segments.loc[recent & segments["tenure_days"].eq(segments["recency_days"])
                 & segments["order_count"].eq(1), "segment"] = "Recent first observed buyer"
    segments.loc[recent & segments["order_count"].ge(2)
                 & segments["gross_spend_gbp"].ge(high_spend), "segment"] = "High-value repeat"
    segments["as_of_date"] = cutoff
    return segments, high_spend


def evaluate_model(orders, first_date, last_date):
    def label(cutoff_text):
        cutoff = pd.Timestamp(cutoff_text)
        horizon = cutoff + timedelta(days=90)
        if cutoff - timedelta(days=179) < first_date or horizon > last_date:
            raise ValueError(f"Incomplete observation window at {cutoff.date()}")
        features = customer_snapshot(orders, cutoff)
        future = orders["invoice_date"].gt(cutoff) & orders["invoice_date"].le(horizon)
        features["repeat_within_90d"] = features["customer_id"].isin(
            orders.loc[future, "customer_id"]
        )
        return features

    training = pd.concat([label(cutoff) for cutoff in TRAIN_DATES], ignore_index=True)
    target = "repeat_within_90d"
    models = {
        "recency_only": ["recency_days"],
        "logistic_regression": FEATURES,
    }
    evaluation = []
    for model_name, columns in models.items():
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
        model.fit(training[columns], training[target])
        for split, cutoff in [("validation", VALIDATION_DATE), ("test", TEST_DATE)]:
            sample = label(cutoff)
            probability = model.predict_proba(sample[columns])[:, 1]
            ranked = sample.assign(probability=probability).sort_values(
                ["probability", "customer_id"], ascending=[False, True]
            )
            capacity = (len(sample) + 9) // 10
            evaluation.append({
                "model": model_name, "split": split, "cutoff": date.fromisoformat(cutoff),
                "customers": len(sample), "positive_rate": sample[target].mean(),
                "average_precision": average_precision_score(sample[target], probability),
                "precision_at_top_10pct": ranked.head(capacity)[target].mean(),
                "brier_score": brier_score_loss(sample[target], probability),
            })
    return pd.DataFrame(evaluation), len(training)


def main():
    columns = [
        "invoice_id", "invoice_date", "customer_id", "stock_code",
        "country", "unit_price_gbp", "quantity", "signed_line_value_gbp",
    ]
    purchases = read_table("purchase_lines.csv", columns)
    transactions = read_table("transactions.csv", columns + [
        "cancellation_prefix", "negative_quantity", "cross_sheet_overlap",
    ])
    revenue, linked = reconcile_revenue(transactions, purchases)
    country_month = purchases.groupby(
        [purchases["invoice_date"].dt.strftime("%Y-%m").rename("month"), "country"],
        dropna=False,
    ).agg(
        gross_sales_gbp=("signed_line_value_gbp", "sum"),
        purchase_orders=("invoice_id", "nunique"),
    )
    reversal_totals = linked.groupby([
        linked["invoice_date"].dt.strftime("%Y-%m").rename("month"), "country",
    ])["signed_line_value_gbp"].sum()
    # Include months where a country had only a matched reversal.
    country_month = country_month.reindex(country_month.index.union(reversal_totals.index))
    country_month["matched_reversal_gbp"] = -reversal_totals.reindex(
        country_month.index, fill_value=0
    )
    country_month["purchase_orders"] = country_month["purchase_orders"].fillna(0).astype(int)
    country_month["gross_sales_gbp"] = country_month["gross_sales_gbp"].fillna(0)
    country_month["provisional_net_gbp"] = (
        country_month["gross_sales_gbp"] - country_month["matched_reversal_gbp"]
    )
    order_keys = ["invoice_id", "invoice_date", "customer_id"]
    invoice_customers = purchases.groupby("invoice_id")["customer_id"].transform("first")
    identified = purchases.assign(customer_id=invoice_customers).dropna(subset=["customer_id"])
    orders = identified.groupby(order_keys, as_index=False)["signed_line_value_gbp"].sum()
    orders = orders.rename(columns={"signed_line_value_gbp": "gross_spend_gbp"})
    segments, high_spend = segment_customers(orders)
    evaluation, sample_count = evaluate_model(
        orders, transactions["invoice_date"].min(), transactions["invoice_date"].max()
    )
    revenue.to_csv(PROCESSED / "monthly_revenue_reconciliation.csv", index=False)
    country_month.to_csv(PROCESSED / "monthly_country_revenue.csv")
    linked.to_csv(PROCESSED / "matched_reversals.csv", index=False)
    segments.to_csv(PROCESSED / "customer_segments.csv", index=False)
    evaluation.to_csv(PROCESSED / "model_evaluation.csv", index=False)
    print(revenue[["gross_sales_gbp", "matched_reversal_gbp", "matched_reversal_lines",
                   "unmatched_cancellation_lines", "provisional_net_gbp"]].sum().to_string())
    print(f"Active-customer spend cutoff: GBP {high_spend:,.2f}")
    print(segments["segment"].value_counts().to_string())
    print(f"Training snapshots: {sample_count:,}")
    print(evaluation.to_string(index=False))


if __name__ == "__main__":
    main()
