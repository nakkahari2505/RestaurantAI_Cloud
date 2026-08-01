from datetime import datetime


def _format_report_date(report_date: str) -> str:
    date_value = datetime.strptime(report_date, "%Y-%m-%d")
    return date_value.strftime("%d %b %Y")


def _format_indian_number(value: float) -> str:
    number = int(round(float(value)))
    sign = "-" if number < 0 else ""
    digits = str(abs(number))

    if len(digits) <= 3:
        return sign + digits

    last_three = digits[-3:]
    remaining = digits[:-3]

    groups = []

    while len(remaining) > 2:
        groups.insert(0, remaining[-2:])
        remaining = remaining[:-2]

    if remaining:
        groups.insert(0, remaining)

    return sign + ",".join(groups + [last_three])


def format_yesterday_sales_report(report: dict) -> str:
    report_date = _format_report_date(report["report_date"])

    # Kept narrow enough for mobile WhatsApp.
    store_width = 18
    yesterday_width = 9
    gap_width = 2
    mtd_width = 11

    table_width = (
        store_width
        + yesterday_width
        + gap_width
        + mtd_width
    )

    lines = [
        "📊 *Yesterday Sales*",
        f"📅 {report_date}",
        "",
        "```",
        (
            f"{'Store':<{store_width}}"
            f"{'Yesterday':>{yesterday_width}}"
            f"{'':<{gap_width}}"
            f"{'MTD':>{mtd_width}}"
        ),
        "-" * table_width,
    ]

    for row in report["rows"]:
        store_name = str(row["store"]).strip()

        if len(store_name) > store_width:
            store_name = store_name[: store_width - 1] + "…"

        yesterday_sales = _format_indian_number(
            row["yesterday_sales"]
        )

        month_to_date_sales = _format_indian_number(
            row["month_to_date_sales"]
        )

        lines.append(
            f"{store_name:<{store_width}}"
            f"{yesterday_sales:>{yesterday_width}}"
            f"{'':<{gap_width}}"
            f"{month_to_date_sales:>{mtd_width}}"
        )

    total = report["total"]

    total_yesterday = _format_indian_number(
        total["yesterday_sales"]
    )

    total_mtd = _format_indian_number(
        total["month_to_date_sales"]
    )

    lines.extend(
        [
            "-" * table_width,
            (
                f"{'TOTAL':<{store_width}}"
                f"{total_yesterday:>{yesterday_width}}"
                f"{'':<{gap_width}}"
                f"{total_mtd:>{mtd_width}}"
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