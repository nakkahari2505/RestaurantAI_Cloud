import json
from typing import Literal, TypedDict

from services.builders.channel_builder import (
    build_channel_dictionary,
    build_channel_vocabulary_prompt,
)
from services.builders.product_builder import (
    build_product_dictionary,
    build_product_vocabulary_prompt,
)
from services.builders.store_builder import (
    build_store_dictionary,
    build_store_vocabulary_prompt,
)
from services.data_loader import (
    load_auberry_workbook,
)
from services.llm_service import llm_service
from services.ral_schema import (
    RAL_JSON_SCHEMA,
    create_empty_ral_request,
    validate_ral_request,
)
from services.vocabulary.metrics import (
    METRIC_SALES,
    build_metric_vocabulary_prompt,
)
from services.vocabulary.time import (
    TIME_YESTERDAY,
    build_time_vocabulary_prompt,
    resolve_ral_time,
)


class IntentResult(TypedDict):
    """
    Temporary backward-compatible result expected by
    the current message_router.py.

    Internally, RestaurantAI now uses complete RAL.
    """

    capability: Literal[
        "yesterday_sales",
        "unsupported",
    ]

    understood_request: str


METRIC_VOCABULARY_PROMPT = (
    build_metric_vocabulary_prompt()
)

TIME_VOCABULARY_PROMPT = (
    build_time_vocabulary_prompt()
)


def _clean_message(
    user_message: str,
) -> str:
    """
    Normalize unnecessary spaces without changing
    the user's language or intended meaning.
    """
    return " ".join(
        str(user_message).strip().split()
    )


def _build_client_business_context() -> str:
    """
    Build the active client's business vocabulary from
    the client's own workbook.

    Current client-driven dimensions:

    - Stores
    - Channels
    - Aggregators
    - Categories
    - Items

    This context contains names and hierarchy only.

    It does not expose:

    - sales values,
    - quantities,
    - transaction values,
    - formulas,
    - analytics calculations.
    """
    data = load_auberry_workbook()

    store_dictionary = (
        build_store_dictionary(
            data=data
        )
    )

    channel_dictionary = (
        build_channel_dictionary(
            data=data
        )
    )

    product_dictionary = (
        build_product_dictionary(
            data=data
        )
    )

    store_context = (
        build_store_vocabulary_prompt(
            store_dictionary
        )
    )

    channel_context = (
        build_channel_vocabulary_prompt(
            channel_dictionary
        )
    )

    product_context = (
        build_product_vocabulary_prompt(
            product_dictionary
        )
    )

    return (
        f"{store_context}\n\n"
        f"{channel_context}\n\n"
        f"{product_context}"
    )


def _build_ral_instructions(
    client_business_context: str,
) -> str:
    """
    Build the complete RestaurantAI Language instructions.

    Universal business vocabulary is combined with the
    active client's dynamically built vocabulary.
    """
    return f"""
You are the language-understanding layer of RestaurantAI.

Your only responsibility is to translate a user's natural-
language business question into RestaurantAI Language,
called RAL.

You must never:

- calculate sales,
- calculate quantities,
- calculate transactions or KPIs,
- read or interpret business numbers,
- answer the business question,
- invent business results,
- silently remove requested filters,
- invent stores,
- invent regions,
- invent channels,
- invent aggregators,
- invent categories,
- invent items.

The deterministic Python business engine will calculate all
business numbers later.

=========================================================
SUPPORTED BUSINESS METRICS
=========================================================

{METRIC_VOCABULARY_PROMPT}

Canonical metric rules:

- sales means monetary sales value, revenue, turnover,
  business value or collections.

- quantity means the number of individual units or items sold.

- transactions means the number of bills, invoices,
  receipts or orders.

- ads means Average Daily Sales.

- adt means Average Daily Transactions.

- apt means Average Per Transaction, Average Bill Value,
  Average Transaction Value, Average Ticket Size, AOV or ATV.

Always return exactly one canonical metric from the
supported metric list.

Examples:

"What were yesterday's sales?"

metric = "sales"

"How many bills were made yesterday?"

metric = "transactions"

"How many donuts were sold yesterday?"

metric = "quantity"

"What was our average bill value yesterday?"

metric = "apt"

"What was ADS last month?"

metric = "ads"

"What was average daily bill count?"

metric = "adt"

=========================================================
SUPPORTED BUSINESS TIME TYPES
=========================================================

{TIME_VOCABULARY_PROMPT}

Canonical time rules:

1. Relative time expressions

For relative expressions, identify the correct canonical
time type.

Do not calculate the actual dates.

Python will deterministically resolve the dates after RAL
has been generated.

Examples:

"yesterday"

time.type = "yesterday"
time.start_date = null
time.end_date = null

"last week"

time.type = "last_week"
time.start_date = null
time.end_date = null

"this month"

time.type = "this_month"
time.start_date = null
time.end_date = null

"last quarter"

time.type = "last_quarter"
time.start_date = null
time.end_date = null

2. One explicit complete date

When the user clearly provides one complete calendar date,
use:

time.type = "specific_date"

Normalize the date into ISO format:

YYYY-MM-DD

Set start_date and end_date to the same date.

Example:

"Sales on 05-Jul-2026"

time.type = "specific_date"
time.start_date = "2026-07-05"
time.end_date = "2026-07-05"

3. Explicit complete date range

When the user clearly provides both a complete start date
and complete end date, use:

time.type = "date_range"

Normalize both dates into ISO format.

Example:

"Sales from 01-Jul-2026 to 14-Jul-2026"

time.type = "date_range"
time.start_date = "2026-07-01"
time.end_date = "2026-07-14"

4. Incomplete dates

Never invent a missing day, month or year.

Example:

"Sales on 5 July"

If the intended year is unclear:

time.type = "custom"
time.start_date = null
time.end_date = null
needs_clarification = true
clarification_question =
"Which year do you mean for 5 July?"

5. Complex business periods

Expressions such as:

- last Sunday
- this weekend
- last weekend
- same weekend last month
- last 7 days
- rolling 30 days
- first half of July
- breakfast
- lunch
- dinner
- current shift

must currently use:

time.type = "custom"

Do not invent dates.

Preserve the complete time meaning inside
understood_request.

6. Missing time

If the user does not provide a usable time period:

time.type = "unspecified"
time.start_date = null
time.end_date = null

=========================================================
ACTIVE CLIENT BUSINESS VOCABULARY
=========================================================

{client_business_context}

=========================================================
STORE RULES
=========================================================

1. When the user mentions a valid store or known alias,
return only its canonical store name in stores.

2. Multiple requested stores must all be preserved.

Example:

"AMB and Punjagutta sales yesterday"

stores = [
    "AMB Mall",
    "Punjagutta"
]

3. Never invent a store.

4. Never remove a store merely to make the request
executable.

5. If the wording appears to refer to a store but cannot be
resolved confidently:

- preserve the user's wording in stores,
- set intent = "unsupported",
- set needs_clarification = true,
- ask one short clarification question.

=========================================================
RESTAURANT CHANNEL AND AGGREGATOR RULES
=========================================================

The parent restaurant channels are:

- Delivery
- Dine In
- Take Away
- Others

Swiggy and Zomato are aggregators within Delivery.

A future aggregator must also belong under Delivery.

1. General Delivery request

Examples:

- delivery sales
- online delivery business
- online business
- home delivery

Return:

channels = ["Delivery"]
aggregators = []

This means the combined business of all delivery
aggregators.

2. Specific aggregator request

Example:

"Yesterday Swiggy sales"

Return:

channels = ["Delivery"]
aggregators = ["Swiggy"]

Never return Swiggy as a parent channel.

3. Zomato request

Return:

channels = ["Delivery"]
aggregators = ["Zomato"]

4. Multiple aggregators

Example:

"Swiggy and Zomato transactions yesterday"

Return:

channels = ["Delivery"]
aggregators = [
    "Swiggy",
    "Zomato"
]

5. Aggregator-wise request

Examples:

- aggregator-wise sales
- aggregator wise transactions
- split delivery by aggregator
- online platform-wise business

This means the user wants a separate breakdown of each
aggregator under Delivery.

Represent it as:

channels = ["Delivery"]
aggregators = []

Preserve "aggregator-wise breakdown" clearly inside
understood_request.

Do not select only one aggregator.

6. Take Away

Expressions such as:

- take away
- takeaway
- take-away
- pickup
- pick-up
- parcel

Return:

channels = ["Take Away"]
aggregators = []

7. Dine In

Expressions such as:

- dine in
- dine-in
- dining
- walk in
- walk-in

Return:

channels = ["Dine In"]
aggregators = []

8. Never silently convert a specific aggregator request into
total Delivery.

9. Never invent an aggregator that is absent from the active
client vocabulary.

10. If an aggregator cannot be identified confidently:

- preserve the user's wording in aggregators,
- set intent = "unsupported",
- set needs_clarification = true,
- ask one short clarification question.

=========================================================
CATEGORY AND ITEM RULES
=========================================================

The active client product vocabulary contains a hierarchy:

Category
    -> Item

Categories and items are different RAL dimensions.

1. Whole-category request

When the user asks about a complete category, populate the
canonical category and leave items empty.

Example:

"How many Donuts were sold last month?"

Return conceptually:

metric = "quantity"
categories = ["Donuts"]
items = []

This means the whole Donuts category.

2. Specific-item request

When the user asks about one specific item, populate the
canonical item name.

When its category is known from the client product master,
also populate its canonical category.

Example:

"How many Biscoff Donuts were sold last month?"

If the canonical item is "Biscoff Donut" and its category is
"Donuts", return:

metric = "quantity"
categories = ["Donuts"]
items = ["Biscoff Donut"]

3. Multiple items

Preserve every specifically requested valid item.

Example:

"Sales of Biscoff Donut and Nutella Filled Donut yesterday"

Return conceptually:

metric = "sales"
categories = ["Donuts"]
items = [
    "Biscoff Donut",
    "Nutella Filled Donut"
]

4. Multiple categories

Preserve every specifically requested valid category.

5. Never return a category name inside items.

6. Never return an individual item name as a category.

7. Never invent an item or category that does not exist in
the active client product vocabulary.

8. Never silently replace an unknown item with a similar
known item.

9. Never guess the category of an item classified as
Unmapped.

For an unmapped item:

- populate the canonical item if confidently identified,
- do not populate a guessed category.

10. Singular and plural business meaning

Ordinary singular and plural wording may refer to the same
canonical category or item.

Examples:

- donut
- donuts

Use the active client hierarchy to determine whether the
request refers to a whole category or one listed item.

11. Ambiguity

If the user's wording could refer to both a category and a
specific item and the meaning cannot be determined
confidently:

- set intent = "unsupported",
- set needs_clarification = true,
- ask one short clarification question.

12. Product wording must never be removed merely to make a
request executable.

=========================================================
CURRENTLY EXECUTABLE BUSINESS SCOPE
=========================================================

RestaurantAI currently executes only:

Overall restaurant SALES for yesterday.

For this exact executable request, return:

- intent = "sales"
- metric = "sales"
- time.type = "yesterday"
- time.start_date = null
- time.end_date = null
- stores = []
- regions = []
- channels = []
- aggregators = []
- categories = []
- items = []
- comparison.enabled = false
- all comparison dates = null
- needs_clarification = false
- clarification_question = null

Examples:

- Yesterday Sales
- Yesterday business
- How did we perform yesterday?
- How much did we sell yesterday?
- How was business yesterday?
- Give me yesterday's numbers
- Kal ka business
- Kal kitna hua?
- Ystrday performnce
- Natural requests in languages understood by the model

=========================================================
UNDERSTOOD BUT NOT YET EXECUTABLE
=========================================================

RAL must understand and preserve requests involving:

- quantity
- transactions
- ADS
- ADT
- APT
- today
- this week
- last week
- this month
- last month
- this quarter
- last quarter
- one specific date
- a date range
- custom time periods
- comparisons
- stores
- regions
- parent channels
- aggregators
- categories
- items

Because the corresponding complete business engines are not
yet connected, set:

intent = "unsupported"

while preserving every correctly understood RAL dimension.

Examples:

"How many donuts were sold yesterday?"

Return conceptually:

- intent = "unsupported"
- metric = "quantity"
- time.type = "yesterday"
- categories = ["Donuts"]
- items = []

"How many Biscoff Donuts were sold last month?"

Return conceptually:

- intent = "unsupported"
- metric = "quantity"
- time.type = "last_month"
- categories = ["Donuts"]
- items = ["Biscoff Donut"]

"How many bills were made last week?"

Return conceptually:

- intent = "unsupported"
- metric = "transactions"
- time.type = "last_week"

"What was our APT last month?"

Return conceptually:

- intent = "unsupported"
- metric = "apt"
- time.type = "last_month"

"Yesterday delivery sales"

Return conceptually:

- intent = "unsupported"
- metric = "sales"
- time.type = "yesterday"
- channels = ["Delivery"]
- aggregators = []

"Yesterday Swiggy sales"

Return conceptually:

- intent = "unsupported"
- metric = "sales"
- time.type = "yesterday"
- channels = ["Delivery"]
- aggregators = ["Swiggy"]

"Yesterday takeaway transactions"

Return conceptually:

- intent = "unsupported"
- metric = "transactions"
- time.type = "yesterday"
- channels = ["Take Away"]
- aggregators = []

"Sales from 01-Jul-2026 to 14-Jul-2026"

Return conceptually:

- intent = "unsupported"
- metric = "sales"
- time.type = "date_range"
- time.start_date = "2026-07-01"
- time.end_date = "2026-07-14"

=========================================================
COMPARISON RULES
=========================================================

When the user clearly asks to compare two periods:

- comparison.enabled = true
- intent = "unsupported" for now

Use comparison date fields only when two complete explicit
date periods are clearly provided.

Never invent comparison dates for relative or complex
expressions.

Example:

"Compare 01-Apr-2025 to 30-Jun-2025 with
01-Apr-2026 to 30-Jun-2026"

comparison.enabled = true
comparison.from_start_date = "2025-04-01"
comparison.from_end_date = "2025-06-30"
comparison.to_start_date = "2026-04-01"
comparison.to_end_date = "2026-06-30"

For:

"Compare this weekend with last weekend"

comparison.enabled = true

All comparison dates must remain null because Python will
resolve relative periods later.

=========================================================
SAFETY RULES
=========================================================

1. Understand meaning rather than matching exact words.

2. Be tolerant of ordinary spelling mistakes.

3. Never change the user's requested metric merely to fit an
available engine.

4. Never remove store, region, channel, aggregator, category
or item filters merely to make a request executable.

5. If the user requests quantity, do not classify it as
sales.

6. If the user requests bills, transactions, invoices,
receipts or orders, use metric = "transactions".

7. If the user asks only "How did we perform yesterday?"
without specifying another metric, use metric = "sales".

8. Never invent missing calendar information.

9. Swiggy and Zomato must never be returned as parent
channels.

10. A specific aggregator request must always include:

channels = ["Delivery"]

11. A whole-category request must leave items empty.

12. A specific-item request must populate items and should
also populate its category when the client hierarchy
provides it.

13. Never guess the category of an unmapped item.

14. If clarification is required:

- needs_clarification = true
- clarification_question must contain one short question

15. If clarification is not required:

- needs_clarification = false
- clarification_question = null

16. If the request is unclear or unrelated:

- intent = "unsupported"
- time.type = "unspecified"

17. understood_request must briefly describe the complete
request in plain English.

18. Return only the structured RAL object required by the
schema.
"""


def parse_ral_request(
    user_message: str,
) -> dict:
    """
    Translate human language into a complete, date-resolved
    RAL request.

    Flow:

        Human message
            ↓
        Dynamic client vocabulary
            ↓
        GPT proposes RAL
            ↓
        Python validates RAL structure
            ↓
        Python resolves relative time into dates
            ↓
        Python validates the final RAL again
            ↓
        Complete structured request
    """
    cleaned_message = _clean_message(
        user_message
    )

    if not cleaned_message:
        empty_request = (
            create_empty_ral_request()
        )

        empty_request[
            "understood_request"
        ] = "The message was empty."

        validate_ral_request(
            empty_request
        )

        return empty_request

    client_business_context = (
        _build_client_business_context()
    )

    ral_instructions = (
        _build_ral_instructions(
            client_business_context=(
                client_business_context
            )
        )
    )

    response = (
        llm_service.client.responses.create(
            model="gpt-5-mini",
            instructions=ral_instructions,
            input=cleaned_message,
            reasoning={
                "effort": "minimal",
            },
            text={
                "format": {
                    "type": "json_schema",
                    "name": (
                        "restaurantai_ral_request"
                    ),
                    "description": (
                        "A structured RestaurantAI "
                        "Language request."
                    ),
                    "schema": RAL_JSON_SCHEMA,
                    "strict": True,
                }
            },
        )
    )

    response_text = (
        response.output_text.strip()
    )

    try:
        proposed_ral_request = json.loads(
            response_text
        )

    except json.JSONDecodeError as error:
        raise ValueError(
            "The LLM returned invalid RAL JSON."
        ) from error

    # First guardrail:
    # validate exactly what GPT proposed.
    validate_ral_request(
        proposed_ral_request
    )

    # Resolve relative business time deterministically.
    resolved_ral_request = (
        resolve_ral_time(
            proposed_ral_request
        )
    )

    # Second guardrail:
    # validate the final date-resolved request.
    validate_ral_request(
        resolved_ral_request
    )

    return resolved_ral_request


def _ral_can_run_yesterday_sales(
    ral_request: dict,
) -> bool:
    """
    Decide deterministically whether the RAL request can
    safely use the existing overall Yesterday Sales engine.

    Only this exact request can execute:

    - sales metric,
    - yesterday,
    - one deterministically resolved date,
    - all stores,
    - all regions,
    - all channels,
    - all aggregators,
    - all categories,
    - all items,
    - no comparison,
    - no clarification.
    """
    if (
        ral_request["intent"]
        != "sales"
    ):
        return False

    if (
        ral_request["metric"]
        != METRIC_SALES
    ):
        return False

    if (
        ral_request["time"]["type"]
        != TIME_YESTERDAY
    ):
        return False

    start_date = ral_request[
        "time"
    ]["start_date"]

    end_date = ral_request[
        "time"
    ]["end_date"]

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

    if start_date != end_date:
        return False

    if ral_request["stores"]:
        return False

    if ral_request["regions"]:
        return False

    if ral_request["channels"]:
        return False

    if ral_request["aggregators"]:
        return False

    if ral_request["categories"]:
        return False

    if ral_request["items"]:
        return False

    if (
        ral_request["comparison"][
            "enabled"
        ]
    ):
        return False

    if ral_request[
        "needs_clarification"
    ]:
        return False

    return True


def parse_intent(
    user_message: str,
) -> IntentResult:
    """
    Backward-compatible adapter used by message_router.py.

    Internally:

        human language
            ↓
        complete date-resolved RAL
            ↓
        deterministic execution guardrail
            ↓
        old capability result

    Only unfiltered overall yesterday sales can currently
    reach the existing business engine through GPT.
    """
    ral_request = parse_ral_request(
        user_message=user_message
    )

    if _ral_can_run_yesterday_sales(
        ral_request
    ):
        capability = "yesterday_sales"

    else:
        capability = "unsupported"

    return {
        "capability": capability,
        "understood_request": (
            ral_request[
                "understood_request"
            ]
        ),
    }