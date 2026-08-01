import re

from services.data_loader import load_auberry_workbook
from services.formatter import format_yesterday_sales_report
from services.sales_for_a_period import get_store_performance_report
from services.sales_for_a_period_image import (
    generate_sales_for_a_period_image,
)
from services.yesterday_sales import get_yesterday_sales_report


SALES_PERIOD_PATTERN = re.compile(
    r"^sales\s+from\s+"
    r"(\d{1,2}\s+[a-zA-Z]{3}\s+\d{4})"
    r"\s+to\s+"
    r"(\d{1,2}\s+[a-zA-Z]{3}\s+\d{4})$",
    re.IGNORECASE,
)


def route_message(message: str) -> dict:
    """
    Route a WhatsApp message and return either:

    {
        "response_type": "text",
        "body": "..."
    }

    or:

    {
        "response_type": "media",
        "body": "...",
        "relative_media_url": "/static/reports/....png"
    }
    """
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

        return {
            "response_type": "text",
            "body": format_yesterday_sales_report(report),
        }

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

            image_result = generate_sales_for_a_period_image(
                report
            )

        except ValueError as error:
            return {
                "response_type": "text",
                "body": str(error),
            }

        return {
            "response_type": "media",
            "body": (
                "📊 Sales Performance\n"
                f"{start_date_text} to {end_date_text}"
            ),
            "relative_media_url": image_result[
                "relative_url"
            ],
        }

    return {
        "response_type": "text",
        "body": (
            "Sorry, I could not understand that request.\n\n"
            "Currently available commands:\n"
            "• Yesterday Sales\n"
            "• Sales from 01 Jul 2026 to 14 Jul 2026"
        ),
    }