from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd

from services.reports.yesterday.morning_report import IST, _prepare_sales_frame


def detect_three_day_store_declines(
    data: dict,
    as_of_date: date | None = None,
) -> dict:
    """Find stores whose sales declined on each of the latest 3 days vs same weekday last week.

    A day is comparable only when the store has positive sales on both the
    current day and the same weekday seven days earlier. This prevents store
    closures from being reported as performance declines.
    """
    sales = _prepare_sales_frame(data)
    today = as_of_date if as_of_date is not None else datetime.now(IST).date()
    performance_through = today - timedelta(days=1)
    current_dates = [performance_through - timedelta(days=offset) for offset in (2, 1, 0)]

    daily = (
        sales.groupby(["Store", "Date"], as_index=False)["Sub Total"]
        .sum()
        .rename(columns={"Sub Total": "Sales"})
    )
    lookup = {
        (str(row["Store"]).strip(), row["Date"]): float(row["Sales"])
        for _, row in daily.iterrows()
    }

    stores = sorted({str(v).strip() for v in sales["Store"].dropna() if str(v).strip()})
    findings = []

    for store in stores:
        comparisons = []
        qualifies = True

        for current_date in current_dates:
            comparison_date = current_date - timedelta(days=7)
            current_sales = lookup.get((store, current_date), 0.0)
            comparison_sales = lookup.get((store, comparison_date), 0.0)

            if current_sales <= 0 or comparison_sales <= 0:
                qualifies = False
                break

            change_pct = ((current_sales - comparison_sales) / comparison_sales) * 100.0
            if change_pct >= 0:
                qualifies = False
                break

            comparisons.append({
                "date": current_date.isoformat(),
                "comparison_date": comparison_date.isoformat(),
                "sales": current_sales,
                "comparison_sales": comparison_sales,
                "change_pct": change_pct,
            })

        if qualifies and len(comparisons) == 3:
            findings.append({"store": store, "comparisons": comparisons})

    return {
        "performance_through": performance_through.isoformat(),
        "days_checked": [d.isoformat() for d in current_dates],
        "findings": findings,
        "count": len(findings),
    }
