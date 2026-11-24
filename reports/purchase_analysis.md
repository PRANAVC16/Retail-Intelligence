# Provisional purchase and cohort analysis

Run `src/analyze_purchases.py` after generating the [prepared data](data_preparation.md). The script reads the transaction CSV for calendar coverage and the purchase CSV for the metrics, then writes two CSVs to `data/processed/`. The purchase criteria, stock-code rule, and duplicate assumptions are inherited from preparation. Net revenue requires a separately validated reversal measure.

## First run

| Measure | Observed value |
| --- | ---: |
| Provisional gross sales | £19,699,784.97 |
| Distinct purchase invoices | 39,516 |
| Identified customers | 5,852 |
| Identified customers with at least two purchase invoices | 4,234 (72.35%) |

The repeat share in this table uses the entire observed window. November 2011 had the highest monthly provisional gross sales, at £1,457,742.24. December 2011 ends on the 9th and is marked partial.

## How the tables are built

- **Monthly purchase KPIs.** Sum eligible line amounts for gross sales and count each invoice once. Anonymous sales contribute to gross sales and order count. The customer repeat rate divides identified customers with two or more purchases in that month by identified buyers in the same month. Customer counts can include the same person in multiple months.
- **Invoice checks.** Each purchase invoice had a consistent calendar date, country, and known customer ID. There were 82 invoices with more than one timestamp on their shared date. The monthly analysis uses that date. Within-day ordering would require reviewing these invoices first.
- **Cohort retention.** Assign identified customers to their first observed purchase month. Count each active customer once per month and divide by the size of the original cohort. The December 2009 cohort had 951 customers, of whom 333 purchased in January 2010 (35.02%). Some members may have purchased before the workbook began.
- **Coverage.** Calendar months with source rows are labeled observed, with edge months marked partial when the workbook starts after the first day or ends before the last day. Observed months can still contain unrecorded activity. Cohort cells involving a partial or unobserved month are blank. Eligible months with no repeat activity show zero.

The exports contain 25 monthly KPI rows and 325 cohort-month rows. Monthly line counts, invoices, and gross sales reconcile to the purchase extract. Comparable month-zero retention is 100%, and December 2011 retention cells are blank.
