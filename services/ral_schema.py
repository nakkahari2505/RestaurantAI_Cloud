from typing import Any

from services.vocabulary.metrics import (
    METRIC_SALES,
    SUPPORTED_METRICS,
)
from services.vocabulary.time import (
    SUPPORTED_TIME_TYPES,
    TIME_UNSPECIFIED,
)


RAL_VERSION = "1.0"


SUPPORTED_INTENTS = {
    "sales",
    "compare",
    "unsupported",
}


RAL_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "ral_version": {
            "type": "string",
            "enum": [
                RAL_VERSION,
            ],
        },
        "intent": {
            "type": "string",
            "enum": sorted(
                SUPPORTED_INTENTS
            ),
        },
        "metric": {
            "type": "string",
            "enum": sorted(
                SUPPORTED_METRICS
            ),
        },
        "time": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": sorted(
                        SUPPORTED_TIME_TYPES
                    ),
                },
                "start_date": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "end_date": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
            },
            "required": [
                "type",
                "start_date",
                "end_date",
            ],
            "additionalProperties": False,
        },
        "stores": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "regions": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "channels": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "aggregators": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "categories": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "items": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "comparison": {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                },
                "from_start_date": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "from_end_date": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "to_start_date": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "to_end_date": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
            },
            "required": [
                "enabled",
                "from_start_date",
                "from_end_date",
                "to_start_date",
                "to_end_date",
            ],
            "additionalProperties": False,
        },
        "understood_request": {
            "type": "string",
        },
        "needs_clarification": {
            "type": "boolean",
        },
        "clarification_question": {
            "type": [
                "string",
                "null",
            ],
        },
    },
    "required": [
        "ral_version",
        "intent",
        "metric",
        "time",
        "stores",
        "regions",
        "channels",
        "aggregators",
        "categories",
        "items",
        "comparison",
        "understood_request",
        "needs_clarification",
        "clarification_question",
    ],
    "additionalProperties": False,
}


def create_empty_ral_request() -> dict[str, Any]:
    """
    Return a safe empty RAL request.

    This is used when:
    - the user message is empty,
    - intent extraction fails safely,
    - a request is currently unsupported.
    """
    return {
        "ral_version": RAL_VERSION,
        "intent": "unsupported",
        "metric": METRIC_SALES,
        "time": {
            "type": TIME_UNSPECIFIED,
            "start_date": None,
            "end_date": None,
        },
        "stores": [],
        "regions": [],
        "channels": [],
        "aggregators": [],
        "categories": [],
        "items": [],
        "comparison": {
            "enabled": False,
            "from_start_date": None,
            "from_end_date": None,
            "to_start_date": None,
            "to_end_date": None,
        },
        "understood_request": (
            "The request could not be interpreted."
        ),
        "needs_clarification": False,
        "clarification_question": None,
    }


def validate_ral_request(
    ral_request: dict[str, Any],
) -> None:
    """
    Perform deterministic validation of a RAL request.

    GPT proposes the RAL request.
    Python verifies its structure and allowed values.
    """
    if not isinstance(
        ral_request,
        dict,
    ):
        raise ValueError(
            "RAL request must be an object."
        )

    required_fields = {
        "ral_version",
        "intent",
        "metric",
        "time",
        "stores",
        "regions",
        "channels",
        "aggregators",
        "categories",
        "items",
        "comparison",
        "understood_request",
        "needs_clarification",
        "clarification_question",
    }

    received_fields = set(
        ral_request.keys()
    )

    missing_fields = (
        required_fields
        - received_fields
    )

    if missing_fields:
        raise ValueError(
            "RAL request is missing fields: "
            + ", ".join(
                sorted(missing_fields)
            )
        )

    unexpected_fields = (
        received_fields
        - required_fields
    )

    if unexpected_fields:
        raise ValueError(
            "RAL request contains unexpected fields: "
            + ", ".join(
                sorted(unexpected_fields)
            )
        )

    if (
        ral_request["ral_version"]
        != RAL_VERSION
    ):
        raise ValueError(
            "Unsupported RAL version."
        )

    if (
        ral_request["intent"]
        not in SUPPORTED_INTENTS
    ):
        raise ValueError(
            "Unsupported RAL intent."
        )

    if (
        ral_request["metric"]
        not in SUPPORTED_METRICS
    ):
        raise ValueError(
            "Unsupported RAL metric."
        )

    _validate_time(
        ral_request["time"]
    )

    _validate_string_list(
        ral_request["stores"],
        "stores",
    )

    _validate_string_list(
        ral_request["regions"],
        "regions",
    )

    _validate_string_list(
        ral_request["channels"],
        "channels",
    )

    _validate_string_list(
        ral_request["aggregators"],
        "aggregators",
    )

    _validate_string_list(
        ral_request["categories"],
        "categories",
    )

    _validate_string_list(
        ral_request["items"],
        "items",
    )

    _validate_comparison(
        ral_request["comparison"]
    )

    understood_request = ral_request[
        "understood_request"
    ]

    if not isinstance(
        understood_request,
        str,
    ):
        raise ValueError(
            "RAL understood_request must be text."
        )

    if not understood_request.strip():
        raise ValueError(
            "RAL understood_request cannot be empty."
        )

    needs_clarification = ral_request[
        "needs_clarification"
    ]

    if not isinstance(
        needs_clarification,
        bool,
    ):
        raise ValueError(
            "RAL needs_clarification must "
            "be true or false."
        )

    clarification_question = ral_request[
        "clarification_question"
    ]

    if (
        clarification_question is not None
        and not isinstance(
            clarification_question,
            str,
        )
    ):
        raise ValueError(
            "RAL clarification_question must "
            "be text or null."
        )

    if (
        needs_clarification
        and (
            clarification_question is None
            or not clarification_question.strip()
        )
    ):
        raise ValueError(
            "A clarification question is required "
            "when needs_clarification is true."
        )

    if (
        not needs_clarification
        and clarification_question is not None
    ):
        raise ValueError(
            "clarification_question must be null "
            "when needs_clarification is false."
        )


def _validate_time(
    time_value: Any,
) -> None:
    """
    Validate the RAL time object.
    """
    if not isinstance(
        time_value,
        dict,
    ):
        raise ValueError(
            "RAL time must be an object."
        )

    required_time_fields = {
        "type",
        "start_date",
        "end_date",
    }

    received_time_fields = set(
        time_value.keys()
    )

    if (
        received_time_fields
        != required_time_fields
    ):
        raise ValueError(
            "RAL time must contain exactly: "
            "type, start_date and end_date."
        )

    if (
        time_value["type"]
        not in SUPPORTED_TIME_TYPES
    ):
        raise ValueError(
            "Unsupported RAL time type."
        )

    for date_field in {
        "start_date",
        "end_date",
    }:
        date_value = time_value[
            date_field
        ]

        if (
            date_value is not None
            and not isinstance(
                date_value,
                str,
            )
        ):
            raise ValueError(
                f"RAL time {date_field} must "
                "be text or null."
            )


def _validate_string_list(
    field_value: Any,
    field_name: str,
) -> None:
    """
    Validate a RAL dimension list.
    """
    if not isinstance(
        field_value,
        list,
    ):
        raise ValueError(
            f"RAL {field_name} must be a list."
        )

    for item_value in field_value:
        if not isinstance(
            item_value,
            str,
        ):
            raise ValueError(
                f"Every RAL {field_name} value "
                "must be text."
            )

        if not item_value.strip():
            raise ValueError(
                f"RAL {field_name} cannot contain "
                "an empty value."
            )


def _validate_comparison(
    comparison_value: Any,
) -> None:
    """
    Validate the RAL comparison object.
    """
    if not isinstance(
        comparison_value,
        dict,
    ):
        raise ValueError(
            "RAL comparison must be an object."
        )

    required_comparison_fields = {
        "enabled",
        "from_start_date",
        "from_end_date",
        "to_start_date",
        "to_end_date",
    }

    received_comparison_fields = set(
        comparison_value.keys()
    )

    if (
        received_comparison_fields
        != required_comparison_fields
    ):
        raise ValueError(
            "RAL comparison must contain exactly: "
            "enabled, from_start_date, from_end_date, "
            "to_start_date and to_end_date."
        )

    if not isinstance(
        comparison_value["enabled"],
        bool,
    ):
        raise ValueError(
            "RAL comparison enabled must "
            "be true or false."
        )

    comparison_date_fields = {
        "from_start_date",
        "from_end_date",
        "to_start_date",
        "to_end_date",
    }

    for date_field in comparison_date_fields:
        date_value = comparison_value[
            date_field
        ]

        if (
            date_value is not None
            and not isinstance(
                date_value,
                str,
            )
        ):
            raise ValueError(
                f"RAL comparison {date_field} "
                "must be text or null."
            )