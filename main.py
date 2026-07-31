from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse

from services.data_loader import load_auberry_workbook
from services.formatter import format_yesterday_sales_report
from services.message_router import route_message
from services.yesterday_sales import get_yesterday_sales_report

app = FastAPI()


@app.get("/")
def home():
    return {
        "status": "running",
        "application": "RestaurantAI_Cloud",
    }


@app.get("/test-data")
def test_data():
    data = load_auberry_workbook()

    return {
        "sales_rows": len(data["sales"]),
        "store_rows": len(data["store_info"]),
        "category_rows": len(data["item_category"]),
    }


@app.get("/yesterday")
def yesterday_sales():
    data = load_auberry_workbook()
    return get_yesterday_sales_report(data)


@app.get("/yesterday-message", response_class=PlainTextResponse)
def yesterday_sales_message():
    data = load_auberry_workbook()
    report = get_yesterday_sales_report(data)

    return format_yesterday_sales_report(report)


@app.post("/whatsapp")
async def whatsapp(
    Body: str = Form(...)
):
    reply = route_message(Body)

    response = MessagingResponse()
    response.message(reply)

    return PlainTextResponse(
        content=str(response),
        media_type="application/xml",
    )