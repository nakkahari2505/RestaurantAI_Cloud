from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from twilio.twiml.messaging_response import MessagingResponse

from services.data_loader import load_auberry_workbook
from services.formatter import format_yesterday_sales_report
from services.message_router import route_message
from services.sales_for_a_period import get_store_performance_report
from services.sales_for_a_period_image import (
    generate_sales_for_a_period_image,
)
from services.yesterday_sales import get_yesterday_sales_report


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading Auberry workbook into memory...")

    data = load_auberry_workbook()

    print(
        "Workbook loaded successfully:",
        f"{len(data['sales'])} sales rows",
    )

    yield


app = FastAPI(lifespan=lifespan)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)


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


@app.get(
    "/yesterday-message",
    response_class=PlainTextResponse,
)
def yesterday_sales_message():
    data = load_auberry_workbook()
    report = get_yesterday_sales_report(data)

    return format_yesterday_sales_report(report)


@app.get("/sales-for-a-period-image")
def sales_for_a_period_image(
    start_date: str = "01 Apr 2026",
    end_date: str = "30 Apr 2026",
):
    data = load_auberry_workbook()

    report = get_store_performance_report(
        data=data,
        start_date_text=start_date,
        end_date_text=end_date,
    )

    image_result = generate_sales_for_a_period_image(
        report
    )

    return FileResponse(
        path=image_result["file_path"],
        media_type="image/png",
    )


@app.post("/whatsapp")
async def whatsapp(
    request: Request,
    Body: str = Form(...),
):
    routed_response = route_message(Body)

    response = MessagingResponse()
    message = response.message()

    message.body(
        routed_response["body"]
    )

    if (
        routed_response["response_type"]
        == "media"
    ):
        relative_media_url = routed_response[
            "relative_media_url"
        ]

        base_url = str(
            request.base_url
        ).rstrip("/")

        public_media_url = (
            f"{base_url}{relative_media_url}"
        )

        print(
            "Sending WhatsApp media URL:",
            public_media_url,
        )

        message.media(public_media_url)

    return PlainTextResponse(
        content=str(response),
        media_type="application/xml",
    )