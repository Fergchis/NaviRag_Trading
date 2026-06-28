"""
Evaluacion EV3 de NaviRAG Trading.

Estructura basada en Clase 3.1:
- run_agent
- extract_tool_calls
- get_final_answer
- tool_call_accuracy
- agent_goal_accuracy
- main

No registra observabilidad local. Solo escribe eval/resultados_ev3.json
cuando se ejecuta la evaluacion real.
"""

import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage  # noqa: E402

import agent_app.agent as agent_module  # noqa: E402


EVALS_PATH = Path(__file__).parent / "casos_ev3.json"
RESULTS_PATH = Path(__file__).parent / "resultados_ev3.json"
judge_llm = agent_module.llm


def message_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content)


def run_agent(pregunta: str, thread_id: str | None = None, user_id: str | None = None) -> dict:
    config = {
        "configurable": {
            "thread_id": thread_id or str(uuid.uuid4()),
            "user_id": user_id or f"ev3-user-{uuid.uuid4()}",
        }
    }
    return agent_module.graph.invoke(
        {"messages": [HumanMessage(content=pregunta)]},
        config=config,
    )


def extract_tool_calls(messages: list) -> list[dict]:
    """Retorna lista de {name, args} de cada tool call ejecutada."""
    calls = []
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tool_call in msg.tool_calls:
                calls.append({
                    "name": tool_call["name"],
                    "args": tool_call.get("args", {}),
                })
    return calls


def get_final_answer(messages: list) -> str:
    """Retorna el contenido del ultimo mensaje del agente."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return message_text(msg.content)
    return ""


def tool_call_accuracy(actual: list, expected: list) -> float:
    """
    Compara las tool calls reales vs esperadas en orden.
    Si args esta vacio en el caso, solo valida el nombre de la tool.
    """
    if not expected:
        return 1.0 if not actual else 0.0

    correct = 0
    for index, exp in enumerate(expected):
        if index >= len(actual):
            break

        expected_name = exp.get("tool") or exp.get("name")
        expected_args = exp.get("args", {})
        name_ok = actual[index]["name"] == expected_name
        args_ok = all(
            str(actual[index]["args"].get(key)) == str(value)
            for key, value in expected_args.items()
        )
        if name_ok and args_ok:
            correct += 1

    return correct / len(expected)


def normalize_judge_answer(text: str) -> str:
    return message_text(text).strip().lower().rstrip(".").replace("sí", "si")


def agent_goal_accuracy(pregunta: str, respuesta_final: str, respuesta_esperada: str) -> float:
    """
    Usa el LLM del proyecto como juez para decidir si la respuesta final logra el objetivo.
    Retorna 1.0 si cumple, 0.0 si no.
    """
    result = judge_llm.invoke([
        SystemMessage(content=(
            "Evalua semanticamente si la respuesta del agente cumple el criterio esperado. "
            "No exijas coincidencia textual. Una referencia como [FUENTE 1] cuenta como "
            "evidencia visible. Responde solamente 'si' o 'no'."
        )),
        HumanMessage(content=(
            f"Pregunta: {pregunta}\n"
            f"Criterio esperado: {respuesta_esperada}\n"
            f"Respuesta del agente: {respuesta_final}"
        )),
    ])
    answer = normalize_judge_answer(result.content)
    return 1.0 if answer in {"si", "yes"} else 0.0


def agent_consistency_score(preguntas: list[str], respuestas: list[str], criterio: str) -> float:
    """Evalua si respuestas a parafrasis son consistentes entre si."""
    conversation = "\n\n".join(
        f"Pregunta {index}: {question}\nRespuesta {index}: {answer}"
        for index, (question, answer) in enumerate(zip(preguntas, respuestas), start=1)
    )
    result = judge_llm.invoke([
        SystemMessage(content=(
            "Evalua si las respuestas son semanticamente consistentes entre si. "
            "Deben mantener el mismo criterio educativo, no contradecirse y cumplir "
            "el objetivo descrito. Responde solamente 'si' o 'no'."
        )),
        HumanMessage(content=f"Criterio: {criterio}\n\n{conversation}"),
    ])
    answer = normalize_judge_answer(result.content)
    return 1.0 if answer in {"si", "yes"} else 0.0


def _expected_tool_names(case: dict) -> list[str]:
    return [tool.get("tool") or tool.get("name") for tool in case.get("tools_esperadas", [])]


def _diagnostics_ok(result: dict, case: dict) -> bool:
    return (
        bool(result.get("retrieval_used", False)) == bool(case.get("retrieval_esperado", False))
        and bool(result.get("memory_used", False)) == bool(case.get("memoria_esperada", False))
        and bool(result.get("financial_rejection", False))
        == bool(case.get("rechazo_financiero_esperado", False))
    )


def _run_single_case(case: dict, user_id: str) -> dict:
    started = time.perf_counter()
    result = run_agent(case["pregunta"], user_id=user_id)
    latency = time.perf_counter() - started

    messages = result["messages"]
    actual_calls = extract_tool_calls(messages)
    final_answer = get_final_answer(messages)
    expected_tools = _expected_tool_names(case)
    actual_tools = [call["name"] for call in actual_calls]

    t_score = tool_call_accuracy(actual_calls, case.get("tools_esperadas", []))
    g_score = agent_goal_accuracy(case["pregunta"], final_answer, case["respuesta_esperada"])
    route_ok = result.get("next") == case["ruta_esperada"]
    agents_ok = result.get("executed_agents", []) == case.get("agentes_esperados", [])
    tools_ok = actual_tools == expected_tools
    diagnostics_ok = _diagnostics_ok(result, case)
    passed = route_ok and agents_ok and tools_ok and diagnostics_ok and g_score == 1.0

    return {
        "passed": passed,
        "exception": False,
        "latency": latency,
        "route": result.get("next"),
        "agents": result.get("executed_agents", []),
        "tools": actual_tools,
        "tool_call_accuracy": t_score,
        "agent_goal_accuracy": g_score,
        "consistency_score": None,
        "answer": final_answer,
        "diagnostics_ok": diagnostics_ok,
        "flags": {
            "retrieval_used": bool(result.get("retrieval_used", False)),
            "memory_used": bool(result.get("memory_used", False)),
            "financial_rejection": bool(result.get("financial_rejection", False)),
        },
    }


def _run_consistency_case(case: dict, user_id: str) -> dict:
    thread_ids = [f"{case['id'].lower()}-{uuid.uuid4()}" for _ in case["preguntas"]]
    runs = []
    latencies = []

    for pregunta, thread_id in zip(case["preguntas"], thread_ids):
        started = time.perf_counter()
        result = run_agent(pregunta, thread_id=thread_id, user_id=user_id)
        latency = time.perf_counter() - started
        latencies.append(latency)

        messages = result["messages"]
        actual_calls = extract_tool_calls(messages)
        final_answer = get_final_answer(messages)
        runs.append({
            "pregunta": pregunta,
            "respuesta": final_answer,
            "ruta": result.get("next"),
            "agentes": result.get("executed_agents", []),
            "tools": [call["name"] for call in actual_calls],
            "tool_call_accuracy": tool_call_accuracy(
                actual_calls,
                case.get("tools_esperadas", []),
            ),
            "agent_goal_accuracy": agent_goal_accuracy(
                pregunta,
                final_answer,
                case["respuesta_esperada"],
            ),
            "diagnostics_ok": _diagnostics_ok(result, case),
            "flags": {
                "retrieval_used": bool(result.get("retrieval_used", False)),
                "memory_used": bool(result.get("memory_used", False)),
                "financial_rejection": bool(result.get("financial_rejection", False)),
            },
        })

    expected_tools = _expected_tool_names(case)
    structural_ok = all(
        run["ruta"] == case["ruta_esperada"]
        and run["agentes"] == case.get("agentes_esperados", [])
        and run["tools"] == expected_tools
        and run["diagnostics_ok"]
        for run in runs
    )
    consistency = agent_consistency_score(
        case["preguntas"],
        [run["respuesta"] for run in runs],
        case["respuesta_esperada"],
    )
    goal_accuracy = sum(run["agent_goal_accuracy"] for run in runs) / len(runs)
    tool_accuracy = sum(run["tool_call_accuracy"] for run in runs) / len(runs)
    passed = structural_ok and goal_accuracy == 1.0 and consistency == 1.0

    return {
        "passed": passed,
        "exception": False,
        "latency": sum(latencies),
        "latencies": latencies,
        "route": [run["ruta"] for run in runs],
        "agents": [run["agentes"] for run in runs],
        "tools": [run["tools"] for run in runs],
        "tool_call_accuracy": tool_accuracy,
        "agent_goal_accuracy": goal_accuracy,
        "consistency_score": consistency,
        "answer": [run["respuesta"] for run in runs],
        "diagnostics_ok": structural_ok,
        "runs": runs,
    }


def _result_record(case: dict, outcome: dict) -> dict:
    return {
        "_exception": bool(outcome.get("exception", False)),
        "_latency_raw_s": float(outcome.get("latency", 0.0)),
        "caso": case["id"],
        "tipo": case["tipo"],
        "input": case.get("pregunta", case.get("preguntas")),
        "ruta_esperada": case["ruta_esperada"],
        "ruta_observada": outcome.get("route"),
        "agentes_esperados": case.get("agentes_esperados", []),
        "agentes_ejecutados": outcome.get("agents"),
        "tools_esperadas": _expected_tool_names(case),
        "tools_usadas": outcome.get("tools"),
        "respuesta": outcome.get("answer"),
        "tool_call_accuracy": outcome.get("tool_call_accuracy", 0.0),
        "agent_goal_accuracy": outcome.get("agent_goal_accuracy", 0.0),
        "consistency_score": outcome.get("consistency_score"),
        "latency_s": round(outcome.get("latency", 0.0), 3),
        "diagnostics_ok": outcome.get("diagnostics_ok", False),
        "resultado": "PASS" if outcome.get("passed") else "FAIL",
        "error": outcome.get("error"),
    }


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summarize_results(records: list[dict]) -> dict:
    total_cases = len(records)
    passed_count = sum(1 for record in records if record.get("resultado") == "PASS")
    exception_count = sum(1 for record in records if record.get("_exception"))
    tool_scores = [float(record.get("tool_call_accuracy", 0.0)) for record in records]
    goal_scores = [float(record.get("agent_goal_accuracy", 0.0)) for record in records]
    consistency_scores = [
        float(record["consistency_score"])
        for record in records
        if record.get("consistency_score") is not None
    ]
    latencies = [float(record.get("_latency_raw_s", 0.0)) for record in records]

    case_pass_rate = passed_count / total_cases if total_cases else 0.0
    error_frequency = (total_cases - passed_count) / total_cases if total_cases else 0.0
    exception_frequency = exception_count / total_cases if total_cases else 0.0

    return {
        "total_cases": total_cases,
        "case_pass_rate": round(case_pass_rate, 4),
        "tool_call_accuracy_avg": round(_average(tool_scores), 4),
        "agent_goal_accuracy_avg": round(_average(goal_scores), 4),
        "consistency_score": round(_average(consistency_scores), 4),
        "error_frequency": round(error_frequency, 4),
        "exception_frequency": round(exception_frequency, 4),
        "latency_avg_s": round(_average(latencies), 3),
    }


def run_cases() -> bool:
    evals = json.loads(EVALS_PATH.read_text(encoding="utf-8"))
    user_id = f"ev3-user-{uuid.uuid4()}"

    result_records = []

    print("=" * 72)
    print("Evaluacion EV3 de NaviRAG Trading")
    print("=" * 72)

    for index, case in enumerate(evals, start=1):
        print(f"\n[{index}] {case['id']} - {case['tipo']}")
        try:
            if case["tipo"] == "consistencia":
                outcome = _run_consistency_case(case, user_id)
            else:
                outcome = _run_single_case(case, user_id)
        except Exception as exc:
            outcome = {
                "passed": False,
                "exception": True,
                "latency": 0.0,
                "tool_call_accuracy": 0.0,
                "agent_goal_accuracy": 0.0,
                "consistency_score": 0.0 if case["tipo"] == "consistencia" else None,
                "error": f"{type(exc).__name__}: {exc}",
            }

        result_records.append(_result_record(case, outcome))

        print(f"   Resultado            : {'PASS' if outcome.get('passed') else 'FAIL'}")
        print(f"   Latencia             : {outcome.get('latency', 0.0):.2f}s")
        print(f"   Tool Call Accuracy   : {outcome.get('tool_call_accuracy', 0.0):.2f}")
        print(f"   Agent Goal Accuracy  : {outcome.get('agent_goal_accuracy', 0.0):.2f}")
        if outcome.get("consistency_score") is not None:
            print(f"   Consistency Score    : {outcome['consistency_score']:.2f}")
        if outcome.get("error"):
            print(f"   Error                : {outcome['error']}")

    summary = summarize_results(result_records)
    public_records = [
        {key: value for key, value in record.items() if not key.startswith("_")}
        for record in result_records
    ]

    RESULTS_PATH.write_text(
        json.dumps({"summary": summary, "cases": public_records}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )

    print("\n" + "=" * 72)
    print("RESULTADO FINAL")
    print("=" * 72)
    print(f"  Tool Call Accuracy  (promedio): {summary['tool_call_accuracy_avg']:.2f}")
    print(f"  Agent Goal Accuracy (promedio): {summary['agent_goal_accuracy_avg']:.2f}")
    print(f"  Consistency Score             : {summary['consistency_score']:.2f}")
    print(f"  Error Frequency               : {summary['error_frequency']:.2f}")
    print(f"  Exception Frequency           : {summary['exception_frequency']:.2f}")
    print(f"  Latencia promedio             : {summary['latency_avg_s']:.2f}s")
    print(f"  Case Pass Rate                : {summary['case_pass_rate']:.2f}")
    print(f"  Resultados                    : {RESULTS_PATH}")
    print("=" * 72)

    return summary["case_pass_rate"] == 1.0


def main() -> None:
    # Caso futuro opcional: EV3-MEM01 podria agregarse si se decide evaluar memoria.
    raise SystemExit(0 if run_cases() else 1)


if __name__ == "__main__":
    main()
