# Project brief

Use historical UK online retail transactions to measure recorded revenue and repeat purchase behavior, identify actionable customer groups, and evaluate whether a 90-day repeat-purchase score adds value. This brief records the original proposed definitions. See the [portfolio results](portfolio_results.md) for the implemented measures and model evaluation.

## Proposed KPIs

A qualifying purchase line has a valid invoice and date, no cancellation prefix, and positive quantity and price. Review adjustment and non-merchandise stock codes before finalizing that rule. Count distinct purchase invoices as orders after checking that each invoice maps consistently to one order.

| KPI | Proposed definition |
| --- | --- |
| Gross sales | Sum of quantity × unit price for qualifying purchase lines, in GBP. |
| Cancellation and return value | Absolute value of validated reversal lines using signed quantity × price. Review prefix and quantity disagreements before counting them, and count each reversal once. |
| Net recorded revenue | Gross sales minus validated reversal value, credited to the reversal date. Report unresolved adjustments separately. |
| Average order value | Gross sales divided by distinct qualifying purchase invoices. |
| Active identified customers | Distinct known customer IDs with a qualifying purchase in the selected period. |
| Repeat customer rate | Identified customers with at least two qualifying invoices in the period divided by identified customers with at least one in the same period. |

Include qualifying anonymous lines in sales and order KPIs. Exclude unidentified customers from customer-level denominators and report the missing-ID share by period to show how much activity those analyses cover. Show undefined ratios as blank when the denominator is zero.

## Customer segmentation

Use RFM (recency, frequency, monetary value) at a fixed reporting date and over a documented lookback. Calculate recency as days since the latest qualifying purchase, frequency as distinct qualifying invoices, and monetary value as qualifying gross spend. Use known customer IDs and only transactions available through the reporting date. Inspect distributions before setting cutoffs. Candidate groups include recent first-time buyers, frequent high-spend buyers, and previously frequent buyers with long gaps since their last purchase.

## Cohort retention

Group identified customers by calendar month of first observed qualifying purchase. For each cohort and month offset, divide the number of cohort members who bought in that month by the original cohort size. Month zero is the acquisition baseline. Show a zero for a fully observed month with no returning customers and leave unobserved or partial months blank in the comparable retention view. Early cohorts can contain existing customers because purchases before the workbook began are unobserved. Keep partial periods, including December 2011, visibly labeled in transaction views.

## Future 90-day repeat-purchase prediction

Create customer snapshots at fixed dates for known customers with at least one qualifying purchase by the cutoff. Build features such as recency, order count, spend, and time since first observed purchase using only activity through that cutoff. Label a snapshot positive if the customer makes a qualifying purchase during the following 90 calendar days, from day 1 through day 90. Exclude snapshots without a fully observed follow-up window. Use a consistent historical lookback and account for limited history near the start of the workbook.

Train a simple baseline and logistic regression before testing more complex models. Split by cutoff date, keeping training label windows fully before validation cutoffs and using the latest eligible period as a held-out test. Use average precision and precision at outreach capacity to compare the model with a simple recency ranking. Check calibration for models that produce probabilities.

## Data-quality decisions to record

- **Missing customer IDs** Measure missingness by sheet and month before deciding how to present customer coverage. Keep unknown IDs distinct from identified customers.
- **Cancellations and adjustments** Report the UCI invoice prefix `C` and negative quantities separately, then investigate mismatches, zero quantities, and non-positive prices.
- **Duplicate candidates** Inspect matching full rows within and across sheets. Validate whether matches are repeated item lines or duplicate records before removing anything.
- **Incomplete observation** Check timestamp boundaries and monthly counts before comparing calendar periods. Document any gaps, partial periods, unobserved pre-history, and censored prediction windows.

Dataset attribution and license are recorded in the [project README](../README.md#data-source-and-attribution).
