import re

from services.data_loader import load_auberry_workbook
from services.formatter import (
    format_store_performance_report,
    format_yesterday_sales_report,
)
from services.sales_analytics import get_store_performance_report
from services.yesterday_sales import get_yesterday_sales_report


SALES_PERIOD_PATTERN = re.compile(
    r"^sales\s+from\s+"
    r"(\d{1,2}\s+[a-zA-Z]{3}\s+\d{4})"
    r"\s+to\s+"
    r"(\d{1,2}\s+[a-zA-Z]{3}\s+\d{4})$",
    re.IGNORECASE,
)


def route_message(message: str) -> str:
    normalized_message = " ".join(
        message.strip().split()
    )

    yesterday_commands = {
        "yesterday sales",
        "yesterdays sales",
        "yesterday sale",
    }

    if normalized_message.lower() in yesterday_commands:
        data = load_auberry_workbook()
        report = get_yesterday_sales_report(data)

        return format_yesterday_sales_report(report)

    sales_period_match = SALES_PERIOD_PATTERN.match(
        normalized_message
    )

    if sales_period_match:
        start_date_text = sales_period_match.group(1)
        end_date_text = sales_period_match.group(2)

        data = load_auberry_workbook()

        try:
            report = get_store_performance_report(
                data=data,
                start_date_text=start_date_text,
                end_date_text=end_date_text,
            )
        except ValueError as error:
            return str(error)

        return format_store_performance_report(report)

    return (
        "Sorry, I could not understand that request.\n\n"
        "Currently available commands:\n"
        "• Yesterday Sales\n"
        "• Sales from 01 Jul 2026 to 14 Jul 2026"
    )