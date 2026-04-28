"""Simple safety rules for the educational trading domain."""

FORBIDDEN_PHRASES = (
    "should i buy",
    "should i sell",
    "what crypto should i buy",
    "trading signal",
    "give me a signal",
    "deberia comprar",
    "deberia vender",
    "debo comprar",
    "debo vender",
    "conviene comprar",
    "conviene vender",
    "senal de trading",
    "señal de trading",
)

INTENT_TERMS = (
    "buy",
    "sell",
    "invest",
    "recommend",
    "recommendation",
    "signal",
    "comprar",
    "vender",
    "invertir",
    "recomendar",
    "recomendacion",
    "recomendación",
    "senal",
    "señal",
)

ASSET_TERMS = (
    "bitcoin",
    "btc",
    "crypto",
    "cripto",
    "stock",
    "stocks",
    "acciones",
)


def is_forbidden_question(question: str) -> bool:
    """Detect obvious requests for financial advice or trading signals."""
    normalized = question.lower()
    if any(phrase in normalized for phrase in FORBIDDEN_PHRASES):
        return True

    has_intent = any(term in normalized for term in INTENT_TERMS)
    has_asset = any(term in normalized for term in ASSET_TERMS)
    return has_intent and has_asset
