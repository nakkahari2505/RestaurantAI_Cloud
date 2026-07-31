from datetime import datetime


def _parse_report_date(report_date: str) -> datetime:
    return datetime.strptime(report_date, "%Y-%m-%d")


def _format_report_date(report_date: str) -> str:
    date_value = _parse_report_date(report_date)
    return date_value.strftime("%d %b %Y")


def format_yesterday_sales_report(report: dict) -> str:
    report_date = _format_report_date(report["report_date"])

    store_width = 20
    yesterday_width = 12
    mtd_width = 12
    table_width = store_width + yesterday_width + mtd_width

    lines = [
        "📊 *Yesterday Sales*",
        f"📅 {report_date}",
        "",
        "```",
        (
            f"{'Store':<{store_width}}"
            f"{'Yesterday':>{yesterday_width}}"
            f"{'MTD':>{mtd_width}}"
        ),
        "-" * table_width,
    ]

    for row in report["rows"]:
        store_name = str(row["store"])[:store_width]

        lines.append(
            f"{store_name:<{store_width}}"
            f"{row['yesterday_sales']:>{yesterday_width},.0f}"
            f"{row['month_to_date_sales']:>{mtd_width},.0f}"
        )

    lines.extend(
        [
            "-" * table_width,
            (
                f"{'TOTAL':<{store_width}}"
                f"{report['total']['yesterday_sales']:>{yesterday_width},.0f}"
                f"{report['total']['month_to_date_sales']:>{mtd_width},.0f}"
            ),
            "```",
            "",
        ]
    )

    if report.get("warning"):
        lines.extend(
            [
                "⚠️ *Data Warning:*",
                report["warning"],
            ]
        )
    else:
        lines.append("✅ Data refreshed successfully.")

    return "\n".join(lines)