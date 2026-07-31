from fastapi import FastAPI

from services.data_loader import load_auberry_workbook
from services.yesterday_sales import get_yesterday_sales_report

app = FastAPI()


@app.get("/")
def home():
    return {
        "status": "running",
        "application": "RestaurantAI_Cloud"
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

    report = get_yesterday_sales_report(data)

    return report