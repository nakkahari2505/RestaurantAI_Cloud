import re

from services.data_loader import load_auberry_workbook
from services.formatter import format_yesterday_sales_report
from services.kpi_period_comparison import (
    get_kpi_period_comparison_report,
)
from services.kpi_period_comparison_image import (
    generate_kpi_period_comparison_image,
)
from services.sales_for_a_period import (
    get_store_performance_report,
)
from services.sales_for_a_period_image import (
    generate_sales_for_a_period_image,
)
from services.yesterday_sales import (
    get_yesterday_sales_report,
)


DATE_TOKEN_PATTERN = (
    r"\d{1,2}(?:-[a-zA-Z]{3}-|\s+[a-zA-Z]{3}\s+)\d{4}"
)


SALES_PERIOD_PATTERN = re.compile(
    rf"^sales\s+from\s+"
    rf"({DATE_TOKEN_PATTERN})"
    rf"\s+to\s+"
    rf"({DATE_TOKEN_PATTERN})$",
    re.IGNORECASE,
)


COMPARISON_PATTERN = re.compile(
    rf"^compare\s+"
    rf"({DATE_TOKEN_PATTERN})\s+"
    rf"({DATE_TOKEN_PATTERN})\s+"
    rf"({DATE_TOKEN_PATTERN})\s+"
    rf"({DATE_TOKEN_PATTERN})$",
    re.IGNORECASE,
)


def _display_date(
    date_text: str,
) -> str:
    """
    Convert any accepted input date into the official
    RestaurantAI display format: DD-Mmm-YYYY.
    """
    cleaned_date = " ".join(
        str(date_text).strip().split()
    )

    cleaned_date = cleaned_date.replace(
        " ",
        "-",
    )

    parts = cleaned_date.split("-")

    if len(parts) != 3:
        return cleaned_date

    day_text, month_text, year_text = parts

    try:
        day_number = int(day_text)
    except ValueError:
        return cleaned_date

    return (
        f"{day_number:02d}-"
        f"{month_text.title()}-"
        f"{year_text}"
    )


def route_message(
    message: str,
) -> dict:
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
        str(message).strip().split()
    )

    normalized_lower = (
        normalized_message.lower()
    )

    yesterday_commands = {
        "yesterday sales",
        "yesterdays sales",
        "yesterday sale",
    }

    # =====================================================
    # CAPABILITY 1: YESTERDAY SALES
    # =====================================================

    if normalized_lower in yesterday_commands:
        data = load_auberry_workbook()

        report = get_yesterday_sales_report(
            data
        )

        return {
            "response_type": "text",
            "body": format_yesterday_sales_report(
                report
            ),
        }

    # =====================================================
    # CAPABILITY 2: SALES FOR A PERIOD
    # =====================================================

    sales_period_match = SALES_PERIOD_PATTERN.match(
        normalized_message
    )

    if sales_period_match:
        start_date_text = (
            sales_period_match.group(1)
        )

        end_date_text = (
            sales_period_match.group(2)
        )

        data = load_auberry_workbook()

        try:
            report = get_store_performance_report(
                data=data,
                start_date_text=start_date_text,
                end_date_text=end_date_text,
            )

            image_result = (
                generate_sales_for_a_period_image(
                    report
                )
            )

        except ValueError as error:
            return {
                "response_type": "text",
                "body": str(error),
            }

        except Exception as error:
            print(
                "Sales-for-period report error:",
                repr(error),
            )

            return {
                "response_type": "text",
                "body": (
                    "The sales report could not be generated. "
                    "Please try again."
                ),
            }

        start_date_display = _display_date(
            start_date_text
        )

        end_date_display = _display_date(
            end_date_text
        )

        return {
            "response_type": "media",
            "body": (
                "📊 Sales Performance\n"
                f"{start_date_display} to "
                f"{end_date_display}"
            ),
            "relative_media_url": (
                image_result["relative_url"]
            ),
        }

    # =====================================================
    # CAPABILITY 3: KPI PERIOD COMPARISON
    # =====================================================

    comparison_match = COMPARISON_PATTERN.match(
        normalized_message
    )

    if comparison_match:
        from_start_date_text = (
            comparison_match.group(1)
        )

        from_end_date_text = (
            comparison_match.group(2)
        )

        to_start_date_text = (
            comparison_match.group(3)
        )

        to_end_date_text = (
            comparison_match.group(4)
        )

        data = load_auberry_workbook()

        try:
            report = (
                get_kpi_period_comparison_report(
                    data=data,
                    from_start_date_text=(
                        from_start_date_text
                    ),
                    from_end_date_text=(
                        from_end_date_text
                    ),
                    to_start_date_text=(
                        to_start_date_text
                    ),
                    to_end_date_text=(
                        to_end_date_text
                    ),
                )
            )

            image_result = (
                generate_kpi_period_comparison_image(
                    report
                )
            )

        except ValueError as error:
            return {
                "response_type": "text",
                "body": str(error),
            }

        except Exception as error:
            print(
                "KPI comparison report error:",
                repr(error),
            )

            return {
                "response_type": "text",
                "body": (
                    "The comparison report could not "
                    "be generated. Please try again."
                ),
            }

        from_start_display = _display_date(
            from_start_date_text
        )

        from_end_display = _display_date(
            from_end_date_text
        )

        to_start_display = _display_date(
            to_start_date_text
        )

        to_end_display = _display_date(
            to_end_date_text
        )

        return {
            "response_type": "media",
            "body": (
                "📊 Store Performance Comparison\n"
                f"{from_start_display} to "
                f"{from_end_display}\n"
                "vs\n"
                f"{to_start_display} to "
                f"{to_end_display}"
            ),
            "relative_media_url": (
                image_result["relative_url"]
            ),
        }

    # =====================================================
    # SPECIFIC INVALID-COMMAND GUIDANCE
    # =====================================================

    if normalized_lower.startswith(
        "compare"
    ):
        return {
            "response_type": "text",
            "body": (
                "Please use the comparison command "
                "in this format:\n\n"
                "Compare DD-Mmm-YYYY DD-Mmm-YYYY "
                "DD-Mmm-YYYY DD-Mmm-YYYY\n\n"
                "Example:\n"
                "Compare 01-Apr-2025 30-Jun-2025 "
                "01-Apr-2026 30-Jun-2026"
            ),
        }

    if normalized_lower.startswith(
        "sales"
    ):
        return {
            "response_type": "text",
            "body": (
                "Please use the sales command "
                "in this format:\n\n"
                "Sales from DD-Mmm-YYYY "
                "to DD-Mmm-YYYY\n\n"
                "Example:\n"
                "Sales from 01-Jul-2026 "
                "to 14-Jul-2026"
            ),
        }

    # =====================================================
    # UNKNOWN COMMAND
    # =====================================================

    return {
        "response_type": "text",
        "body": (
            "Sorry, I could not understand that request.\n\n"
            "Currently available commands:\n\n"
            "• Yesterday Sales\n\n"
            "• Sales from 01-Jul-2026 "
            "to 14-Jul-2026\n\n"
            "• Compare 01-Apr-2025 30-Jun-2025 "
            "01-Apr-2026 30-Jun-2026"
        ),
    }