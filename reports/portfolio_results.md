# Retail retention and revenue results

## Revenue and repeat purchase

The prepared purchase data contains **£19,699,784.97 in provisional gross sales** and **39,516 purchase invoices**. Across the observed window, **4,234 of 5,852 identified customers (72.35%)** bought at least twice. November 2011 had the highest monthly gross sales at **£1,457,742.24**. December 2011 is partial. The [purchase analysis](purchase_analysis.md) describes monthly totals and retention cohorts.

The reconciliation linked **3,132 cancellation lines** worth **£143,628.67**, giving **£19,556,156.30 after matched reversals**. A link requires one unique original purchase and one unique cancellation with the same known customer, stock code, country, unit price, and absolute quantity. The purchase must have an earlier calendar date. The reversal is attributed to the cancellation month. **16,032 eligible cancellation lines remain unmatched**. The rule can miss same-day, partial, ambiguous, and anonymous reversals. Both gross and net figures are provisional.

`monthly_revenue_reconciliation.csv` summarizes the reconciliation by month. `monthly_country_revenue.csv` supplies the country breakdown, and `matched_reversals.csv` contains the linked invoice pairs.

## Customer segments as of November 30, 2011

Recency uses the last observed purchase. Frequency and gross spend use the latest 180 calendar days through the cutoff. The high-spend threshold is the 75th percentile among customers with a purchase in that window, **£1,240.10**. `customer_segments.csv` has one row per eligible identified customer.

| Segment | Rule | Customers |
| --- | --- | ---: |
| Lapsed | No purchase in the 180-day window | 2,380 |
| Other active | Remaining customers with a purchase in the window | 1,668 |
| High-value repeat | Recency at most 90 days, at least two orders, and spend at or above the threshold | 791 |
| At risk | Last purchase 91–179 days before the cutoff | 599 |
| Recent first observed buyer | One order and first observed purchase at most 90 days before the cutoff | 386 |

## 90-day repeat purchase

Logistic regression uses days since last purchase, 180-day order count and spend, and days since first observed purchase. Each snapshot includes only customers with a purchase through the cutoff and labels purchases from day 1 through day 90. Both models trained on 10,804 snapshots across June, September, and December 2010. The validation cutoff was April 30, 2011. The held-out test cutoff was August 31, 2011. Training outcomes end before validation begins, and validation outcomes end before the test cutoff.

| Held-out metric | Recency alone | Full logistic regression |
| --- | ---: | ---: |
| Average precision | 67.11% | 74.64% |
| Precision in top-scored 10% | 75.91% | 90.25% |
| Brier score, lower is better | 0.213 | 0.188 |

Among the 5,224 test customers, 42.80% purchased within 90 days. Precision measures the observed repeat share among the highest-scored customers. Average precision summarizes ranking quality over thresholds. Brier score measures mean squared probability error. The evaluation measures predictive ranking on one historical test period. Measuring the effect of outreach would require a separate experiment. `model_evaluation.csv` includes validation and test metrics for both models.

## Reproduce the results

`src/complete_analysis.py` links eligible reversals, groups purchase lines into orders, builds customer snapshots, and compares the two logistic regression pipelines. `powerbi/build_report.py` turns aggregate outputs into an editable Power BI project. Follow the [Windows instructions](../README.md#run-on-windows).
