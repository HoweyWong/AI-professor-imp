import argparse
import json
from pathlib import Path
from typing import Sequence

from app.embeddings import embed_texts
from app.evaluation import build_retrieval_report, load_evaluation_cases
from app.retrieval import search_vectors

DEFAULT_CASES_PATH = Path(__file__).resolve().parents[1] / "evals" / "week-02-cases.json"


def run_retrieval_evaluation(
    document_id: str,
    cases_path: Path,
    ks: Sequence[int],
) -> dict[str, object]:
    cases = load_evaluation_cases(cases_path)
    questions = [str(case["question"]) for case in cases]
    embedding_model, query_vectors = embed_texts(questions)
    max_k = max(ks)
    retrieved_by_case = []
    for query_vector in query_vectors:
        matches = search_vectors(document_id, embedding_model, query_vector, max_k)
        retrieved_by_case.append([int(match["chunk_index"]) for match in matches])

    report = build_retrieval_report(cases, retrieved_by_case, ks)
    return {
        "document_id": document_id,
        "embedding_model": embedding_model,
        "ks": list(ks),
        **report,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行 RAG-CMS 检索 Recall@K 与充分证据命中评测")
    parser.add_argument("--document-id", required=True, help="已完成向量化的文档 ID")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH, help="评测用例 JSON")
    parser.add_argument("--k", type=int, nargs="+", default=[1, 3], help="需要计算的 K 值")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if any(k < 1 for k in args.k):
        raise SystemExit("--k 必须是大于等于 1 的整数")
    report = run_retrieval_evaluation(args.document_id, args.cases, args.k)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
