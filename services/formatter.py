from datetime import datetime


def _format_report_date(report_date: str) -> str:
    date_value = datetime.strptime(report_date, "%Y-%m-%d")
    return date_value.strftime("%d %b %Y")


def _format_column_date(report_date: str) -> str:
    date_value = datetime.strptime(report_date, "%Y-%m-%d")
    return date_value.strftime("%d %b")


def _format_month_label(report_date: str) -> str:
    date_value = datetime.strptime(report_date, "%Y-%m-%d")
    return date_value.strftime("%b'%y MTD")


def format_yesterday_sales_report(report: dict) -> str:
    report_date = _format_report_date(report["report_date"])
    yesterday_label = _format_column_date(report["report_date"])
    month_label = _format_month_label(report["report_date"])

    store_width = 22
    yesterday_width = 12
    month_width = 14

    lines = [
        f"📊 *Yesterday Sales ({report_date})*",
        "",
        "```",
        (
            f"{'Store':<{store_width}}"
            f"{yesterday_label:>{yesterday_width}}"
            f"{month_label:>{month_width}}"
        ),
        "-" * (store_width + yesterday_width + month_width),
    ]

    for row in report["rows"]:
        store_name = str(row["store"])[:store_width]

        lines.append(
            f"{store_name:<{store_width}}"
            f"{row['yesterday_sales']:>{yesterday_width},.0f}"
            f"{row['month_to_date_sales']:>{month_width},.0f}"
        )

    lines.extend(
        [
            "-" * (store_width + yesterday_width + month_width),
            (
                f"{'TOTAL':<{store_width}}"
                f"{report['total']['yesterday_sales']:>{yesterday_width},.0f}"
                f"{report['total']['month_to_date_sales']:>{month_width},.0f}"
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