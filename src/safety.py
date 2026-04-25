"""Simple safety rules for the educational trading domain."""

FORBIDDEN_TERMS = (
    "compro",
    "comprar",
    "vendo",
    "vender",
    "debería vender",
    "deberia vender",
    "debería comprar",
    "deberia comprar",
    "entrada",
    "stop loss",
    "take profit",
    "invertir",
    "invierto",
    "portafolio me recomiendas",
    "va a subir",
    "va a bajar",
    "señal",
    "senal",
)


def is_forbidden_question(question: str) -> bool:
    """Detect obvious requests for financial advice or trading signals."""
    normalized = question.lower()
    return any(term in normalized for term in FORBIDDEN_TERMS)
