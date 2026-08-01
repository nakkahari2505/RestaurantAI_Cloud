from datetime import datetime


def _parse_report_date(report_date: str) -> datetime:
    return datetime.strptime(report_date, "%Y-%m-%d")


def _format_report_date(report_date: str) -> str:
    date_value = _parse_report_date(report_date)
    return date_value.strftime("%d %b %Y")


def _format_date_with_ordinal(date_value: datetime) -> str:
    day = date_value.day

    if 10 < day % 100 < 14:
        suffix = "th"
    else:
        suffix = {
            1: "st",
            2: "nd",
            3: "rd",
        }.get(day % 10, "th")

    return f"{day}{suffix} {date_value.strftime('%b')}"


def _format_month_date_range(report_date: str) -> str:
    end_date = _parse_report_date(report_date)
    start_date = end_date.replace(day=1)

    return (
        f"{_format_date_with_ordinal(start_date)}"
        f" to "
        f"{_format_date_with_ordinal(end_date)}"
    )


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


def _format_decimal(value: float) -> str:
    numeric_value = float(value)

    if numeric_value.is_integer():
        return str(int(numeric_value))

    return f"{numeric_value:.1f}"


def _shorten_store_name(store_name: str, width: int) -> str:
    cleaned_name = str(store_name).strip()

    if len(cleaned_name) <= width:
        return cleaned_name

    return cleaned_name[: width - 1] + "…"


def _build_two_column_table(
    rows: list[dict],
    value_key: str,
    total_value: float,
) -> list[str]:
    store_width = 18
    value_width = 11
    table_width = store_width + value_width

    lines = [
        "```",
        (
            f"{'Store':<{store_width}}"
            f"{'Sales':>{value_width}}"
        ),
        "-" * table_width,
    ]

    for row in rows:
        store_name = _shorten_store_name(
            row["store"],
            store_width,
        )

        sales_value = _format_indian_number(
            row[value_key]
        )

        lines.append(
            f"{store_name:<{store_width}}"
            f"{sales_value:>{value_width}}"
        )

    lines.extend(
        [
            "-" * table_width,
            (
                f"{'TOTAL':<{store_width}}"
                f"{_format_indian_number(total_value):>{value_width}}"
            ),
            "```",
        ]
    )

    return lines


def format_yesterday_sales_report(report: dict) -> str:
    report_date = _format_report_date(
        report["report_date"]
    )

    month_date_range = _format_month_date_range(
        report["report_date"]
    )

    lines = [
        "📊 *Yesterday Sales*",
        f"📅 {report_date}",
        "",
    ]

    lines.extend(
        _build_two_column_table(
            rows=report["rows"],
            value_key="yesterday_sales",
            total_value=report["total"]["yesterday_sales"],
        )
    )

    lines.extend(
        [
            "",
            "📈 *Month Till Date*",
            f"🗓️ {month_date_range}",
            "",
        ]
    )

    lines.extend(
        _build_two_column_table(
            rows=report["rows"],
            value_key="month_to_date_sales",
            total_value=report["total"][
                "month_to_date_sales"
            ],
        )
    )

    lines.append("")

    if report.get("warning"):
        lines.extend(
            [
                "⚠️ *Data Warning:*",
                report["warning"],
            ]
        )
    else:
        lines.append(
            "✅ Data refreshed successfully."
        )

    return "\n".join(lines)


def _build_store_performance_table(
    report: dict,
) -> list[str]:
    store_width = 14
    sales_width = 11
    txns_width = 7
    ads_width = 9
    adt_width = 6
    apt_width = 7

    table_width = (
        store_width
        + sales_width
        + txns_width
        + ads_width
        + adt_width
        + apt_width
    )

    lines = [
        "```",
        (
            f"{'Store':<{store_width}}"
            f"{'Sales':>{sales_width}}"
            f"{'Txns':>{txns_width}}"
            f"{'ADS':>{ads_width}}"
            f"{'ADT':>{adt_width}}"
            f"{'APT':>{apt_width}}"
        ),
        "-" * table_width,
    ]

    for row in report["rows"]:
        store_name = _shorten_store_name(
            row["store"],
            store_width,
        )

        lines.append(
            f"{store_name:<{store_width}}"
            f"{_format_indian_number(row['total_sales']):>{sales_width}}"
            f"{_format_indian_number(row['total_txns']):>{txns_width}}"
            f"{_format_indian_number(row['ads']):>{ads_width}}"
            f"{_format_decimal(row['adt']):>{adt_width}}"
            f"{_format_indian_number(row['apt']):>{apt_width}}"
        )

    total = report["total"]

    lines.extend(
        [
            "-" * table_width,
            (
                f"{'TOTAL':<{store_width}}"
                f"{_format_indian_number(total['total_sales']):>{sales_width}}"
                f"{_format_indian_number(total['total_txns']):>{txns_width}}"
                f"{_format_indian_number(total['ads']):>{ads_width}}"
                f"{_format_decimal(total['adt']):>{adt_width}}"
                f"{_format_indian_number(total['apt']):>{apt_width}}"
            ),
            "```",
        ]
    )

    return lines


def _format_missing_dates(
    missing_dates: list[str],
) -> list[str]:
    formatted_dates = [
        _format_report_date(date_text)
        for date_text in missing_dates
    ]

    lines = []

    for index in range(0, len(formatted_dates), 3):
        date_group = formatted_dates[
            index:index + 3
        ]

        lines.append(", ".join(date_group))

    return lines


def format_store_performance_report(
    report: dict,
) -> str:
    start_date = _format_report_date(
        report["start_date"]
    )

    end_date = _format_report_date(
        report["end_date"]
    )

    lines = [
        "📊 *Sales Performance*",
        "",
        (
            f"🗓️ *Time Period:* "
            f"{start_date} to {end_date}"
        ),
        "",
    ]

    lines.extend(
        _build_store_performance_table(report)
    )

    lines.extend(
        [
            "",
            "ADS = Average Daily Sales",
            "ADT = Average Daily Transactions",
            "APT = Average Per Transaction",
            "",
        ]
    )

    if report["data_complete"]:
        lines.append(
            "✅ Sales data is available for all dates "
            "in the selected period."
        )
    else:
        lines.append(
            "⚠️ *Sales data is not available for:*"
        )

        lines.extend(
            _format_missing_dates(
                report["missing_dates"]
            )
        )

    return "\n".join(lines)