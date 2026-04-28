import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402
from ragas.embeddings.base import embedding_factory  # noqa: E402
from ragas.llms.base import llm_factory  # noqa: E402
from ragas.metrics.collections import (  # noqa: E402
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)
from src.generate.generate import RAGGenerator  # noqa: E402
from src.utils.embeddings import DEFAULT_GITHUB_EMBEDDING_MODEL  # noqa: E402
from src.utils.llm import DEFAULT_GITHUB_CHAT_MODEL  # noqa: E402

load_dotenv()

DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset.json")


def run_evaluation(limit=1):
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    if limit:
        dataset = dataset[:limit]

    rag = RAGGenerator()

    github_client = AsyncOpenAI(
        api_key=os.getenv("GITHUB_TOKEN"),
        base_url="https://models.github.ai/inference",
    )

    llm = llm_factory(
        os.getenv("GITHUB_CHAT_MODEL") or DEFAULT_GITHUB_CHAT_MODEL,
        provider="openai",
        client=github_client,
    )
    embeddings = embedding_factory(
        provider="openai",
        model=os.getenv("GITHUB_EMBEDDING_MODEL") or DEFAULT_GITHUB_EMBEDDING_MODEL,
        client=github_client,
    )

    metrics = {
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevancy": AnswerRelevancy(llm=llm, embeddings=embeddings),
        "context_precision": ContextPrecision(llm=llm),
        "context_recall": ContextRecall(llm=llm),
    }

    results = []
    print(f"Running RAG + evaluation on {len(dataset)} questions...\n")

    for item in dataset:
        query = item["question"]
        ground_truth = item["ground_truth"]

        chunks = rag.retriever.retrieve(query, top_k=5)
        context_texts = [chunk["text"] for chunk in chunks]
        response = rag.generate(query=query, history=[])
        answer = response["answer"]

        scores = {}
        score_inputs = {
            "faithfulness": dict(user_input=query, response=answer, retrieved_contexts=context_texts),
            "answer_relevancy": dict(user_input=query, response=answer),
            "context_precision": dict(user_input=query, reference=ground_truth, retrieved_contexts=context_texts),
            "context_recall": dict(user_input=query, retrieved_contexts=context_texts, reference=ground_truth),
        }
        for name, metric in metrics.items():
            try:
                result = metric.score(**score_inputs[name])
                scores[name] = round(result.value, 3)
            except Exception as e:
                scores[name] = f"error: {e}"

        results.append({
            "question": query,
            "answer": answer,
            "scores": scores,
        })

        print(f"Q: {query[:60]}")
        for k, v in scores.items():
            print(f"  {k}: {v}")
        print()

    print("=== Summary ===")
    for metric_name in metrics:
        values = [r["scores"][metric_name] for r in results if isinstance(r["scores"][metric_name], float)]
        if values:
            print(f"{metric_name}: {round(sum(values) / len(values), 3)}")

    return results


if __name__ == "__main__":
    run_evaluation(limit=1)
