"""Simple safety rules for the educational trading domain."""

FORBIDDEN_TERMS = (
    "compro",
    "comprar",
    "recomiendame",
    "recomiéndame",
    "recomiendas",
    "conviene comprar",
    "conviene vender",
    "vendo",
    "vender",
    "deberia vender",
    "debería vender",
    "deberia comprar",
    "debería comprar",
    "debo vender",
    "debo comprar",
    "entrada",
    "precio objetivo",
    "target",
    "abrir posicion",
    "abrir posición",
    "cerrar posicion",
    "cerrar posición",
    "long",
    "short",
    "apalancamiento",
    "stop loss",
    "take profit",
    "invertir",
    "invierto",
    "portafolio me recomiendas",
    "va a subir",
    "va a bajar",
    "senal",
    "señal",
)


def is_forbidden_question(question: str) -> bool:
    """Detect obvious requests for financial advice or trading signals."""
    normalized = question.lower()
    return any(term in normalized for term in FORBIDDEN_TERMS)
