from typing import Final

import pandas as pd

from services.builders.channel_builder import (
    CHANNEL_DELIVERY,
    build_channel_dictionary,
)
from services.builders.product_builder import (
    build_product_dictionary,
)
from services.builders.store_builder import (
    build_store_dictionary,
)
from services.vocabulary.metrics import (
    METRIC_ADS,
    METRIC_ADT,
    METRIC_APT,
    METRIC_QUANTITY,
    METRIC_SALES,
    METRIC_TRANSACTIONS,
    calculate_metric,
)


# =========================================================
# SOURCE COLUMNS
# =========================================================

DATE_COLUMN: Final[str] = "Date"
SOURCE_STORE_COLUMN: Final[str] = "Restaurant"
CHANNEL_COLUMN: Final[str] = "Area"
CATEGORY_COLUMN: Final[str] = "Category"
ITEM_COLUMN: Final[str] = "Item Name"


# =========================================================
# SUPPORTED GROUPING DIMENSIONS
# =========================================================

GROUP_STORE: Final[str] = "store"
GROUP_CHANNEL: Final[str] = "channel"
GROUP_AGGREGATOR: Final[str] = "aggregator"
GROUP_CATEGORY: Final[str] = "category"
GROUP_ITEM: Final[str] = "item"


SUPPORTED_GROUPING_DIMENSIONS: Final[set[str]] = {
    GROUP_STORE,
    GROUP_CHANNEL,
    GROUP_AGGREGATOR,
    GROUP_CATEGORY,
    GROUP_ITEM,
}


# =========================================================
# INTERNAL GROUP COLUMN NAMES
# =========================================================

GROUP_COLUMN_MAP: Final[dict[str, str]] = {
    GROUP_STORE: "__group_store",
    GROUP_CHANNEL: "__group_channel",
    GROUP_AGGREGATOR: "__group_aggregator",
    GROUP_CATEGORY: "__group_category",
    GROUP_ITEM: "__group_item",
}


# =========================================================
# TEXT HELPERS
# =========================================================


def _clean_text(
    value,
) -> str:
    if pd.isna(value):
        return ""

    return " ".join(
        str(value)
        .strip()
        .split()
    )


def _normalize_text(
    value,
) -> str:
    return _clean_text(
        value
    ).lower()


# =========================================================
# STORE CANONICALIZATION
# =========================================================


def _build_raw_store_to_canonical_map(
    data: dict,
) -> dict[str, str]:
    """
    Build:

        raw Restaurant name
            ->
        canonical short store name
    """
    store_dictionary = (
        build_store_dictionary(
            data=data
        )
    )

    raw_to_canonical: dict[str, str] = {}

    for (
        canonical_name,
        store_definition,
    ) in store_dictionary.items():

        canonical_clean = (
            _clean_text(
                canonical_name
            )
        )

        raw_to_canonical[
            _normalize_text(
                canonical_name
            )
        ] = canonical_clean

        for alias in store_definition.get(
            "aliases",
            [],
        ):
            raw_to_canonical[
                _normalize_text(
                    alias
                )
            ] = canonical_clean

    return raw_to_canonical


def _add_store_group_column(
    sales: pd.DataFrame,
    data: dict,
) -> pd.DataFrame:

    working_sales = sales.copy()

    raw_to_canonical = (
        _build_raw_store_to_canonical_map(
            data=data
        )
    )

    working_sales[
        GROUP_COLUMN_MAP[
            GROUP_STORE
        ]
    ] = (
        working_sales[
            SOURCE_STORE_COLUMN
        ]
        .map(
            lambda value: (
                raw_to_canonical.get(
                    _normalize_text(
                        value
                    ),
                    _clean_text(
                        value
                    ),
                )
            )
        )
    )

    return working_sales


# =========================================================
# CHANNEL / AGGREGATOR CANONICALIZATION
# =========================================================


def _build_raw_area_maps(
    data: dict,
) -> tuple[
    dict[str, str],
    dict[str, str],
]:
    """
    Build:

        raw Area
            ->
        canonical Channel

    and:

        raw Area
            ->
        canonical Aggregator
    """
    channel_dictionary = (
        build_channel_dictionary(
            data=data
        )
    )

    raw_to_channel: dict[str, str] = {}

    raw_to_aggregator: dict[str, str] = {}

    for (
        channel_name,
        channel_definition,
    ) in channel_dictionary.items():

        canonical_channel = (
            _clean_text(
                channel_name
            )
        )

        for raw_value in (
            channel_definition.get(
                "raw_values",
                [],
            )
        ):

            normalized_raw = (
                _normalize_text(
                    raw_value
                )
            )

            raw_to_channel[
                normalized_raw
            ] = canonical_channel

        aggregators = (
            channel_definition.get(
                "aggregators",
                {},
            )
        )

        for (
            aggregator_name,
            aggregator_definition,
        ) in aggregators.items():

            canonical_aggregator = (
                _clean_text(
                    aggregator_name
                )
            )

            for raw_value in (
                aggregator_definition.get(
                    "raw_values",
                    [],
                )
            ):

                normalized_raw = (
                    _normalize_text(
                        raw_value
                    )
                )

                raw_to_channel[
                    normalized_raw
                ] = CHANNEL_DELIVERY

                raw_to_aggregator[
                    normalized_raw
                ] = canonical_aggregator

    return (
        raw_to_channel,
        raw_to_aggregator,
    )


def _add_channel_group_column(
    sales: pd.DataFrame,
    data: dict,
) -> pd.DataFrame:

    working_sales = sales.copy()

    (
        raw_to_channel,
        _,
    ) = _build_raw_area_maps(
        data=data
    )

    working_sales[
        GROUP_COLUMN_MAP[
            GROUP_CHANNEL
        ]
    ] = (
        working_sales[
            CHANNEL_COLUMN
        ]
        .map(
            lambda value: (
                raw_to_channel.get(
                    _normalize_text(
                        value
                    ),
                    _clean_text(
                        value
                    ),
                )
            )
        )
    )

    return working_sales


def _add_aggregator_group_column(
    sales: pd.DataFrame,
    data: dict,
) -> pd.DataFrame:

    working_sales = sales.copy()

    (
        _,
        raw_to_aggregator,
    ) = _build_raw_area_maps(
        data=data
    )

    working_sales[
        GROUP_COLUMN_MAP[
            GROUP_AGGREGATOR
        ]
    ] = (
        working_sales[
            CHANNEL_COLUMN
        ]
        .map(
            lambda value: (
                raw_to_aggregator.get(
                    _normalize_text(
                        value
                    ),
                    "",
                )
            )
        )
    )

    return working_sales


# =========================================================
# CATEGORY / ITEM CANONICALIZATION
# =========================================================


def _build_item_maps(
    data: dict,
) -> tuple[
    dict[str, str],
    dict[str, str],
]:
    """
    Build:

        raw / alias / canonical item
            ->
        canonical item

    and:

        raw / alias / canonical item
            ->
        canonical category
    """
    product_dictionary = (
        build_product_dictionary(
            data=data
        )
    )

    item_to_canonical: dict[str, str] = {}

    item_to_category: dict[str, str] = {}

    for (
        category_name,
        category_definition,
    ) in product_dictionary.items():

        canonical_category = (
            _clean_text(
                category_name
            )
        )

        items = (
            category_definition.get(
                "items",
                {},
            )
        )

        for (
            item_name,
            item_definition,
        ) in items.items():

            canonical_item = (
                _clean_text(
                    item_name
                )
            )

            all_names = {
                canonical_item,
            }

            all_names.update(
                item_definition.get(
                    "raw_names",
                    [],
                )
            )

            all_names.update(
                item_definition.get(
                    "aliases",
                    [],
                )
            )

            for name in all_names:

                normalized_name = (
                    _normalize_text(
                        name
                    )
                )

                item_to_canonical[
                    normalized_name
                ] = canonical_item

                item_to_category[
                    normalized_name
                ] = canonical_category

    return (
        item_to_canonical,
        item_to_category,
    )


def _add_category_group_column(
    sales: pd.DataFrame,
    data: dict,
) -> pd.DataFrame:
    """
    Resolve canonical category using Product Builder first.

    Fall back to the physical Category column only when
    Product Builder cannot resolve the item.
    """
    working_sales = sales.copy()

    (
        _,
        item_to_category,
    ) = _build_item_maps(
        data=data
    )

    def resolve_category(
        row,
    ) -> str:

        item_name = (
            _normalize_text(
                row[
                    ITEM_COLUMN
                ]
            )
        )

        canonical_category = (
            item_to_category.get(
                item_name
            )
        )

        if canonical_category:
            return canonical_category

        return _clean_text(
            row[
                CATEGORY_COLUMN
            ]
        )

    working_sales[
        GROUP_COLUMN_MAP[
            GROUP_CATEGORY
        ]
    ] = working_sales.apply(
        resolve_category,
        axis=1,
    )

    return working_sales


def _add_item_group_column(
    sales: pd.DataFrame,
    data: dict,
) -> pd.DataFrame:

    working_sales = sales.copy()

    (
        item_to_canonical,
        _,
    ) = _build_item_maps(
        data=data
    )

    working_sales[
        GROUP_COLUMN_MAP[
            GROUP_ITEM
        ]
    ] = (
        working_sales[
            ITEM_COLUMN
        ]
        .map(
            lambda value: (
                item_to_canonical.get(
                    _normalize_text(
                        value
                    ),
                    _clean_text(
                        value
                    ),
                )
            )
        )
    )

    return working_sales


# =========================================================
# SINGLE GROUP COLUMN PREPARATION
# =========================================================


def _prepare_group_column(
    sales: pd.DataFrame,
    data: dict,
    grouping_dimension: str,
) -> tuple[
    pd.DataFrame,
    str,
]:

    normalized_dimension = (
        str(
            grouping_dimension
        )
        .strip()
        .lower()
    )

    if (
        normalized_dimension
        not in SUPPORTED_GROUPING_DIMENSIONS
    ):
        raise ValueError(
            "Unsupported grouping dimension: "
            f"{grouping_dimension}"
        )

    if normalized_dimension == GROUP_STORE:

        working_sales = (
            _add_store_group_column(
                sales=sales,
                data=data,
            )
        )

    elif normalized_dimension == GROUP_CHANNEL:

        working_sales = (
            _add_channel_group_column(
                sales=sales,
                data=data,
            )
        )

    elif normalized_dimension == GROUP_AGGREGATOR:

        working_sales = (
            _add_aggregator_group_column(
                sales=sales,
                data=data,
            )
        )

    elif normalized_dimension == GROUP_CATEGORY:

        working_sales = (
            _add_category_group_column(
                sales=sales,
                data=data,
            )
        )

    elif normalized_dimension == GROUP_ITEM:

        working_sales = (
            _add_item_group_column(
                sales=sales,
                data=data,
            )
        )

    else:
        raise ValueError(
            "Unsupported grouping dimension."
        )

    return (
        working_sales,
        GROUP_COLUMN_MAP[
            normalized_dimension
        ],
    )


# =========================================================
# MULTI-DIMENSION GROUP PREPARATION
# =========================================================


def _prepare_group_columns(
    sales: pd.DataFrame,
    data: dict,
    grouping_dimensions: list[str],
) -> tuple[
    pd.DataFrame,
    list[str],
]:
    """
    Prepare all requested grouping dimensions.

    Example:

        ["store", "channel"]

    becomes internal columns:

        [
            "__group_store",
            "__group_channel",
        ]

    The same logic works for one or many dimensions.
    """
    if not grouping_dimensions:
        raise ValueError(
            "At least one grouping dimension is required."
        )

    normalized_dimensions = [
        str(
            dimension
        )
        .strip()
        .lower()
        for dimension in grouping_dimensions
    ]

    if (
        len(
            normalized_dimensions
        )
        != len(
            set(
                normalized_dimensions
            )
        )
    ):
        raise ValueError(
            "Grouping dimensions cannot contain duplicates."
        )

    working_sales = (
        sales.copy()
    )

    group_columns: list[str] = []

    for dimension in (
        normalized_dimensions
    ):

        (
            working_sales,
            group_column,
        ) = _prepare_group_column(
            sales=working_sales,
            data=data,
            grouping_dimension=dimension,
        )

        group_columns.append(
            group_column
        )

    return (
        working_sales,
        group_columns,
    )


# =========================================================
# GROUP CLEANING
# =========================================================


def _clean_group_columns(
    sales: pd.DataFrame,
    group_columns: list[str],
) -> pd.DataFrame:
    """
    Clean grouping labels and remove rows that cannot be
    assigned to every requested grouping dimension.

    This is especially important for aggregator grouping,
    because non-aggregator rows have a blank aggregator.
    """
    working_sales = (
        sales.copy()
    )

    for group_column in (
        group_columns
    ):

        working_sales[
            group_column
        ] = (
            working_sales[
                group_column
            ]
            .fillna("")
            .map(
                _clean_text
            )
        )

        working_sales = (
            working_sales.loc[
                working_sales[
                    group_column
                ]
                != ""
            ]
            .copy()
        )

    return working_sales


# =========================================================
# METRIC EXECUTION
# =========================================================


def _calculate_group_metric(
    group_df: pd.DataFrame,
    metric_name: str,
) -> float:
    """
    Delegate metric calculation to the existing universal
    Metric Engine.

    Grouping Engine never duplicates metric formulas.
    """
    metric_value = (
        calculate_metric(
            metric_name=metric_name,
            filtered_df=group_df,
        )
    )

    return float(
        metric_value
    )


# =========================================================
# GROUP LABEL BUILDING
# =========================================================


def _build_group_values(
    grouping_dimensions: list[str],
    group_key,
) -> dict[str, str]:
    """
    Convert a pandas group key into clean structured
    RestaurantAI grouping values.

    Handles both pandas behaviours:

    Single dimension:
        "AMB Mall"

    or:
        ("AMB Mall",)

    Multiple dimensions:
        ("AMB Mall", "Dine In")
    """

    if len(grouping_dimensions) == 1:

        # Pandas may return either:
        #
        #     "AMB Mall"
        #
        # or:
        #
        #     ("AMB Mall",)
        #
        # depending on how groupby was called / pandas version.
        #
        # Always unwrap a one-value tuple.

        if isinstance(
            group_key,
            tuple,
        ):
            if len(group_key) != 1:
                raise ValueError(
                    "Single-dimensional grouping returned "
                    "an unexpected multi-value group key."
                )

            group_values = [
                group_key[0]
            ]

        else:
            group_values = [
                group_key
            ]

    else:

        if not isinstance(
            group_key,
            tuple,
        ):
            raise ValueError(
                "Multi-dimensional grouping returned "
                "an invalid group key."
            )

        if (
            len(group_key)
            != len(grouping_dimensions)
        ):
            raise ValueError(
                "Grouping key count does not match "
                "the requested grouping dimensions."
            )

        group_values = list(
            group_key
        )

    return {
        dimension: _clean_text(
            value
        )
        for (
            dimension,
            value,
        ) in zip(
            grouping_dimensions,
            group_values,
        )
    }


# =========================================================
# PUBLIC GROUPING ENGINE
# =========================================================


def calculate_grouped_metric(
    filtered_sales: pd.DataFrame,
    data: dict,
    ral_request: dict,
) -> dict:
    """
    Execute a grouped RestaurantAI metric.

    Supports one or multiple grouping dimensions.

    Examples:

        Store-wise sales

        Channel-wise transactions

        Category-wise quantity

        Store-wise channel-wise sales

        Store-wise category-wise quantity

        Category-wise item-wise sales

        Store-wise aggregator-wise transactions
    """

    # =====================================================
    # RAL GROUPING
    # =====================================================

    grouping = ral_request.get(
        "grouping",
        {},
    )

    if not grouping.get(
        "enabled",
        False,
    ):
        raise ValueError(
            "Grouping is not enabled in this RAL request."
        )

    grouping_dimensions = (
        grouping.get(
            "dimensions",
            [],
        )
    )

    if not isinstance(
        grouping_dimensions,
        list,
    ):
        raise ValueError(
            "Grouping dimensions must be a list."
        )

    if not grouping_dimensions:
        raise ValueError(
            "At least one grouping dimension is required."
        )

    normalized_dimensions = [
        str(
            dimension
        )
        .strip()
        .lower()
        for dimension
        in grouping_dimensions
    ]

    for dimension in (
        normalized_dimensions
    ):

        if (
            dimension
            not in SUPPORTED_GROUPING_DIMENSIONS
        ):
            raise ValueError(
                "Unsupported grouping dimension: "
                f"{dimension}"
            )

    # =====================================================
    # METRIC
    # =====================================================

    metric_name = (
        str(
            ral_request.get(
                "metric",
                ""
            )
        )
        .strip()
        .lower()
    )

    if metric_name not in {
        METRIC_SALES,
        METRIC_QUANTITY,
        METRIC_TRANSACTIONS,
        METRIC_ADS,
        METRIC_ADT,
        METRIC_APT,
    }:
        raise ValueError(
            "Unsupported grouped metric: "
            f"{metric_name}"
        )

    # =====================================================
    # PREPARE CANONICAL GROUPING COLUMNS
    # =====================================================

    (
        working_sales,
        group_columns,
    ) = _prepare_group_columns(
        sales=filtered_sales,
        data=data,
        grouping_dimensions=(
            normalized_dimensions
        ),
    )

    working_sales = (
        _clean_group_columns(
            sales=working_sales,
            group_columns=group_columns,
        )
    )

    # =====================================================
    # EXECUTE GROUPING
    # =====================================================

    result_rows: list[dict] = []

    grouped_data = (
        working_sales.groupby(
            group_columns,
            sort=False,
            dropna=False,
        )
    )

    for (
        group_key,
        group_df,
    ) in grouped_data:

        groups = (
            _build_group_values(
                grouping_dimensions=(
                    normalized_dimensions
                ),
                group_key=group_key,
            )
        )

        metric_value = (
            _calculate_group_metric(
                group_df=group_df,
                metric_name=metric_name,
            )
        )

        result_row = {
            "groups": groups,
            "metric_value": (
                metric_value
            ),
            "matching_rows": (
                len(
                    group_df
                )
            ),
        }

        # ---------------------------------------------
        # Backward-friendly field for single grouping
        # ---------------------------------------------

        if (
            len(
                normalized_dimensions
            )
            == 1
        ):

            single_dimension = (
                normalized_dimensions[
                    0
                ]
            )

            result_row[
                "group"
            ] = groups[
                single_dimension
            ]

        result_rows.append(
            result_row
        )

    # =====================================================
    # SORT
    # =====================================================

    result_rows.sort(
        key=lambda row: (
            row[
                "metric_value"
            ]
        ),
        reverse=True,
    )

    # =====================================================
    # RESULT
    # =====================================================

    result = {
        "metric": metric_name,

        "grouping_dimensions": (
            normalized_dimensions
        ),

        "row_count": len(
            result_rows
        ),

        "rows": (
            result_rows
        ),
    }

    # Keep old field for single-dimension debugging
    # so our existing tests remain readable.

    if (
        len(
            normalized_dimensions
        )
        == 1
    ):

        result[
            "grouping_dimension"
        ] = (
            normalized_dimensions[
                0
            ]
        )

    return result