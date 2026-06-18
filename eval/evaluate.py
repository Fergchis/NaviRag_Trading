import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402
from ragas.embeddings.base import embedding_factory  # noqa: E402
from ragas.llms.base import llm_factory  # noqa: E402
from ragas.metrics.collections import (  # noqa: E402
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

from agent_app.agent import graph  # noqa: E402
from agent_app.tools import retrieve  # noqa: E402

load_dotenv()

DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset.json")


def get_final_answer(messages: list) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:
            return str(message.content)
    return ""


def run_evaluation(limit=None):
    with open(DATASET_PATH, "r", encoding="utf-8") as file:
        dataset = json.load(file)

    if limit is not None:
        dataset = dataset[:limit]

    github_client = AsyncOpenAI(
        api_key=os.getenv("GITHUB_TOKEN"),
        base_url="https://models.github.ai/inference",
    )
    llm = llm_factory(
        os.getenv("GITHUB_CHAT_MODEL", "openai/gpt-4o-mini"),
        provider="openai",
        client=github_client,
    )
    embeddings = embedding_factory(
        provider="openai",
        model=os.getenv("GITHUB_EMBEDDING_MODEL", "openai/text-embedding-3-small"),
        client=github_client,
    )

    metrics = {
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevancy": AnswerRelevancy(llm=llm, embeddings=embeddings),
        "context_precision": ContextPrecision(llm=llm),
        "context_recall": ContextRecall(llm=llm),
    }

    results = []
    print(f"Running supervisor + RAG evaluation on {len(dataset)} questions...\n")

    for item in dataset:
        query = item["question"]
        ground_truth = item["ground_truth"]
        chunks = retrieve(query, top_k=5)
        context_texts = [chunk.get("text", "") for chunk in chunks]
        run_id = str(uuid.uuid4())
        response = graph.invoke(
            {"messages": [HumanMessage(content=query)]},
            config={
                "configurable": {
                    "thread_id": f"ragas-{run_id}",
                    "user_id": f"ragas-{run_id}",
                }
            },
        )
        answer = get_final_answer(response["messages"])

        scores = {}
        score_inputs = {
            "faithfulness": dict(
                user_input=query,
                response=answer,
                retrieved_contexts=context_texts,
            ),
            "answer_relevancy": dict(user_input=query, response=answer),
            "context_precision": dict(
                user_input=query,
                reference=ground_truth,
                retrieved_contexts=context_texts,
            ),
            "context_recall": dict(
                user_input=query,
                retrieved_contexts=context_texts,
                reference=ground_truth,
            ),
        }
        for name, metric in metrics.items():
            try:
                result = metric.score(**score_inputs[name])
                scores[name] = round(result.value, 3)
            except Exception as exc:
                scores[name] = f"error: {exc}"

        results.append({
            "question": query,
            "answer": answer,
            "route": response.get("next"),
            "scores": scores,
        })

        print(f"Q: {query[:60]}")
        print(f"  route: {response.get('next')}")
        for name, value in scores.items():
            print(f"  {name}: {value}")
        print()

    print("=== Summary ===")
    for metric_name in metrics:
        values = [
            result["scores"][metric_name]
            for result in results
            if isinstance(result["scores"][metric_name], float)
        ]
        if values:
            print(f"{metric_name}: {round(sum(values) / len(values), 3)}")

    return results


if __name__ == "__main__":
    run_evaluation()
