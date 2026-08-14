from __future__ import annotations

import re
from difflib import SequenceMatcher

import pandas as pd


def _normalize(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def _column_key(value: object) -> str:
    text = str(value).casefold().strip()
    text = text.replace("%", " percentage ")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _find_column(columns, candidates):
    normalized = {_column_key(column): column for column in columns}
    for candidate in candidates:
        key = _column_key(candidate)
        if key in normalized:
            return normalized[key]
    return None


def _format_money(value: float) -> str:
    if float(value).is_integer():
        return f"₹{int(value):,}"
    return f"₹{value:,.2f}"


def _extract_product_text(message: str) -> str:
    text = " ".join(str(message).strip().split())
    text = re.sub(r"(?i)^\s*(what|whats|what's|tell me|give me|show me)\s+", "", text)
    text = re.sub(r"(?i)\b(mrp|cogs\s*%|cogs percentage|cogs percent|cogs)\b", " ", text)
    text = re.sub(r"(?i)\b(of|for|is|the|a|an|product|item|price|cost)\b", " ", text)
    return " ".join(text.split()).strip(" ?.,")


def _best_product_match(query: str, product_names: list[str]) -> tuple[str | None, float]:
    query_n = _normalize(query)
    if not query_n:
        return None, 0.0

    best_name = None
    best_score = 0.0
    for name in product_names:
        name_n = _normalize(name)
        if query_n == name_n:
            return name, 1.0
        score = SequenceMatcher(None, query_n, name_n).ratio()
        # Strongly reward containment for short natural-language variants.
        if query_n in name_n or name_n in query_n:
            score = max(score, 0.92)
        if score > best_score:
            best_name, best_score = name, score
    return best_name, best_score


def answer_product_master_question(data: dict, message: str) -> str | None:
    """Answer MRP/COGS questions from item_category. Returns None if not such a question."""
    if not re.search(r"(?i)\b(mrp|cogs)\b", str(message)):
        return None

    master = data.get("item_category")
    if not isinstance(master, pd.DataFrame) or master.empty:
        return "Sorry, product master information is not available in the current data."

    item_col = _find_column(master.columns, ("Item Name", "Item", "Product Name", "Product"))
    mrp_col = _find_column(master.columns, ("MRP", "Selling Price", "Menu Price", "Price"))
    cogs_col = _find_column(master.columns, ("COGS", "COGS Value", "Cost", "Food Cost", "Product Cost"))
    cogs_pct_col = _find_column(master.columns, ("COGS %", "COGS%", "COGS Percentage", "Food Cost %", "Food Cost%"))

    if item_col is None or mrp_col is None or cogs_col is None:
        return "Sorry, I’m unable to answer this question with my current product-master data."

    work = master.copy()
    work = work[work[item_col].notna()].copy()
    work[item_col] = work[item_col].astype(str).str.strip()
    work = work[work[item_col] != ""]

    query = _extract_product_text(message)
    names = work[item_col].drop_duplicates().tolist()
    matched_name, score = _best_product_match(query, names)

    # Deliberately conservative: spelling tolerant, but do not confidently answer the wrong product.
    if matched_name is None or score < 0.62:
        return "Sorry, I couldn’t reliably match that product in the current product master."

    row = work.loc[work[item_col] == matched_name].iloc[-1]
    mrp = pd.to_numeric(pd.Series([row[mrp_col]]), errors="coerce").iloc[0]
    cogs = pd.to_numeric(pd.Series([row[cogs_col]]), errors="coerce").iloc[0]

    if pd.isna(mrp) or pd.isna(cogs):
        return f"I found *{matched_name}*, but its MRP/COGS details are incomplete in the product master."

    if cogs_pct_col is not None:
        cogs_pct = pd.to_numeric(pd.Series([row[cogs_pct_col]]), errors="coerce").iloc[0]
    else:
        cogs_pct = float(cogs) / float(mrp) * 100.0 if float(mrp) else float("nan")

    if pd.notna(cogs_pct) and abs(float(cogs_pct)) <= 1.0:
        # Excel percentage cells may be stored as 0.32 rather than 32.
        cogs_pct = float(cogs_pct) * 100.0

    pct_text = f"{float(cogs_pct):.1f}%" if pd.notna(cogs_pct) else "Not available"

    return (
        f"*{matched_name}*\n"
        f"MRP: *{_format_money(float(mrp))}*\n"
        f"COGS: *{_format_money(float(cogs))}*\n"
        f"COGS %: *{pct_text}*"
    )
