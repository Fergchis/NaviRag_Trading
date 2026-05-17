from dataclasses import dataclass


@dataclass
class PlanStep:
    name: str
    tool: str
    description: str
    priority: int
    status: str = "pending"
    reason: str = ""


class AgentPlanner:
    def create_plan(self, query: str) -> list[PlanStep]:
        return [
            PlanStep(
                name="load_memory",
                tool="load_memory_tool",
                description="Cargar memoria de largo plazo para la sesion.",
                priority=1,
            ),
            PlanStep(
                name="safety_check",
                tool="safety_check_tool",
                description="Validar si la pregunta pide recomendacion financiera o senales.",
                priority=2,
            ),
            PlanStep(
                name="retrieve_context",
                tool="retrieve_context_tool",
                description="Recuperar contexto semantico desde MongoDB Vector Search.",
                priority=3,
            ),
            PlanStep(
                name="write_answer",
                tool="write_answer_tool",
                description="Generar una respuesta educativa usando el contexto recuperado.",
                priority=4,
            ),
            PlanStep(
                name="save_memory",
                tool="save_memory_tool",
                description="Guardar datos minimos de continuidad de la sesion.",
                priority=5,
            ),
        ]


def serialize_plan(plan: list[PlanStep]) -> list[dict]:
    return [
        {
            "step": step.name,
            "tool": step.tool,
            "status": step.status,
            "reason": step.reason,
        }
        for step in plan
    ]
