from dataclasses import dataclass


@dataclass
class GraphRoute:
    node: str
    on_success: str | None = None
    on_blocked: str | None = None
    on_error: str | None = None


class AgentPlanner:
    def describe_graph(self) -> list[GraphRoute]:
        return [
            GraphRoute(node="load_memory", on_success="check_financial_safety"),
            GraphRoute(
                node="check_financial_safety",
                on_success="agent",
                on_blocked="blocked_response",
            ),
            GraphRoute(node="blocked_response", on_success="save_memory"),
            GraphRoute(node="agent", on_success="generate_query"),
            GraphRoute(node="generate_query", on_success="retrieve_context"),
            GraphRoute(
                node="retrieve_context",
                on_success="generate_answer",
                on_error="save_memory",
            ),
            GraphRoute(node="generate_answer", on_success="save_memory"),
            GraphRoute(node="save_memory"),
        ]


def serialize_routes(routes: list[GraphRoute]) -> list[dict]:
    return [
        {
            "node": route.node,
            "on_success": route.on_success,
            "on_blocked": route.on_blocked,
            "on_error": route.on_error,
        }
        for route in routes
    ]
