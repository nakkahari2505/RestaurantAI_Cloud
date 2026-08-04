import json
from typing import Literal, TypedDict

from services.llm_service import llm_service


class IntentResult(TypedDict):
    """
    Structured result returned by RestaurantAI's
    natural-language intent parser.
    """

    capability: Literal[
        "yesterday_sales",
        "unsupported",
    ]

    understood_request: str


INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "capability": {
            "type": "string",
            "enum": [
                "yesterday_sales",
                "unsupported",
            ],
        },
        "understood_request": {
            "type": "string",
        },
    },
    "required": [
        "capability",
        "understood_request",
    ],
    "additionalProperties": False,
}


INTENT_INSTRUCTIONS = """
You are the intent-understanding layer of RestaurantAI.

RestaurantAI is a business analytics assistant for restaurant owners.

Your current job is extremely narrow:

1. Read the user's message.
2. Decide whether the user is asking for the restaurant's
   overall yesterday sales or yesterday business performance.
3. Return the required structured result.
4. Never calculate sales.
5. Never answer the business question.
6. Never invent a capability.

Available capabilities:

- yesterday_sales
  Use this only when the user is asking for the overall
  restaurant business, sales, revenue, turnover, performance,
  numbers, KPIs, report or summary for yesterday.

- unsupported
  Use this for every other request.

Examples that mean yesterday_sales:

- Yesterday Sales
- Yesterday sale
- Yesterday report
- Yesterday performance
- How was yesterday?
- How did we perform yesterday?
- Show me yesterday's business
- Can I see yesterday's numbers?
- How much did we sell yesterday?
- Give me yesterday's revenue
- What was yesterday's turnover?
- Yesterdy sales
- Ystrday performance
- How was yday business?
- Show yestrday report

Examples that must be unsupported for now:

- Sales last week
- Sales today
- Compare yesterday with last Sunday
- Yesterday Swiggy sales
- Yesterday sales in Gachibowli
- Which store performed best yesterday?
- How many donuts did we sell yesterday?
- What is the weather?
- Hello
- Thank you

Important rules:

- Be tolerant of ordinary spelling mistakes.
- Understand natural language rather than matching exact words.
- Do not treat a filtered question about one store, channel,
  product or category as the overall yesterday_sales capability.
- The field understood_request must contain a short plain-English
  description of what you understood.
- If uncertain, choose unsupported.
"""


def parse_intent(
    user_message: str,
) -> IntentResult:
    """
    Convert a natural-language user message into a safe,
    structured RestaurantAI intent.

    This function does not:
    - read sales data,
    - calculate KPIs,
    - generate reports,
    - send WhatsApp messages.

    It only identifies what the user is asking for.
    """
    cleaned_message = " ".join(
        str(user_message).strip().split()
    )

    if not cleaned_message:
        return {
            "capability": "unsupported",
            "understood_request": (
                "The message was empty."
            ),
        }

    response = llm_service.client.responses.create(
        model="gpt-5-mini",
        instructions=INTENT_INSTRUCTIONS,
        input=cleaned_message,
        reasoning={
            "effort": "minimal",
        },
        text={
            "format": {
                "type": "json_schema",
                "name": "restaurantai_intent",
                "description": (
                    "RestaurantAI capability selected "
                    "from a user message."
                ),
                "schema": INTENT_SCHEMA,
                "strict": True,
            }
        },
    )

    response_text = response.output_text.strip()

    try:
        parsed_result = json.loads(
            response_text
        )

    except json.JSONDecodeError as error:
        raise ValueError(
            "The LLM returned an invalid intent response."
        ) from error

    capability = parsed_result.get(
        "capability"
    )

    understood_request = str(
        parsed_result.get(
            "understood_request",
            "",
        )
    ).strip()

    if capability not in {
        "yesterday_sales",
        "unsupported",
    }:
        raise ValueError(
            "The LLM returned an unsupported capability."
        )

    if not understood_request:
        understood_request = (
            "No request description was returned."
        )

    return {
        "capability": capability,
        "understood_request": understood_request,
    }