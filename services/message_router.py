import re
import shutil
from pathlib import Path
from uuid import uuid4

from services.data_loader import (
    load_auberry_workbook,
)
from services.formatter import (
    format_yesterday_sales_report,
)
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


# =========================================================
# EXISTING FIXED-COMMAND PATTERNS
# =========================================================

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


# =========================================================
# COMMON HELPERS
# =========================================================


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
        day_number = int(
            day_text
        )

    except ValueError:
        return cleaned_date

    return (
        f"{day_number:02d}-"
        f"{month_text.title()}-"
        f"{year_text}"
    )


def _build_text_response(
    body: str,
) -> dict:
    """
    Build one standard WhatsApp text response.
    """
    return {
        "response_type": "text",
        "body": str(body),
    }


def _build_media_response(
    body: str,
    relative_media_url: str,
) -> dict:
    """
    Build one standard WhatsApp media response.

    main.py already converts relative_media_url into the
    public Railway/local URL used by Twilio.
    """
    return {
        "response_type": "media",
        "body": str(body),
        "relative_media_url": str(
            relative_media_url
        ),
    }


def _publish_chart_for_whatsapp(
    chart_path: Path,
) -> str:
    """
    Copy a generated chart into the existing /static mount so
    Twilio can retrieve it through a public URL.

    Chart Engine owns rendering.
    Message Router owns delivery preparation.

    A unique filename is used so WhatsApp/Twilio cannot show
    a stale cached image from an earlier request.
    """
    source_path = Path(
        chart_path
    )

    if not source_path.exists():
        raise FileNotFoundError(
            "Generated chart file was not found: "
            f"{source_path}"
        )

    project_root = (
        Path(__file__)
        .resolve()
        .parent
        .parent
    )

    static_reports_directory = (
        project_root
        / "static"
        / "reports"
    )

    static_reports_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    public_file_name = (
        f"restaurantai_chart_"
        f"{uuid4().hex}.png"
    )

    public_file_path = (
        static_reports_directory
        / public_file_name
    )

    shutil.copy2(
        source_path,
        public_file_path,
    )

    return (
        f"/static/reports/"
        f"{public_file_name}"
    )


def _build_chart_caption(
    chart_spec: dict,
) -> str:
    """
    Build the short text that accompanies a WhatsApp chart.
    """
    title = str(
        chart_spec.get(
            "title",
            "RestaurantAI",
        )
    ).strip()

    subtitle = str(
        chart_spec.get(
            "subtitle",
            "",
        )
    ).strip()

    if subtitle:
        return (
            f"📊 {title}\n"
            f"{subtitle}"
        )

    return (
        f"📊 {title}"
    )


# =========================================================
# EXISTING CAPABILITY 1: YESTERDAY SALES
# =========================================================


def _run_yesterday_sales() -> dict:
    """
    Run the existing deterministic Yesterday Sales engine.

    Both the fixed command and compatible natural-language
    requests may continue to use this stable capability.
    """
    data = load_auberry_workbook()

    report = get_yesterday_sales_report(
        data
    )

    return _build_text_response(
        format_yesterday_sales_report(
            report
        )
    )


# =========================================================
# GENERIC RAL EXECUTION
# =========================================================


def _ral_is_ready_for_execution(
    ral_request: dict,
) -> bool:
    """
    Decide whether a RAL request is safe for the generic
    deterministic execution flow.

    The generic flow currently supports:

    - one metric,
    - one resolved date period,
    - stores,
    - channels,
    - aggregators,
    - categories,
    - items,
    - single or multi-dimensional grouping,
    - daily / weekly / monthly trends,
    - text presentation,
    - line-chart presentation,
    - bar-chart presentation.

    It does not yet execute:

    - unresolved time periods,
    - comparisons through the generic RAL path,
    - clarification-dependent requests,
    - region filters.
    """
    if not isinstance(
        ral_request,
        dict,
    ):
        return False

    if ral_request.get(
        "needs_clarification",
        False,
    ):
        return False

    clarification_question = (
        ral_request.get(
            "clarification_question"
        )
    )

    if clarification_question:
        return False

    time_value = ral_request.get(
        "time",
        {},
    )

    if not isinstance(
        time_value,
        dict,
    ):
        return False

    start_date = time_value.get(
        "start_date"
    )

    end_date = time_value.get(
        "end_date"
    )

    if not isinstance(
        start_date,
        str,
    ):
        return False

    if not isinstance(
        end_date,
        str,
    ):
        return False

    comparison = ral_request.get(
        "comparison",
        {},
    )

    if (
        isinstance(
            comparison,
            dict,
        )
        and comparison.get(
            "enabled",
            False,
        )
    ):
        return False

    if ral_request.get(
        "regions",
        [],
    ):
        return False

    metric_name = ral_request.get(
        "metric"
    )

    if not isinstance(
        metric_name,
        str,
    ):
        return False

    if not metric_name.strip():
        return False

    return True


def _build_clarification_response(
    ral_request: dict,
) -> dict | None:
    """
    Return GPT's clarification question when RAL explicitly
    requires clarification.
    """
    if not ral_request.get(
        "needs_clarification",
        False,
    ):
        return None

    clarification_question = (
        ral_request.get(
            "clarification_question"
        )
    )

    if not clarification_question:
        return None

    return _build_text_response(
        clarification_question
    )


def _try_selection_execution(
    user_message: str,
) -> dict | None:
    """
    Execute top-one / bottom-one "which / what / when"
    questions without disturbing ordinary RAL execution.

    Architecture:

        Natural language
            ↓
        Existing RAL parser
            ↓
        Selection detector
            ↓
        Time default/selection preparation
            ↓
        Existing Filter Engine
            ↓
        Existing Grouping OR Trend Engine
            ↓
        Selection Engine picks max/min
            ↓
        WhatsApp text

    This keeps all existing filter/business rules reusable.
    """
    try:
        from services.filter_engine import (
            apply_ral_filters,
        )
        from services.intent_parser import (
            parse_ral_request,
        )
        from services.selection_engine import (
            detect_selection_plan,
            execute_selection,
            format_selection_result,
            prepare_selection_ral,
        )

        # First use the same language-understanding layer that
        # already understands Store/Channel/Category/Item
        # filters. Selection does not create another LLM parser.
        ral_request = parse_ral_request(
            user_message=user_message
        )

        plan = detect_selection_plan(
            user_message=user_message,
            ral_request=ral_request,
        )

        if plan is None:
            return None

        (
            prepared_ral,
            time_meta,
        ) = prepare_selection_ral(
            user_message=user_message,
            ral_request=ral_request,
        )

        print(
            "Selection plan:",
            plan,
        )

        print(
            "Selection RAL:",
            prepared_ral,
        )

        # Preserve any genuine ambiguity that Selection did not
        # deterministically resolve (for example product ambiguity).
        clarification_response = (
            _build_clarification_response(
                prepared_ral
            )
        )

        if clarification_response is not None:
            return clarification_response

        time_value = prepared_ral.get(
            "time",
            {},
        )

        if (
            not isinstance(
                time_value,
                dict,
            )
            or not time_value.get(
                "start_date"
            )
            or not time_value.get(
                "end_date"
            )
        ):
            return _build_text_response(
                "I understood the ranking question, but the "
                "time period is still unclear. Please specify "
                "a date or period."
            )

        data = load_auberry_workbook()

        filtered_sales = apply_ral_filters(
            data=data,
            ral_request=prepared_ral,
        )

        if len(filtered_sales) == 0:
            return _build_text_response(
                "I could not find any matching sales records "
                "for that combination, so I have not treated "
                "the result as zero."
            )

        selection_result = execute_selection(
            filtered_sales=filtered_sales,
            data=data,
            ral_request=prepared_ral,
            plan=plan,
            time_meta=time_meta,
        )

        print(
            "Selection result:",
            selection_result,
        )

        return _build_text_response(
            format_selection_result(
                selection_result
            )
        )

    except ValueError as error:
        print(
            "Selection validation/execution error:",
            repr(error),
        )

        return _build_text_response(
            str(error)
        )

    except Exception as error:
        print(
            "Selection execution error:",
            repr(error),
        )

        return _build_text_response(
            "I understood the ranking question, but the result "
            "could not be generated safely. Please try again."
        )


def _try_generic_ral_execution(
    user_message: str,
) -> dict | None:
    """
    Execute the generic RestaurantAI pipeline.

        Natural language
            ↓
        RAL
            ↓
        Deterministic filters
            ↓
        One of:
            - Metric Engine
            - Grouping Engine
            - Trend Engine
            ↓
        Presentation Engine
            ↓
        One of:
            - WhatsApp text
            - Chart Engine -> PNG -> WhatsApp media

    Stable fixed commands are still handled before this
    function by route_message().
    """
    try:
        from services.chart_engine import (
            render_chart,
        )
        from services.filter_engine import (
            apply_ral_filters,
        )
        from services.formatter import (
            format_ral_metric_reply,
        )
        from services.grouping_engine import (
            calculate_grouped_metric,
        )
        from services.intent_parser import (
            parse_ral_request,
        )
        from services.presentation_engine import (
            present_result,
        )
        from services.pivot_table_image import (
            generate_grouped_pivot_image,
        )
        from services.trend_engine import (
            calculate_trend,
        )
        from services.vocabulary.metrics import (
            calculate_metric,
        )

        # =================================================
        # 1. UNDERSTAND
        # =================================================

        ral_request = parse_ral_request(
            user_message=user_message
        )

        print(
            "Generic RAL request:",
            ral_request,
        )

        clarification_response = (
            _build_clarification_response(
                ral_request
            )
        )

        if clarification_response is not None:
            return clarification_response

        if not _ral_is_ready_for_execution(
            ral_request
        ):
            return None

        # =================================================
        # 2. FILTER
        # =================================================

        data = load_auberry_workbook()

        filtered_sales = apply_ral_filters(
            data=data,
            ral_request=ral_request,
        )

        print(
            "Generic RAL filtered rows:",
            len(
                filtered_sales
            ),
        )

        # Important business guardrail:
        # no matching rows must not silently become "0".
        if len(filtered_sales) == 0:
            return _build_text_response(
                "I could not find any matching sales records "
                "for that combination, so I have not treated "
                "the result as zero."
            )

        trend = ral_request.get(
            "trend",
            {},
        )

        grouping = ral_request.get(
            "grouping",
            {},
        )

        trend_enabled = bool(
            isinstance(
                trend,
                dict,
            )
            and trend.get(
                "enabled",
                False,
            )
        )

        grouping_enabled = bool(
            isinstance(
                grouping,
                dict,
            )
            and grouping.get(
                "enabled",
                False,
            )
        )

        # =================================================
        # 3A. TREND EXECUTION
        # =================================================

        if trend_enabled:
            analytics_result = (
                calculate_trend(
                    filtered_sales=filtered_sales,
                    data=data,
                    ral_request=ral_request,
                )
            )

            presentation_result = (
                present_result(
                    result=analytics_result,
                    result_type="trend",
                    ral_request=ral_request,
                )
            )

            print(
                "Generic RAL trend result:",
                {
                    "metric": analytics_result.get(
                        "metric"
                    ),
                    "grain": analytics_result.get(
                        "grain"
                    ),
                    "point_count": analytics_result.get(
                        "point_count"
                    ),
                    "grouping_enabled": (
                        analytics_result.get(
                            "grouping_enabled"
                        )
                    ),
                },
            )

            if (
                presentation_result.get(
                    "mode"
                )
                == "text"
            ):
                return _build_text_response(
                    presentation_result.get(
                        "text",
                        "",
                    )
                )

            if (
                presentation_result.get(
                    "mode"
                )
                == "chart"
            ):
                chart_spec = (
                    presentation_result[
                        "chart_spec"
                    ]
                )

                chart_file_name = (
                    f"restaurantai_"
                    f"{uuid4().hex}.png"
                )

                chart_path = render_chart(
                    chart_spec=chart_spec,
                    file_name=chart_file_name,
                )

                relative_media_url = (
                    _publish_chart_for_whatsapp(
                        chart_path
                    )
                )

                return _build_media_response(
                    body=_build_chart_caption(
                        chart_spec
                    ),
                    relative_media_url=(
                        relative_media_url
                    ),
                )

            raise ValueError(
                "Trend presentation returned an "
                "unsupported mode."
            )

        # =================================================
        # 3B. GROUPED EXECUTION
        # =================================================

        if grouping_enabled:
            analytics_result = (
                calculate_grouped_metric(
                    filtered_sales=filtered_sales,
                    data=data,
                    ral_request=ral_request,
                )
            )

            print(
                "Generic RAL grouped result:",
                {
                    "metric": analytics_result.get(
                        "metric"
                    ),
                    "grouping_dimensions": (
                        analytics_result.get(
                            "grouping_dimensions"
                        )
                    ),
                    "row_count": analytics_result.get(
                        "row_count"
                    ),
                },
            )

            presentation_result = (
                present_result(
                    result=analytics_result,
                    result_type="grouped",
                    ral_request=ral_request,
                )
            )

            presentation_mode = (
                presentation_result.get(
                    "mode"
                )
            )

            if presentation_mode == "text":
                return _build_text_response(
                    presentation_result.get(
                        "text",
                        "",
                    )
                )

            if presentation_mode == "chart":
                chart_spec = (
                    presentation_result[
                        "chart_spec"
                    ]
                )

                chart_file_name = (
                    f"restaurantai_"
                    f"{uuid4().hex}.png"
                )

                chart_path = render_chart(
                    chart_spec=chart_spec,
                    file_name=chart_file_name,
                )

                relative_media_url = (
                    _publish_chart_for_whatsapp(
                        chart_path
                    )
                )

                return _build_media_response(
                    body=_build_chart_caption(
                        chart_spec
                    ),
                    relative_media_url=(
                        relative_media_url
                    ),
                )

            if presentation_mode == "pivot_table":
                pivot_spec = (
                    presentation_result[
                        "pivot_spec"
                    ]
                )

                pivot_file_name = (
                    f"restaurantai_pivot_"
                    f"{uuid4().hex}.png"
                )

                pivot_result = (
                    generate_grouped_pivot_image(
                        pivot_spec=pivot_spec,
                        file_name=(
                            pivot_file_name
                        ),
                    )
                )

                relative_media_url = (
                    _publish_chart_for_whatsapp(
                        Path(
                            pivot_result[
                                "file_path"
                            ]
                        )
                    )
                )

                title = str(
                    pivot_spec.get(
                        "title",
                        "RestaurantAI Analysis",
                    )
                )

                subtitle = str(
                    pivot_spec.get(
                        "subtitle",
                        "",
                    )
                )

                body = (
                    f"📊 {title}"
                )

                if subtitle:
                    body += (
                        f"\n{subtitle}"
                    )

                return _build_media_response(
                    body=body,
                    relative_media_url=(
                        relative_media_url
                    ),
                )

            raise ValueError(
                "Grouped presentation returned an "
                "unsupported mode."
            )

        # =================================================
        # 3C. SINGLE METRIC EXECUTION
        # =================================================

        metric_value = calculate_metric(
            metric_name=ral_request[
                "metric"
            ],
            filtered_df=filtered_sales,
        )

        reply_text = format_ral_metric_reply(
            ral_request=ral_request,
            metric_value=metric_value,
        )

        print(
            "Generic RAL metric result:",
            {
                "metric": ral_request[
                    "metric"
                ],
                "matching_rows": len(
                    filtered_sales
                ),
                "metric_value": metric_value,
            },
        )

        return _build_text_response(
            reply_text
        )

    except ValueError as error:
        print(
            "Generic RAL validation/execution error:",
            repr(error),
        )

        return _build_text_response(
            str(error)
        )

    except Exception as error:
        print(
            "Generic RAL execution error:",
            repr(error),
        )

        return _build_text_response(
            "I understood the request, but the result "
            "could not be generated safely. Please try again."
        )


# =========================================================
# MAIN WHATSAPP ROUTER
# =========================================================


def route_message(
    message: str,
) -> dict:
    """
    Route a WhatsApp message.

    Routing order:

    1. Stable existing deterministic commands.
    2. Generic RAL execution.
    3. Specific invalid-command guidance.
    4. Unsupported-request message.
    """
    normalized_message = " ".join(
        str(message).strip().split()
    )

    normalized_lower = (
        normalized_message.lower()
    )

    if not normalized_message:
        return _build_text_response(
            "Please send a restaurant business question."
        )

    yesterday_commands = {
        "yesterday sales",
        "yesterdays sales",
        "yesterday sale",
    }

    # =====================================================
    # CAPABILITY 1: YESTERDAY SALES
    # STABLE EXISTING COMMAND
    # =====================================================

    if normalized_lower in yesterday_commands:
        return _run_yesterday_sales()

    # =====================================================
    # CAPABILITY 2: SALES FOR A PERIOD
    # STABLE EXISTING COMMAND
    # =====================================================

    sales_period_match = (
        SALES_PERIOD_PATTERN.match(
            normalized_message
        )
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
            report = (
                get_store_performance_report(
                    data=data,
                    start_date_text=(
                        start_date_text
                    ),
                    end_date_text=(
                        end_date_text
                    ),
                )
            )

            image_result = (
                generate_sales_for_a_period_image(
                    report
                )
            )

        except ValueError as error:
            return _build_text_response(
                str(error)
            )

        except Exception as error:
            print(
                "Sales-for-period report error:",
                repr(error),
            )

            return _build_text_response(
                "The sales report could not be generated. "
                "Please try again."
            )

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
                image_result[
                    "relative_url"
                ]
            ),
        }

    # =====================================================
    # CAPABILITY 3: KPI PERIOD COMPARISON
    # STABLE EXISTING COMMAND
    # =====================================================

    comparison_match = (
        COMPARISON_PATTERN.match(
            normalized_message
        )
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
            return _build_text_response(
                str(error)
            )

        except Exception as error:
            print(
                "KPI comparison report error:",
                repr(error),
            )

            return _build_text_response(
                "The comparison report could not "
                "be generated. Please try again."
            )

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
                image_result[
                    "relative_url"
                ]
            ),
        }

    # =====================================================
    # SELECTION / EXTREME CAPABILITY
    # =====================================================

    selection_response = (
        _try_selection_execution(
            user_message=normalized_message
        )
    )

    if selection_response is not None:
        return selection_response

    # =====================================================
    # GENERIC RAL EXECUTION
    # =====================================================

    generic_response = (
        _try_generic_ral_execution(
            user_message=normalized_message
        )
    )

    if generic_response is not None:
        return generic_response

    # =====================================================
    # INVALID FIXED-COMMAND GUIDANCE
    # =====================================================

    if normalized_lower.startswith(
        "compare"
    ):
        return _build_text_response(
            "This comparison could not yet be executed.\n\n"
            "For the existing comparison report, use:\n\n"
            "Compare DD-Mmm-YYYY DD-Mmm-YYYY "
            "DD-Mmm-YYYY DD-Mmm-YYYY\n\n"
            "Example:\n"
            "Compare 01-Apr-2025 30-Jun-2025 "
            "01-Apr-2026 30-Jun-2026"
        )

    if normalized_lower.startswith(
        "sales from"
    ):
        return _build_text_response(
            "Please use the sales-period command "
            "in this format:\n\n"
            "Sales from DD-Mmm-YYYY "
            "to DD-Mmm-YYYY\n\n"
            "Example:\n"
            "Sales from 01-Jul-2026 "
            "to 14-Jul-2026"
        )

    # =====================================================
    # CURRENTLY UNSUPPORTED REQUEST
    # =====================================================

    return _build_text_response(
        "I understood your message, but I could not safely "
        "execute it yet.\n\n"
        "You can ask questions using combinations of:\n\n"
        "• Sales, Quantity, Transactions, ADS, ADT or APT\n"
        "• A supported date or period\n"
        "• Store\n"
        "• Channel or Aggregator\n"
        "• Category\n"
        "• Item"
    )