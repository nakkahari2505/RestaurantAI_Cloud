from services.data_loader import load_auberry_workbook
from services.formatter import format_yesterday_sales_report
from services.yesterday_sales import get_yesterday_sales_report


def route_message(message: str) -> str:
    normalized_message = " ".join(message.lower().strip().split())

    yesterday_commands = {
        "yesterday sales",
        "yesterdays sales",
        "yesterday sale",
    }

    if normalized_message in yesterday_commands:
        data = load_auberry_workbook()
        report = get_yesterday_sales_report(data)

        return format_yesterday_sales_report(report)

    return (
        "Sorry, I could not understand that request.\n\n"
        "Currently available command:\n"
        "• Yesterday Sales"
    )