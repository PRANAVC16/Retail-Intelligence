"""Generate a portable Power BI project from the aggregate analysis CSVs."""

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5


ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / "data" / "processed"
REPORT = ROOT / "Retail.Report"
MODEL = ROOT / "Retail.SemanticModel"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item"
REPORT_SCHEMA = f"{SCHEMA}/report"
DEFINITION = REPORT / "definition"
FABRIC_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
GBP = "£#,0.00"
PERCENT = "0.0%"


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_csv(name):
    with (DATA / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def model_table(name, rows, fields, measures):
    columns = []
    dax_rows = []
    for source in rows:
        row = []
        for field, _, converter, _ in fields:
            value = source[field]
            if value == "":
                row.append("BLANK()")
            elif converter is str:
                row.append('"' + value.replace('"', '""') + '"')
            else:
                row.append(str(converter(value)))
        dax_rows.append("    { " + ", ".join(row) + " }")
    types = {str: ("string", "STRING"), int: ("int64", "INTEGER"),
             float: ("double", "DOUBLE")}
    arguments = []
    for _, label, converter, format_string in fields:
        model_type, dax_type = types[converter]
        column = {
            "type": "calculatedTableColumn", "name": label, "dataType": model_type,
            "sourceColumn": f"[{label}]", "summarizeBy": "none",
        }
        if format_string:
            column["formatString"] = format_string
        columns.append(column)
        arguments.append(f'"{label}", {dax_type}')
    expression = "DATATABLE(" + ", ".join(arguments) + ", {\n" + ",\n".join(dax_rows) + "\n})"
    return {
        "name": name, "columns": columns,
        "measures": [{"name": label, "expression": formula, "formatString": fmt}
                     for label, formula, fmt in measures],
        "partitions": [{"name": name, "mode": "import",
                        "source": {"type": "calculated", "expression": expression}}],
    }


def field(table, name, kind="Column"):
    return {
        "field": {kind: {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}},
        "queryRef": f"{table}.{name}", "nativeQueryRef": name,
    }


def identity(label):
    return hashlib.sha256(label.encode()).hexdigest()[:20]


def add_page(label, specifications):
    page_id = identity(label)
    folder = DEFINITION / "pages" / page_id
    write_json(folder / "page.json", {
        "$schema": f"{REPORT_SCHEMA}/definition/page/2.1.0/schema.json",
        "name": page_id, "displayName": label, "displayOption": "FitToPage",
        "height": 720, "width": 1280,
    })
    for index, (title, kind, box, fields, sort) in enumerate(specifications, start=1):
        visual_id = identity(f"{label}/{title}")
        x, y, width, height = box
        query = {"queryState": {role: {"projections": columns} for role, columns in fields.items()}}
        if sort:
            projection, direction = sort
            query["sortDefinition"] = {
                "sort": [{"field": projection["field"], "direction": direction}],
                "isDefaultSort": False,
            }
        write_json(folder / "visuals" / visual_id / "visual.json", {
            "$schema": f"{REPORT_SCHEMA}/definition/visualContainer/2.9.0/schema.json",
            "name": visual_id,
            "position": {"x": x, "y": y, "z": index * 1000, "width": width,
                         "height": height, "tabOrder": index * 1000},
            "visual": {
                "visualType": kind, "query": query,
                "visualContainerObjects": {"title": [{"properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "text": {"expr": {"Literal": {"Value": f"'{title}'"}}},
                }}]},
            },
        })
    return page_id


def main():
    revenue = read_csv("monthly_revenue_reconciliation.csv")
    for row in revenue:
        row["axis_month"] = row["month"] + (" (partial)" if row["coverage"] == "partial" else "")
    countries = read_csv("monthly_country_revenue.csv")
    segment_counts = Counter(row["segment"] for row in read_csv("customer_segments.csv"))
    segments = [{"segment": label, "count": count} for label, count in segment_counts.items()]
    tables = [
        model_table("Monthly Revenue", revenue, [
            ("axis_month", "Month", str, None),
            ("gross_sales_gbp", "Gross amount", float, GBP),
            ("provisional_net_gbp", "Provisional net amount", float, GBP),
            ("purchase_orders", "Invoice count", int, "#,0"),
        ], [
            ("Gross sales", 'SUM(\'Monthly Revenue\'[Gross amount])', GBP),
            ("Provisional net", 'SUM(\'Monthly Revenue\'[Provisional net amount])', GBP),
            ("Purchase invoices", 'SUM(\'Monthly Revenue\'[Invoice count])', "#,0"),
        ]),
        model_table("Country Revenue", countries, [
            ("country", "Country", str, None), ("month", "Month", str, None),
            ("gross_sales_gbp", "Gross amount", float, GBP),
        ], [("Country gross sales", 'SUM(\'Country Revenue\'[Gross amount])', GBP)]),
        model_table("Segments", segments, [
            ("segment", "Segment", str, None), ("count", "Segment size", int, "#,0"),
        ], [("Customers", "SUM(Segments[Segment size])", "#,0")]),
        model_table("Cohorts", read_csv("cohort_retention.csv"), [
            ("cohort_month", "First observed purchase month", str, None),
            ("month_offset", "Months since first purchase", int, "0"),
            ("retention_rate", "Rate", float, PERCENT),
        ], [("Retention", "SELECTEDVALUE(Cohorts[Rate])", PERCENT)]),
        model_table("Model Evaluation", read_csv("model_evaluation.csv"), [
            ("model", "Model", str, None), ("split", "Holdout", str, None),
            ("cutoff", "Cutoff", str, None), ("customers", "Customers evaluated", int, "#,0"),
            ("positive_rate", "Repeat share", float, PERCENT),
            ("average_precision", "Average precision", float, PERCENT),
            ("precision_at_top_10pct", "Top 10% precision", float, PERCENT),
            ("brier_score", "Brier score", float, "0.000"),
        ], []),
    ]
    write_json(MODEL / "definition.pbism", {"version": "1.0", "settings": {}})
    for path, item_type in [(REPORT, "Report"), (MODEL, "SemanticModel")]:
        write_json(path / ".platform", {
            "$schema": f"{FABRIC_SCHEMA}/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": item_type, "displayName": "Retail Intelligence"},
            "config": {"version": "2.0",
                       "logicalId": str(uuid5(NAMESPACE_URL, f"retail-retention-intelligence/{item_type}"))},
        })
    write_json(MODEL / "model.bim", {
        "name": "Retail Intelligence", "compatibilityLevel": 1600,
        "model": {"culture": "en-GB", "defaultPowerBIDataSourceVersion": "powerBI_V3",
                  "tables": tables},
    })
    write_json(REPORT / "definition.pbir", {
        "$schema": f"{REPORT_SCHEMA}/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": "../Retail.SemanticModel"}},
    })
    write_json(DEFINITION / "version.json", {
        "$schema": f"{REPORT_SCHEMA}/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0",
    })
    write_json(DEFINITION / "report.json", {
        "$schema": f"{REPORT_SCHEMA}/definition/report/3.3.0/schema.json",
        "themeCollection": {"baseTheme": {
            "name": "CY24SU10", "type": "SharedResources",
            "reportVersionAtImport": {"visual": "2.9.0", "page": "2.1.0", "report": "3.3.0"},
        }},
    })
    gross = field("Monthly Revenue", "Gross sales", "Measure")
    net = field("Monthly Revenue", "Provisional net", "Measure")
    invoices = field("Monthly Revenue", "Purchase invoices", "Measure")
    month = field("Monthly Revenue", "Month")
    country = field("Country Revenue", "Country")
    country_sales = field("Country Revenue", "Country gross sales", "Measure")
    customers = field("Segments", "Customers", "Measure")
    pages = [
        add_page("Revenue", [
            ("Gross sales", "card", (24, 24, 390, 120), {"Values": [gross]}, None),
            ("Provisional net after matched reversals", "card", (445, 24, 390, 120),
             {"Values": [net]}, None),
            ("Purchase invoices", "card", (866, 24, 390, 120), {"Values": [invoices]}, None),
            ("Monthly gross sales and provisional net", "lineChart", (24, 168, 800, 528),
             {"Category": [month], "Y": [gross, net]}, (month, "Ascending")),
            ("Gross sales by country", "barChart", (848, 168, 408, 528),
             {"Category": [country], "Y": [country_sales]}, (country_sales, "Descending")),
        ]),
        add_page("Customers", [
            ("Customer segments as of 30 November 2011", "barChart", (24, 24, 1232, 672),
             {"Category": [field("Segments", "Segment")], "Y": [customers]},
             (customers, "Descending")),
        ]),
        add_page("Cohort retention", [
            ("Monthly retention by first observed purchase", "pivotTable", (24, 24, 1232, 672),
             {"Rows": [field("Cohorts", "First observed purchase month")],
              "Columns": [field("Cohorts", "Months since first purchase")],
              "Values": [field("Cohorts", "Retention", "Measure")]}, None),
        ]),
        add_page("90-day repeat purchase", [
            ("Out-of-time model performance", "tableEx", (24, 24, 1232, 360),
             {"Values": [field("Model Evaluation", column["name"]) for column in tables[-1]["columns"]]},
             None),
        ]),
    ]
    write_json(DEFINITION / "pages" / "pages.json", {
        "$schema": f"{REPORT_SCHEMA}/definition/pagesMetadata/1.1.0/schema.json",
        "pageOrder": pages, "activePageName": pages[0],
    })
    write_json(ROOT / "Retail.pbip", {
        "$schema": f"{FABRIC_SCHEMA}/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": "Retail.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })


if __name__ == "__main__":
    main()
