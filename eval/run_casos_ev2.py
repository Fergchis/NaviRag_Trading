import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent import TradingAgent  # noqa: E402


CASES_PATH = Path(__file__).with_name("casos_ev2.json")


def expected_routes(case: dict) -> list[str]:
    if "rutas_esperadas" in case:
        return case["rutas_esperadas"]
    return [case["ruta_esperada"]]


def run_cases() -> bool:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    agent = TradingAgent()
    all_passed = True

    for case in cases:
        error = None
        result = {}
        try:
            result = agent.run(
                query=case["pregunta"],
                history=[],
                session_id=f"ev2-{case['id'].lower()}-{uuid.uuid4()}",
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        expected = expected_routes(case)
        obtained = result.get("decision", {}).get("route", "exception")
        sources = len(result.get("sources", []))
        passed = error is None and obtained in expected
        all_passed = all_passed and passed

        print("=" * 72)
        print(f"id: {case['id']}")
        print(f"pregunta: {case['pregunta']}")
        print(f"ruta esperada: {', '.join(expected)}")
        print(f"ruta obtenida: {obtained}")
        print(f"resultado: {'PASS' if passed else 'FAIL'}")
        print(f"fuentes: {sources}")
        print(f"error: {error or result.get('error') or '-'}")

    print("=" * 72)
    print(f"resultado general: {'PASS' if all_passed else 'FAIL'}")
    return all_passed


if __name__ == "__main__":
    raise SystemExit(0 if run_cases() else 1)
