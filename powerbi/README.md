# Power BI Desktop report

Open [Retail.pbip](Retail.pbip) in Power BI Desktop with enhanced PBIR support. If Desktop prompts you to refresh calculated tables, select **Refresh now**. Keep the report and semantic model folders next to the project file.

| Page | Contents |
| --- | --- |
| Revenue | Gross sales, provisional net after matched reversals, purchase invoices, monthly revenue, and gross sales by country. December 2011 is marked partial. |
| Customers | Counts by customer segment as of November 30, 2011. |
| Cohort retention | Retention by first observed purchase month and elapsed months. Blank cells preserve partial-period and unavailable retention. |
| 90-day repeat purchase | Validation and held-out results for recency alone and the full logistic regression. |

The semantic model embeds aggregate rows from the processed CSVs as DAX calculated tables. To update them, close the project, rerun the Python analysis and report builder from the repository root, then reopen and refresh the project. The builder regenerates the report definitions. Save manual layout changes in a separate copy before rebuilding. If Desktop offers to upgrade the semantic model format on save, choose **Don't upgrade** to keep it compatible with the builder.

Compare the report totals with the [portfolio results](../reports/portfolio_results.md). Gross sales use the provisional merchandise and overlap rules. Provisional net deducts uniquely matched reversals. Dataset credit and license are in the [project README](../README.md#data-source-and-attribution).

Microsoft documents the [Power BI Project format](https://learn.microsoft.com/power-bi/developer/projects/projects-overview) and the [enhanced report definition format](https://learn.microsoft.com/power-bi/developer/embedded/projects-enhanced-report-format).
