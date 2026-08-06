import re
from typing import Any, Final

import pandas as pd


# =========================================================
# DEFAULT DATA LOCATION
# =========================================================

DEFAULT_SALES_SHEET_KEY: Final[str] = "sales"
DEFAULT_CHANNEL_COLUMN: Final[str] = "Area"


# =========================================================
# CANONICAL RESTAURANT CHANNELS
# =========================================================

CHANNEL_DELIVERY: Final[str] = "Delivery"
CHANNEL_DINE_IN: Final[str] = "Dine In"
CHANNEL_TAKE_AWAY: Final[str] = "Take Away"
CHANNEL_OTHERS: Final[str] = "Others"


DEFAULT_AGGREGATORS: Final[tuple[str, ...]] = (
    "Swiggy",
    "Zomato",
)


DELIVERY_ALIASES: Final[tuple[str, ...]] = (
    "delivery",
    "online delivery",
    "online business",
    "online sales",
    "delivery business",
    "delivery sales",
    "food delivery",
    "home delivery",
    "aggregator business",
    "aggregator sales",
)


DINE_IN_ALIASES: Final[tuple[str, ...]] = (
    "dine in",
    "dine-in",
    "dinein",
    "dining",
    "restaurant dining",
    "in store",
    "in-store",
    "walk in",
    "walk-in",
    "walkin",
)


TAKE_AWAY_ALIASES: Final[tuple[str, ...]] = (
    "take away",
    "take-away",
    "takeaway",
    "pick up",
    "pick-up",
    "pickup",
    "self pickup",
    "self pick up",
    "self pick-up",
    "parcel",
    "counter pickup",
)


# =========================================================
# TEXT HELPERS
# =========================================================


def _clean_text(
    value: Any,
) -> str:
    """
    Convert a value into clean display text.
    """
    if pd.isna(value):
        return ""

    return " ".join(
        str(value).strip().split()
    )


def _normalize_alias(
    value: str,
) -> str:
    """
    Normalize text for exact deterministic matching.

    Examples:

        "Swiggy"       -> "swiggy"
        " Dine   In "  -> "dine in"
        "Take-Away"    -> "take-away"
    """
    return " ".join(
        str(value).strip().lower().split()
    )


def _normalize_search_text(
    value: str,
) -> str:
    """
    Normalize punctuation and separators for contains-based
    aggregator matching.

    Examples:

        "Swiggy_DONUT EXPRESS BY AUB"
            -> "swiggy donut express by aub"

        "Zomato-Auberry - The Bake Shop"
            -> "zomato auberry the bake shop"

        "SWIGGY"
            -> "swiggy"

    This makes matching independent of underscores, hyphens
    and other separators used by POS systems.
    """
    normalized_value = re.sub(
        r"[^a-z0-9]+",
        " ",
        str(value).strip().lower(),
    )

    return " ".join(
        normalized_value.split()
    )


def _contains_business_term(
    text: str,
    business_term: str,
) -> bool:
    """
    Check whether a normalized business term occurs as a
    complete word or phrase inside normalized text.

    This avoids accidental partial matches.

    Example:

        term = "swiggy"
        text = "swiggy donut express by aub"
        -> True
    """
    normalized_text = _normalize_search_text(
        text
    )

    normalized_term = _normalize_search_text(
        business_term
    )

    if (
        not normalized_text
        or not normalized_term
    ):
        return False

    padded_text = (
        f" {normalized_text} "
    )

    padded_term = (
        f" {normalized_term} "
    )

    return padded_term in padded_text


def _add_unique_alias(
    aliases: list[str],
    alias: str,
) -> None:
    """
    Add an alias only when its normalized form does not
    already exist.
    """
    cleaned_alias = _clean_text(
        alias
    )

    if not cleaned_alias:
        return

    normalized_alias = _normalize_alias(
        cleaned_alias
    )

    normalized_existing = {
        _normalize_alias(
            existing_alias
        )
        for existing_alias in aliases
    }

    if (
        normalized_alias
        not in normalized_existing
    ):
        aliases.append(
            cleaned_alias
        )


# =========================================================
# EMPTY CHANNEL STRUCTURE
# =========================================================


def _create_channel_definition(
    canonical_name: str,
    aliases: tuple[str, ...] = (),
) -> dict:
    """
    Create a standard canonical channel definition.
    """
    channel_definition = {
        "canonical_name": canonical_name,
        "aliases": [],
        "aggregators": {},
        "raw_values": [],
    }

    _add_unique_alias(
        channel_definition["aliases"],
        canonical_name,
    )

    for alias in aliases:
        _add_unique_alias(
            channel_definition["aliases"],
            alias,
        )

    return channel_definition


def _create_base_channel_dictionary() -> dict[str, dict]:
    """
    Create the universal restaurant channel hierarchy.

    Delivery is a parent channel whose members may include
    Swiggy, Zomato and future online aggregators.
    """
    return {
        CHANNEL_DELIVERY: (
            _create_channel_definition(
                canonical_name=CHANNEL_DELIVERY,
                aliases=DELIVERY_ALIASES,
            )
        ),
        CHANNEL_DINE_IN: (
            _create_channel_definition(
                canonical_name=CHANNEL_DINE_IN,
                aliases=DINE_IN_ALIASES,
            )
        ),
        CHANNEL_TAKE_AWAY: (
            _create_channel_definition(
                canonical_name=CHANNEL_TAKE_AWAY,
                aliases=TAKE_AWAY_ALIASES,
            )
        ),
        CHANNEL_OTHERS: (
            _create_channel_definition(
                canonical_name=CHANNEL_OTHERS,
                aliases=(
                    "other",
                    "others",
                    "other channels",
                ),
            )
        ),
    }


# =========================================================
# AGGREGATOR HELPERS
# =========================================================


def _build_aggregator_lookup(
    aggregator_names: list[str],
) -> dict[str, str]:
    """
    Build a normalized aggregator-to-canonical-name lookup.

    Example:

        "swiggy" -> "Swiggy"
        "zomato" -> "Zomato"
    """
    aggregator_lookup: dict[
        str,
        str,
    ] = {}

    for aggregator_name in aggregator_names:
        cleaned_name = _clean_text(
            aggregator_name
        )

        if not cleaned_name:
            continue

        aggregator_lookup[
            _normalize_alias(
                cleaned_name
            )
        ] = cleaned_name

    return aggregator_lookup


def _find_matching_aggregator(
    raw_channel: str,
    aggregator_lookup: dict[str, str],
) -> str | None:
    """
    Identify whether a raw POS value belongs to a configured
    aggregator.

    Matching order:

    1. Exact normalized match
    2. Contains-based word or phrase match

    Examples:

        "Swiggy"
            -> "Swiggy"

        "Swiggy_DONUT EXPRESS BY AUB"
            -> "Swiggy"

        "Zomato_Auberry - The Bake Shop"
            -> "Zomato"

    Returns None when no configured aggregator is found.
    """
    normalized_raw = _normalize_alias(
        raw_channel
    )

    exact_match = aggregator_lookup.get(
        normalized_raw
    )

    if exact_match is not None:
        return exact_match

    for (
        normalized_aggregator,
        canonical_aggregator,
    ) in aggregator_lookup.items():
        if _contains_business_term(
            text=raw_channel,
            business_term=(
                normalized_aggregator
            ),
        ):
            return canonical_aggregator

    return None


def _add_aggregator(
    channel_dictionary: dict[str, dict],
    aggregator_name: str,
    raw_value: str,
) -> None:
    """
    Add an aggregator under the Delivery parent channel.
    """
    delivery_definition = channel_dictionary[
        CHANNEL_DELIVERY
    ]

    aggregators = delivery_definition[
        "aggregators"
    ]

    if aggregator_name not in aggregators:
        aggregators[
            aggregator_name
        ] = {
            "canonical_name": aggregator_name,
            "aliases": [],
            "raw_values": [],
        }

    aggregator_definition = aggregators[
        aggregator_name
    ]

    _add_unique_alias(
        aggregator_definition["aliases"],
        aggregator_name,
    )

    _add_unique_alias(
        aggregator_definition["aliases"],
        raw_value,
    )

    _add_unique_alias(
        aggregator_definition["raw_values"],
        raw_value,
    )

    _add_unique_alias(
        delivery_definition["raw_values"],
        raw_value,
    )


# =========================================================
# CHANNEL CLASSIFICATION
# =========================================================


def _classify_raw_channel(
    raw_channel: str,
    aggregator_lookup: dict[str, str],
    additional_mapping: dict[str, str],
) -> tuple[str, str | None]:
    """
    Classify one raw channel value.

    Returns:

        (
            canonical_parent_channel,
            canonical_aggregator_or_none,
        )

    Examples:

        Swiggy
        -> ("Delivery", "Swiggy")

        Swiggy_DONUT EXPRESS BY AUB
        -> ("Delivery", "Swiggy")

        Zomato_Auberry - The Bake Shop
        -> ("Delivery", "Zomato")

        Take Away
        -> ("Take Away", None)

        Walk In
        -> ("Dine In", None)
    """
    normalized_raw = _normalize_alias(
        raw_channel
    )

    matching_aggregator = (
        _find_matching_aggregator(
            raw_channel=raw_channel,
            aggregator_lookup=(
                aggregator_lookup
            ),
        )
    )

    if matching_aggregator is not None:
        return (
            CHANNEL_DELIVERY,
            matching_aggregator,
        )

    normalized_delivery_aliases = {
        _normalize_alias(alias)
        for alias in DELIVERY_ALIASES
    }

    if normalized_raw in normalized_delivery_aliases:
        return (
            CHANNEL_DELIVERY,
            None,
        )

    normalized_dine_in_aliases = {
        _normalize_alias(alias)
        for alias in DINE_IN_ALIASES
    }

    if normalized_raw in normalized_dine_in_aliases:
        return (
            CHANNEL_DINE_IN,
            None,
        )

    normalized_take_away_aliases = {
        _normalize_alias(alias)
        for alias in TAKE_AWAY_ALIASES
    }

    if normalized_raw in normalized_take_away_aliases:
        return (
            CHANNEL_TAKE_AWAY,
            None,
        )

    if normalized_raw in additional_mapping:
        mapped_value = additional_mapping[
            normalized_raw
        ]

        if mapped_value in {
            CHANNEL_DELIVERY,
            CHANNEL_DINE_IN,
            CHANNEL_TAKE_AWAY,
            CHANNEL_OTHERS,
        }:
            return (
                mapped_value,
                None,
            )

        # Any mapped value other than a parent channel is
        # treated as an aggregator under Delivery.
        return (
            CHANNEL_DELIVERY,
            mapped_value,
        )

    return (
        CHANNEL_OTHERS,
        None,
    )


# =========================================================
# MAIN CHANNEL BUILDER
# =========================================================


def build_channel_dictionary(
    data: dict,
    sheet_key: str = DEFAULT_SALES_SHEET_KEY,
    channel_column: str = DEFAULT_CHANNEL_COLUMN,
    aggregator_names: list[str] | None = None,
    additional_mapping: dict[str, str] | None = None,
) -> dict[str, dict]:
    """
    Build a restaurant-aware client channel dictionary.

    Restaurant hierarchy:

        Delivery
            ├── Swiggy
            ├── Zomato
            └── Future aggregators

        Dine In

        Take Away

        Others

    Aggregator identification supports both:

    - exact raw values such as "Swiggy",
    - embedded POS values such as
      "Swiggy_DONUT EXPRESS BY AUB".

    Parameters
    ----------
    data:
        Loaded client workbook data.

    sheet_key:
        Key containing the sales DataFrame.

    channel_column:
        Raw order-source/channel column.

    aggregator_names:
        Valid online food aggregators for the client.

        Defaults to:

            Swiggy
            Zomato

        A future client may pass:

            [
                "Swiggy",
                "Zomato",
                "ONDC",
                "Uber Eats",
            ]

    additional_mapping:
        Optional normalized business mapping.

        Examples:

            {
                "counter sale": "Take Away",
                "restaurant": "Dine In",
                "ondc": "ONDC",
                "magicpin": "Magicpin",
            }

        When the mapped value is not one of the parent channels,
        it is treated as an aggregator under Delivery.

    This function does not:

    - calculate channel sales,
    - calculate transactions,
    - call GPT,
    - route WhatsApp messages,
    - contain Auberry store or item names.
    """
    if sheet_key not in data:
        raise ValueError(
            f"Sales sheet was not found: "
            f"{sheet_key}"
        )

    sales = data[
        sheet_key
    ].copy()

    sales.columns = (
        sales.columns
        .astype(str)
        .str.strip()
    )

    if channel_column not in sales.columns:
        raise ValueError(
            "Sales data is missing the channel column: "
            f"{channel_column}"
        )

    active_aggregators = (
        list(DEFAULT_AGGREGATORS)
        if aggregator_names is None
        else list(aggregator_names)
    )

    aggregator_lookup = (
        _build_aggregator_lookup(
            active_aggregators
        )
    )

    normalized_additional_mapping: dict[
        str,
        str,
    ] = {}

    if additional_mapping:
        for (
            raw_value,
            mapped_value,
        ) in additional_mapping.items():
            cleaned_mapped_value = (
                _clean_text(
                    mapped_value
                )
            )

            if not cleaned_mapped_value:
                continue

            normalized_additional_mapping[
                _normalize_alias(
                    raw_value
                )
            ] = cleaned_mapped_value

    channel_dictionary = (
        _create_base_channel_dictionary()
    )

    raw_channel_values = (
        sales[channel_column]
        .dropna()
        .map(_clean_text)
    )

    raw_channel_values = (
        raw_channel_values[
            raw_channel_values.ne("")
        ]
        .drop_duplicates()
        .tolist()
    )

    for raw_channel in raw_channel_values:
        (
            parent_channel,
            aggregator_name,
        ) = _classify_raw_channel(
            raw_channel=raw_channel,
            aggregator_lookup=(
                aggregator_lookup
            ),
            additional_mapping=(
                normalized_additional_mapping
            ),
        )

        parent_definition = (
            channel_dictionary[
                parent_channel
            ]
        )

        _add_unique_alias(
            parent_definition["raw_values"],
            raw_channel,
        )

        if aggregator_name is not None:
            _add_aggregator(
                channel_dictionary=(
                    channel_dictionary
                ),
                aggregator_name=(
                    aggregator_name
                ),
                raw_value=raw_channel,
            )

    return channel_dictionary


# =========================================================
# CHANNEL LOOKUP HELPERS
# =========================================================


def get_canonical_channel_names(
    channel_dictionary: dict[
        str,
        dict,
    ],
) -> list[str]:
    """
    Return canonical parent channel names.

    Expected parent channels:

        Delivery
        Dine In
        Take Away
        Others
    """
    return sorted(
        channel_dictionary.keys(),
        key=str.lower,
    )


def get_aggregator_names(
    channel_dictionary: dict[
        str,
        dict,
    ],
) -> list[str]:
    """
    Return aggregators found under the Delivery channel.

    Example:

        [
            "Swiggy",
            "Zomato",
        ]
    """
    delivery_definition = (
        channel_dictionary.get(
            CHANNEL_DELIVERY,
            {},
        )
    )

    aggregators = (
        delivery_definition.get(
            "aggregators",
            {},
        )
    )

    return sorted(
        aggregators.keys(),
        key=str.lower,
    )


def get_channel_alias_map(
    channel_dictionary: dict[
        str,
        dict,
    ],
) -> dict[str, str]:
    """
    Return an alias-to-parent-channel map.

    Examples:

        "online delivery" -> "Delivery"
        "swiggy"           -> "Delivery"
        "pickup"           -> "Take Away"
        "walk in"          -> "Dine In"
    """
    alias_map: dict[
        str,
        str,
    ] = {}

    for (
        canonical_channel,
        channel_definition,
    ) in channel_dictionary.items():
        aliases = channel_definition.get(
            "aliases",
            [],
        )

        raw_values = channel_definition.get(
            "raw_values",
            [],
        )

        for alias in (
            list(aliases)
            + list(raw_values)
        ):
            normalized_alias = (
                _normalize_alias(
                    alias
                )
            )

            if normalized_alias:
                alias_map[
                    normalized_alias
                ] = canonical_channel

        aggregators = channel_definition.get(
            "aggregators",
            {},
        )

        for aggregator_definition in (
            aggregators.values()
        ):
            aggregator_aliases = (
                aggregator_definition.get(
                    "aliases",
                    [],
                )
            )

            aggregator_raw_values = (
                aggregator_definition.get(
                    "raw_values",
                    [],
                )
            )

            for alias in (
                list(aggregator_aliases)
                + list(aggregator_raw_values)
            ):
                normalized_alias = (
                    _normalize_alias(
                        alias
                    )
                )

                if normalized_alias:
                    alias_map[
                        normalized_alias
                    ] = canonical_channel

    return alias_map


def get_aggregator_alias_map(
    channel_dictionary: dict[
        str,
        dict,
    ],
) -> dict[str, str]:
    """
    Return an alias-to-canonical-aggregator map.

    Examples:

        "swiggy" -> "Swiggy"
        "swiggy_donut express by aub" -> "Swiggy"
        "zomato" -> "Zomato"
    """
    alias_map: dict[
        str,
        str,
    ] = {}

    delivery_definition = (
        channel_dictionary.get(
            CHANNEL_DELIVERY,
            {},
        )
    )

    aggregators = (
        delivery_definition.get(
            "aggregators",
            {},
        )
    )

    for (
        canonical_aggregator,
        aggregator_definition,
    ) in aggregators.items():
        aliases = aggregator_definition.get(
            "aliases",
            [],
        )

        raw_values = aggregator_definition.get(
            "raw_values",
            [],
        )

        for alias in (
            list(aliases)
            + list(raw_values)
        ):
            normalized_alias = (
                _normalize_alias(
                    alias
                )
            )

            if normalized_alias:
                alias_map[
                    normalized_alias
                ] = canonical_aggregator

    return alias_map


def resolve_channel_name(
    requested_channel: str,
    channel_dictionary: dict[
        str,
        dict,
    ],
) -> str | None:
    """
    Resolve a user expression to its parent channel.

    Examples:

        "Delivery" -> "Delivery"
        "Online"   -> "Delivery"
        "Swiggy"   -> "Delivery"
        "Pickup"   -> "Take Away"
    """
    normalized_request = (
        _normalize_alias(
            requested_channel
        )
    )

    if not normalized_request:
        return None

    alias_map = get_channel_alias_map(
        channel_dictionary
    )

    exact_result = alias_map.get(
        normalized_request
    )

    if exact_result is not None:
        return exact_result

    matching_aggregator = (
        _find_matching_aggregator(
            raw_channel=requested_channel,
            aggregator_lookup=(
                get_aggregator_alias_map(
                    channel_dictionary
                )
            ),
        )
    )

    if matching_aggregator is not None:
        return CHANNEL_DELIVERY

    return None


def resolve_aggregator_name(
    requested_aggregator: str,
    channel_dictionary: dict[
        str,
        dict,
    ],
) -> str | None:
    """
    Resolve an aggregator expression independently.

    Examples:

        "Swiggy" -> "Swiggy"
        "Swiggy_DONUT EXPRESS BY AUB" -> "Swiggy"
        "Zomato" -> "Zomato"

    Returns None for general Delivery requests.
    """
    normalized_request = (
        _normalize_alias(
            requested_aggregator
        )
    )

    if not normalized_request:
        return None

    alias_map = get_aggregator_alias_map(
        channel_dictionary
    )

    exact_result = alias_map.get(
        normalized_request
    )

    if exact_result is not None:
        return exact_result

    return _find_matching_aggregator(
        raw_channel=requested_aggregator,
        aggregator_lookup=alias_map,
    )


# =========================================================
# GPT VOCABULARY PROMPT
# =========================================================


def build_channel_vocabulary_prompt(
    channel_dictionary: dict[
        str,
        dict,
    ],
) -> str:
    """
    Build restaurant-aware channel context for GPT.

    Important semantic rules:

    - Delivery is a parent channel.
    - Swiggy and Zomato are aggregators within Delivery.
    - A general Delivery request includes all aggregators.
    - An aggregator-specific request identifies both:
        parent channel = Delivery
        aggregator = Swiggy/Zomato
    - Aggregator-wise means a breakdown of Delivery by
      individual aggregators.
    """
    prompt_lines = [
        "Restaurant sales channel hierarchy:",
        "",
    ]

    canonical_channels = (
        get_canonical_channel_names(
            channel_dictionary
        )
    )

    for canonical_channel in canonical_channels:
        channel_definition = (
            channel_dictionary[
                canonical_channel
            ]
        )

        aliases = channel_definition.get(
            "aliases",
            [],
        )

        prompt_lines.append(
            (
                "- Canonical parent channel: "
                f"{canonical_channel}"
            )
        )

        if aliases:
            prompt_lines.append(
                (
                    "  Common expressions: "
                    + ", ".join(
                        aliases
                    )
                )
            )

        aggregators = channel_definition.get(
            "aggregators",
            {},
        )

        if aggregators:
            prompt_lines.append(
                "  Aggregators within this channel:"
            )

            for aggregator_name in sorted(
                aggregators.keys(),
                key=str.lower,
            ):
                aggregator_definition = (
                    aggregators[
                        aggregator_name
                    ]
                )

                aggregator_aliases = (
                    aggregator_definition.get(
                        "aliases",
                        [],
                    )
                )

                prompt_lines.append(
                    (
                        "    - Canonical aggregator: "
                        f"{aggregator_name}"
                    )
                )

                if aggregator_aliases:
                    prompt_lines.append(
                        (
                            "      Known names: "
                            + ", ".join(
                                aggregator_aliases
                            )
                        )
                    )

    prompt_lines.extend(
        [
            "",
            "Restaurant business interpretation rules:",
            (
                "- Delivery or online delivery means the "
                "combined business of all aggregators."
            ),
            (
                "- Swiggy and Zomato are aggregators under "
                "the Delivery parent channel."
            ),
            (
                "- A Swiggy request means Delivery filtered "
                "to aggregator Swiggy."
            ),
            (
                "- A Zomato request means Delivery filtered "
                "to aggregator Zomato."
            ),
            (
                "- Aggregator-wise means separately report "
                "each aggregator within Delivery."
            ),
            (
                "- Take Away includes takeaway, take-away, "
                "pickup, pick-up and parcel expressions."
            ),
            (
                "- Dine In includes dine-in, dining and "
                "walk-in expressions."
            ),
            (
                "- Never treat Swiggy or Zomato as separate "
                "parent channels."
            ),
            (
                "- Never silently treat a specific aggregator "
                "request as total Delivery."
            ),
        ]
    )

    return "\n".join(
        prompt_lines
    )