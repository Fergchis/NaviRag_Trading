import json
import sys
import time
import uuid
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import agent_app.agent as agent_module  # noqa: E402
import agent_app.tools as agent_tools  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage  # noqa: E402


CASES_PATH = Path(__file__).with_name("casos_ev2.json")


def get_final_answer(messages: list) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:
            return str(message.content)
    return ""


def message_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content)


def extract_tool_calls(messages: list) -> list[dict]:
    calls = []
    for message in messages:
        if isinstance(message, AIMessage):
            for tool_call in message.tool_calls:
                calls.append({
                    "name": tool_call["name"],
                    "args": tool_call["args"],
                })
    return calls


def agent_goal_accuracy(question: str, answer: str, expected: str) -> float:
    result = agent_module.llm.invoke([
        SystemMessage(content=(
            "Evalúa semánticamente si la respuesta cumple el criterio esperado. No exijas "
            "coincidencia textual. Una referencia como [FUENTE 1] cuenta como evidencia "
            "visible. Responde solamente 'si' o 'no'."
        )),
        HumanMessage(content=(
            f"Pregunta: {question}\n"
            f"Criterio esperado: {expected}\n"
            f"Respuesta: {answer}"
        )),
    ])
    verdict = message_text(result.content).strip().lower().rstrip(".")
    return 1.0 if verdict in {"si", "sí", "yes"} else 0.0


def run_functional_case(case: dict, user_id: str) -> dict:
    thread_id = f"{case['id'].lower()}-{uuid.uuid4()}"
    started = time.perf_counter()
    result = agent_module.graph.invoke(
        {"messages": [HumanMessage(content=case["pregunta"])]},
        config={
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id,
            }
        },
    )
    latency = time.perf_counter() - started

    answer = get_final_answer(result["messages"])
    calls = extract_tool_calls(result["messages"])
    actual_tools = [call["name"] for call in calls]
    expected_tools = case.get("tools_esperadas", [])
    actual_agents = result.get("executed_agents", [])

    route_ok = result.get("next") == case["ruta_esperada"]
    agents_ok = actual_agents == case.get("agentes_esperados", [])
    tools_ok = actual_tools == expected_tools
    answer_score = agent_goal_accuracy(
        case["pregunta"],
        answer,
        case["respuesta_esperada"],
    )
    diagnostics_ok = (
        bool(result.get("retrieval_used", False))
        == bool(case.get("retrieval_esperado", False))
        and bool(result.get("memory_used", False))
        == bool(case.get("memoria_esperada", False))
        and bool(result.get("financial_rejection", False))
        == bool(case.get("rechazo_financiero_esperado", False))
    )

    return {
        "passed": route_ok and agents_ok and tools_ok and answer_score == 1.0 and diagnostics_ok,
        "latency": latency,
        "route": result.get("next"),
        "agents": actual_agents,
        "tools": actual_tools,
        "answer": answer,
        "answer_score": answer_score,
        "diagnostics_ok": diagnostics_ok,
    }


def run_error_case(case: dict) -> dict:
    expected_exception = case["excepcion_esperada"]
    error = RuntimeError(f"simulated {case['objetivo_error']} failure")
    config = {
        "configurable": {
            "thread_id": f"error-{uuid.uuid4()}",
            "user_id": "ev2-error-user",
        }
    }
    state = {
        "messages": [HumanMessage(content="Caso de error simulado")],
        "user_query": "Caso de error simulado",
        "next": case.get("ruta_simulada", "answer_agent"),
    }
    started = time.perf_counter()

    try:
        target = case["objetivo_error"]
        if target == "supervisor":
            with patch.object(
                type(agent_module.llm),
                "with_structured_output",
                side_effect=error,
            ):
                agent_module.supervisor_node(state)
        elif target == "rag_agent":
            with (
                patch.object(
                    agent_module,
                    "summarize_for",
                    return_value=HumanMessage(content="handoff simulado"),
                ),
                patch.object(agent_module.rag_agent, "invoke", side_effect=error),
            ):
                agent_module.rag_node(state, config)
        elif target == "memory_agent":
            with (
                patch.object(
                    agent_module,
                    "summarize_for",
                    return_value=HumanMessage(content="handoff simulado"),
                ),
                patch.object(agent_module.memory_agent, "invoke", side_effect=error),
            ):
                agent_module.memory_node(state, config)
        elif target == "answer_agent":
            with (
                patch.object(
                    agent_module,
                    "summarize_for",
                    return_value=HumanMessage(content="handoff simulado"),
                ),
                patch.object(agent_module.answer_agent, "invoke", side_effect=error),
            ):
                agent_module.answer_node(state, config)
        elif target == "retrieval":
            with patch.object(agent_tools.collection, "aggregate", side_effect=error):
                agent_tools.retrieve("consulta simulada")
        elif target == "semantic_store":
            with patch.object(type(agent_module.store), "search", side_effect=error):
                agent_module.store.search(("agent_memories", "ev2-error-user"))
        else:
            raise ValueError(f"Objetivo de error desconocido: {target}")
    except Exception as exc:
        latency = time.perf_counter() - started
        return {
            "passed": type(exc).__name__ == expected_exception,
            "latency": latency,
            "error": f"{type(exc).__name__}: {exc}",
        }

    return {
        "passed": False,
        "latency": time.perf_counter() - started,
        "error": "No se produjo la excepción esperada",
    }


def run_cases() -> bool:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    user_id = f"ev2-user-{uuid.uuid4()}"
    all_passed = True
    latencies = []

    for case in cases:
        try:
            if case["tipo"] == "error_simulado":
                outcome = run_error_case(case)
            else:
                outcome = run_functional_case(case, user_id)
        except Exception as exc:
            outcome = {
                "passed": False,
                "latency": 0.0,
                "error": f"{type(exc).__name__}: {exc}",
            }

        all_passed = all_passed and outcome["passed"]
        latencies.append(outcome["latency"])

        print("=" * 72)
        print(f"id: {case['id']}")
        print(f"tipo: {case['tipo']}")
        print(f"resultado: {'PASS' if outcome['passed'] else 'FAIL'}")
        print(f"latencia: {outcome['latency']:.3f}s")
        if "route" in outcome:
            print(f"ruta: {outcome['route']}")
            print(f"agentes: {outcome['agents']}")
            print(f"tools: {outcome['tools']}")
            print(f"goal accuracy: {outcome['answer_score']:.1f}")
            print(f"diagnósticos: {'PASS' if outcome['diagnostics_ok'] else 'FAIL'}")
            if not outcome["passed"]:
                print(f"respuesta: {outcome['answer']}")
        if outcome.get("error"):
            print(f"error: {outcome['error']}")

    print("=" * 72)
    average = sum(latencies) / len(latencies) if latencies else 0.0
    print(f"latencia promedio: {average:.3f}s")
    print(f"resultado general: {'PASS' if all_passed else 'FAIL'}")
    return all_passed


if __name__ == "__main__":
    raise SystemExit(0 if run_cases() else 1)
