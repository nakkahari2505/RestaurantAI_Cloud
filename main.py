from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from twilio.twiml.messaging_response import MessagingResponse

from services.data_loader import load_auberry_workbook
from services.presentation.formatter import format_yesterday_sales_report
from services.reports.kpi_comparison.report import (
    get_kpi_period_comparison_report,
)
from services.reports.kpi_comparison.image import (
    generate_kpi_period_comparison_image,
)
from services.message_router import route_message
import services.semantics.vocabulary.metrics as metrics
from services.reports.sales_period.report import (
    get_store_performance_report,
)
from services.reports.sales_period.image import (
    generate_sales_for_a_period_image,
)
from services.reports.yesterday.legacy_report import (
    get_yesterday_sales_report,
)
from services.semantics.builders.store_builder import (
    build_store_dictionary,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(
        "Loading Auberry workbook into memory..."
    )

    data = load_auberry_workbook()

    print(
        "Workbook loaded successfully:",
        f"{len(data['sales'])} sales rows",
    )

    yield


app = FastAPI(
    lifespan=lifespan
)


app.mount(
    "/static",
    StaticFiles(
        directory="static"
    ),
    name="static",
)


# =========================================================
# APPLICATION STATUS
# =========================================================


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
        "sales_rows": len(
            data["sales"]
        ),
        "store_rows": len(
            data["store_info"]
        ),
        "category_rows": len(
            data["item_category"]
        ),
    }


# =========================================================
# CAPABILITY 1: YESTERDAY SALES
# =========================================================


@app.get("/yesterday")
def yesterday_sales():
    data = load_auberry_workbook()

    return get_yesterday_sales_report(
        data
    )


@app.get(
    "/yesterday-message",
    response_class=PlainTextResponse,
)
def yesterday_sales_message():
    data = load_auberry_workbook()

    report = get_yesterday_sales_report(
        data
    )

    return format_yesterday_sales_report(
        report
    )


# =========================================================
# CAPABILITY 2: SALES FOR A PERIOD
# =========================================================


@app.get("/sales-for-a-period-image")
def sales_for_a_period_image(
    start_date: str = "01-Apr-2026",
    end_date: str = "30-Apr-2026",
):
    data = load_auberry_workbook()

    report = get_store_performance_report(
        data=data,
        start_date_text=start_date,
        end_date_text=end_date,
    )

    image_result = (
        generate_sales_for_a_period_image(
            report
        )
    )

    return FileResponse(
        path=image_result["file_path"],
        media_type="image/png",
    )


# =========================================================
# CAPABILITY 3: KPI PERIOD COMPARISON
# =========================================================


@app.get("/compare-test")
def compare_test():
    data = load_auberry_workbook()

    report = (
        get_kpi_period_comparison_report(
            data=data,
            from_start_date_text=(
                "01-Apr-2025"
            ),
            from_end_date_text=(
                "30-Jun-2025"
            ),
            to_start_date_text=(
                "01-Apr-2026"
            ),
            to_end_date_text=(
                "30-Jun-2026"
            ),
        )
    )

    return report


@app.get("/compare-image-test")
def compare_image_test():
    data = load_auberry_workbook()

    report = (
        get_kpi_period_comparison_report(
            data=data,
            from_start_date_text=(
                "01-Apr-2025"
            ),
            from_end_date_text=(
                "30-Jun-2025"
            ),
            to_start_date_text=(
                "01-Apr-2026"
            ),
            to_end_date_text=(
                "30-Jun-2026"
            ),
        )
    )

    image_result = (
        generate_kpi_period_comparison_image(
            report
        )
    )

    return FileResponse(
        path=image_result["file_path"],
        media_type="image/png",
    )


# =========================================================
# GPT CONNECTION TEST
# =========================================================


@app.get("/llm-test")
def llm_test():
    """
    Test basic OpenAI connectivity without involving:

    - WhatsApp
    - message routing
    - sales calculations
    - report generation
    """
    try:
        from services.llm_service import (
            llm_service,
        )

        response_text = (
            llm_service.test_connection()
        )

        return {
            "status": "success",
            "response": response_text,
        }

    except Exception as error:
        print(
            "LLM connection test error:",
            repr(error),
        )

        return {
            "status": "error",
            "error_type": type(
                error
            ).__name__,
            "message": str(
                error
            ),
        }


# =========================================================
# GPT INTENT TEST
# =========================================================


@app.get("/intent-test")
def intent_test(
    message: str = (
        "How did we perform yesterday?"
    ),
):
    """
    Test RestaurantAI's natural-language intent parser.

    This endpoint only performs:

        User message
            ↓
        GPT intent extraction
            ↓
        Structured JSON

    It does not:

    - run a business engine,
    - read sales data,
    - generate a report,
    - change WhatsApp routing.
    """
    try:
        from services.semantics.intent_parser import (
            parse_intent,
        )

        intent_result = parse_intent(
            user_message=message
        )

        return {
            "status": "success",
            "input_message": message,
            "intent": intent_result,
        }

    except Exception as error:
        print(
            "Intent parser test error:",
            repr(error),
        )

        return {
            "status": "error",
            "input_message": message,
            "error_type": type(
                error
            ).__name__,
            "message": str(
                error
            ),
        }


@app.get("/ral-test")
def ral_test(
    message: str = "How did we perform yesterday?",
):
    """
    Shows the complete RestaurantAI Language (RAL)
    generated by GPT before any routing occurs.
    """
    try:
        from services.semantics.intent_parser import (
            parse_ral_request,
        )

        ral_request = parse_ral_request(
            message
        )

        return {
            "status": "success",
            "input_message": message,
            "ral": ral_request,
        }

    except Exception as error:
        return {
            "status": "error",
            "error_type": type(error).__name__,
            "message": str(error),
        }



# =========================================================
# WHATSAPP
# =========================================================


@app.post("/whatsapp")
async def whatsapp(
    request: Request,
    Body: str = Form(...),
):
    routed_response = route_message(
        Body
    )

    response = MessagingResponse()

    message = response.message()

    message.body(
        routed_response["body"]
    )

    if (
        routed_response["response_type"]
        == "media"
    ):
        relative_media_url = (
            routed_response[
                "relative_media_url"
            ]
        )

        base_url = str(
            request.base_url
        ).rstrip("/")

        public_media_url = (
            f"{base_url}"
            f"{relative_media_url}"
        )

        print(
            "Sending WhatsApp media URL:",
            public_media_url,
        )

        print("=" * 80)
        print("MEDIA URL")
        print(public_media_url)
        print("=" * 80)

        message.media(
            public_media_url
        )

        print(
            "Media added to Twilio response."
        )

    return PlainTextResponse(
        content=str(response),
        media_type="application/xml",
    )

@app.get("/store-builder-test")
def store_builder_test():

    data = load_auberry_workbook()

    store_dictionary = (
        build_store_dictionary(data)
    )

    return store_dictionary

@app.get("/channel-builder-test")
def channel_builder_test():
    """
    Test the client-specific restaurant channel hierarchy.

    This endpoint only:

    - loads the active client's workbook,
    - builds the channel dictionary,
    - returns the resulting hierarchy.

    It does not:

    - calculate sales,
    - call GPT,
    - modify WhatsApp routing,
    - execute any business report.
    """
    from services.semantics.builders.channel_builder import (
        build_channel_dictionary,
    )

    data = load_auberry_workbook()

    channel_dictionary = (
        build_channel_dictionary(
            data=data
        )
    )

    return channel_dictionary

@app.get("/product-builder-test")
def product_builder_test():
    """
    Test the active client's Category–Item hierarchy.

    This endpoint only:

    - loads the Auberry workbook,
    - builds the product dictionary,
    - returns categories and their mapped items.

    It does not:

    - call GPT,
    - calculate sales or quantity,
    - modify WhatsApp routing,
    - execute any report.
    """
    from services.semantics.builders.product_builder import (
        build_product_dictionary,
    )

    data = load_auberry_workbook()

    product_dictionary = (
        build_product_dictionary(
            data=data
        )
    )

    return product_dictionary

@app.get("/sales-columns-test")
def sales_columns_test():
    """
    Show the exact sales columns required before building
    the generic RAL execution engine.
    """
    data = load_auberry_workbook()

    sales = data["sales"]

    return {
        "columns": sales.columns.tolist(),
    }

@app.get("/ral-filter-test")
def ral_filter_test(
    message: str = (
        "How many cupcakes were sold last month "
        "at AMB Mall?"
    ),
):
    """
    Test the complete RestaurantAI execution flow.

    Natural Language
        ↓
    RAL
        ↓
    Deterministic Filters
        ↓
    Metric Calculation
    """
    import services.semantics.vocabulary.metrics as metrics

    print("=" * 80)
    print("METRICS FILE LOADED FROM:")
    print(metrics.__file__)
    print("=" * 80)

    print("HAS calculate_metric ?")
    print(hasattr(metrics, "calculate_metric"))

    print("AVAILABLE NAMES:")
    print([x for x in dir(metrics) if x.startswith("calculate")])
    print("=" * 80)

    from services.filter_engine import (
        apply_ral_filters,
    )
    from services.semantics.intent_parser import (
        parse_ral_request,
    )

    data = load_auberry_workbook()

    ral_request = parse_ral_request(
        user_message=message
    )

    filtered_sales = apply_ral_filters(
        data=data,
        ral_request=ral_request,
    )

    metric_value = metrics.calculate_metric(
        metric_name=ral_request["metric"],
        filtered_df=filtered_sales,
    )

    return {
        "ral": ral_request,
        "matching_rows": len(
            filtered_sales
        ),
        "metric_name": ral_request["metric"],
        "metric_value": metric_value,
        "sample_rows": (
            filtered_sales[
                [
                    "Date",
                    "Restaurant",
                    "Area",
                    "Item Name",
                    "Category",
                    "Qty",
                    "Sub Total",
                ]
            ]
            .head(10)
            .to_dict(
                orient="records"
            )
        ),
    }

@app.get("/metrics-debug")
def metrics_debug():

    import services.semantics.vocabulary.metrics as metrics

    return {
        "module_file": metrics.__file__,
        "has_calculate_metric": hasattr(
            metrics,
            "calculate_metric",
        ),
        "calculate_functions": [
            name
            for name in dir(metrics)
            if name.startswith("calculate")
        ],
    }

@app.get("/ral-group-test")
def ral_group_test(
    message: str = (
        "Store-wise sales last month"
    ),
):
    """
    Test the complete RestaurantAI grouped execution flow.

    Natural Language
        ↓
    RAL
        ↓
    Deterministic Filters
        ↓
    Grouping Engine
        ↓
    Metric Calculation per Group
    """
    from services.filter_engine import (
        apply_ral_filters,
    )
    from services.grouping_engine import (
        calculate_grouped_metric,
    )
    from services.semantics.intent_parser import (
        parse_ral_request,
    )

    data = load_auberry_workbook()

    ral_request = parse_ral_request(
        user_message=message
    )

    filtered_sales = apply_ral_filters(
        data=data,
        ral_request=ral_request,
    )

    grouped_result = calculate_grouped_metric(
        filtered_sales=filtered_sales,
        data=data,
        ral_request=ral_request,
    )

    return {
        "ral": ral_request,
        "filtered_rows": len(
            filtered_sales
        ),
        "grouped_result": (
            grouped_result
        ),
    }

@app.get("/ral-trend-test")
def ral_trend_test(
    message: str = (
        "Daily sales trend this month"
    ),
):
    """
    Test the complete RestaurantAI trend execution flow.

    Natural Language
        ↓
    RAL
        ↓
    Deterministic Filters
        ↓
    Trend Engine
        ↓
    Optional Grouping
        ↓
    Metric Engine
    """
    from services.filter_engine import (
        apply_ral_filters,
    )
    from services.semantics.intent_parser import (
        parse_ral_request,
    )
    from services.trend_engine import (
        calculate_trend,
    )

    data = load_auberry_workbook()

    ral_request = parse_ral_request(
        user_message=message
    )

    filtered_sales = apply_ral_filters(
        data=data,
        ral_request=ral_request,
    )

    trend_result = calculate_trend(
        filtered_sales=filtered_sales,
        data=data,
        ral_request=ral_request,
    )

    return {
        "ral": ral_request,

        "filtered_rows": len(
            filtered_sales
        ),

        "trend_result": (
            trend_result
        ),
    }

@app.get("/ral-chart-test")
def ral_chart_test(
    message: str = (
        "Plot daily sales trend this month"
    ),
):
    """
    Test RestaurantAI visual presentation pipeline.

    Supports:

        Trend -> Line Chart

        Grouping -> Bar Chart

        Trend + Grouping -> Chart
    """
    from services.presentation.chart_engine import (
        render_chart,
    )
    from services.filter_engine import (
        apply_ral_filters,
    )
    from services.grouping_engine import (
        calculate_grouped_metric,
    )
    from services.semantics.intent_parser import (
        parse_ral_request,
    )
    from services.presentation.presentation_engine import (
        present_result,
    )
    from services.trend_engine import (
        calculate_trend,
    )

    data = load_auberry_workbook()

    ral_request = parse_ral_request(
        user_message=message
    )

    filtered_sales = apply_ral_filters(
        data=data,
        ral_request=ral_request,
    )

    # =====================================================
    # TREND
    # =====================================================

    if (
        ral_request[
            "trend"
        ][
            "enabled"
        ]
    ):

        analytics_result = (
            calculate_trend(
                filtered_sales=filtered_sales,
                data=data,
                ral_request=ral_request,
            )
        )

        result_type = "trend"

    # =====================================================
    # GROUPING
    # =====================================================

    elif (
        ral_request[
            "grouping"
        ][
            "enabled"
        ]
    ):

        analytics_result = (
            calculate_grouped_metric(
                filtered_sales=filtered_sales,
                data=data,
                ral_request=ral_request,
            )
        )

        result_type = "grouped"

    else:

        return {
            "status": "unsupported",
            "message": (
                "This chart test currently requires "
                "a grouped or trend request."
            ),
            "ral": ral_request,
        }

    presentation_result = (
        present_result(
            result=analytics_result,
            result_type=result_type,
            ral_request=ral_request,
        )
    )

    if (
        presentation_result[
            "mode"
        ]
        != "chart"
    ):

        return {
            "ral": ral_request,
            "presentation": (
                presentation_result
            ),
        }

    chart_spec = (
        presentation_result[
            "chart_spec"
        ]
    )

    chart_path = (
        render_chart(
            chart_spec=chart_spec,
            file_name=(
                "ral_chart_test.png"
            ),
        )
    )

    return {
        "ral": ral_request,

        "filtered_rows": len(
            filtered_sales
        ),

        "result_type": (
            result_type
        ),

        "analytics_result": (
            analytics_result
        ),

        "chart_spec": (
            chart_spec
        ),

        "chart_file": str(
            chart_path
        ),
    }