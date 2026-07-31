from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUBERRY_FILE = PROJECT_ROOT / "data" / "auberry" / "sales.xlsx"


def load_auberry_workbook():
    if not AUBERRY_FILE.exists():
        raise FileNotFoundError(
            f"Auberry sales file was not found at: {AUBERRY_FILE}"
        )

    workbook = pd.ExcelFile(AUBERRY_FILE)

    required_sheets = {"sales", "store_info", "item_category"}
    available_sheets = set(workbook.sheet_names)
    missing_sheets = required_sheets - available_sheets

    if missing_sheets:
        raise ValueError(
            f"Missing required sheets: {', '.join(sorted(missing_sheets))}"
        )

    sales = pd.read_excel(workbook, sheet_name="sales")
    store_info = pd.read_excel(workbook, sheet_name="store_info")
    item_category = pd.read_excel(workbook, sheet_name="item_category")

    return {
        "sales": sales,
        "store_info": store_info,
        "item_category": item_category,
    }