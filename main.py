from fastapi import FastAPI
from services.data_loader import load_auberry_workbook

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
        "category_rows": len(data["item_category"])
    }