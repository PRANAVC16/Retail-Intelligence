# Data preparation

`src/prepare_dataset.py` reads the original UCI workbook using the same reader as the inspection script. It makes a copy of each input table, cleans the text and number fields, adds flags, and writes two UTF-8 CSVs. Dataset attribution and license are in the [project README](../README.md#data-source-and-attribution).

| Output | What one row represents |
| --- | --- |
| `transactions.csv` | One row from the original workbook, including cancelled, anonymous, and exact-match rows. `source_sheet` and `source_row` point back to the original Excel line. |
| `purchase_lines.csv` | One provisional purchase line from the transaction table. Several lines can share an invoice. |

The text fields are trimmed and blank text becomes missing. Invoice and stock codes are uppercased. IDs and codes should be imported as text. Quantity and price are numeric. The date fields use ISO format. `signed_line_value_gbp` is quantity multiplied by unit price, including negative values. It is a line amount for investigation before revenue measures are finalized.

## Rules and review decisions

- **Missing customer IDs** Keep anonymous lines in the transaction table and include eligible ones in the purchase extract. Filter them out when grouping by customer.
- **Duplicate candidates** Compare all eight original fields before normalizing values. Flag each member of an exact-match group. For exact matches across worksheets, match occurrences one for one and flag the copies from the later worksheet in workbook order. The purchase extract excludes those later copies and retains repeated lines that cannot be paired across worksheets. This rule assumes matching cross-sheet occurrences are copies of the same events. Repeated lines within one sheet still need review before revenue is finalized.
- **Provisional purchase criteria** Require a six-digit invoice, a readable timestamp, positive quantity and price, and a stock code with five digits followed by optional letters. This stock-code pattern is a proxy for merchandise. Review excluded codes and any special codes that match the pattern before using the extract for final KPIs.
- **Cancellations and adjustments** The full table flags the cancellation prefix, negative quantities, and non-positive prices. Review discrepancies and link reversal lines where possible before calculating net revenue.
- **Observation periods** The workbook ends on December 9, 2011. For comparable cohort retention, leave that final partial month blank and use fully observed follow-up windows for future labels.

## Reading the code

`prepare_transactions()` combines the worksheet tables. Arrays of true/false values flag which lines meet each rule. `export_tables()` uses the purchase flag to select rows, stages both CSVs, then replaces the old exports. `main()` handles file paths and prints counts for the workbook.

## First run

The original workbook produced 1,067,371 transaction lines and 1,014,945 provisional purchase lines. The preparation pass flagged 22,523 lines as later copies of cross-sheet matches. The original workbook's SHA-256 hash matched before and after the run.
