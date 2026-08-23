import argparse
import hashlib
import json
from pathlib import Path
from typing import Optional, Sequence

from app.embeddings import embed_texts
from app.evaluation import (
    build_four_layer_report,
    build_retrieval_report,
    load_evaluation_cases,
    load_manual_scores,
)
from app.retrieval import search_vectors

DEFAULT_CASES_PATH = Path(__file__).resolve().parents[1] / "evals" / "week-02-cases.json"
PROJECT_DIRECTORY = Path(__file__).resolve().parents[1]
DEFAULT_MANUAL_SCORES_PATH = (
    Path(__file__).resolve().parents[1] / "evals" / "week-03-manual-scores.json"
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_retrieval_snapshot(
    path: Path,
    cases: Sequence[dict[str, object]],
    cases_path: Path,
    document_id: str,
    max_k: int,
) -> tuple[str, list[list[int]], dict[str, object]]:
    """Load a previously captured real retrieval run without an external call."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("检索快照 schema_version 必须为 1")
    if payload.get("document_id") != document_id:
        raise ValueError("检索快照 document_id 与命令参数不一致")
    if payload.get("cases_sha256") != file_sha256(cases_path):
        raise ValueError("检索快照与当前评测用例文件不匹配")

    fixture = payload.get("fixture")
    fixture_sha256 = payload.get("fixture_sha256")
    if not isinstance(fixture, str) or not isinstance(fixture_sha256, str):
        raise ValueError("检索快照缺少固定语料路径或哈希")
    fixture_path = (PROJECT_DIRECTORY / fixture).resolve()
    try:
        fixture_path.relative_to(PROJECT_DIRECTORY.resolve())
    except ValueError as exc:
        raise ValueError("检索快照固定语料路径必须位于项目目录") from exc
    if not fixture_path.is_file() or file_sha256(fixture_path) != fixture_sha256:
        raise ValueError("检索快照与当前固定语料文件不匹配")

    embedding_model = payload.get("embedding_model")
    results = payload.get("results")
    if not isinstance(embedding_model, str) or not embedding_model.strip():
        raise ValueError("检索快照缺少 embedding_model")
    captured_k = payload.get("captured_k")
    if not isinstance(captured_k, int) or isinstance(captured_k, bool) or captured_k < max_k:
        raise ValueError(f"检索快照不包含本次要求的 Top-{max_k}")
    if not isinstance(results, list):
        raise ValueError("检索快照必须包含 results 数组")

    retrieved_by_id: dict[object, list[int]] = {}
    for result in results:
        if not isinstance(result, dict):
            raise ValueError("检索快照的每条结果必须是对象")
        case_id = result.get("case_id")
        retrieved = result.get("retrieved_chunk_indexes")
        if case_id in retrieved_by_id:
            raise ValueError("检索快照 case_id 不能重复")
        if (
            not isinstance(retrieved, list)
            or len(retrieved) < max_k
            or not all(
                isinstance(index, int) and not isinstance(index, bool) and index >= 0
                for index in retrieved
            )
            or len(set(retrieved)) != len(retrieved)
        ):
            raise ValueError(f"检索快照用例 {case_id} 的 Chunk 顺序无效或不足 Top-{max_k}")
        retrieved_by_id[case_id] = retrieved

    case_ids = [case["id"] for case in cases]
    if set(retrieved_by_id) != set(case_ids):
        raise ValueError("检索快照必须完整覆盖当前评测用例")
    metadata = {key: value for key, value in payload.items() if key != "results"}
    return embedding_model, [retrieved_by_id[case_id] for case_id in case_ids], metadata


def run_retrieval_evaluation(
    document_id: str,
    cases_path: Path,
    ks: Sequence[int],
    manual_scores_path: Optional[Path] = None,
    retrieval_snapshot_path: Optional[Path] = None,
) -> dict[str, object]:
    cases = load_evaluation_cases(cases_path)
    max_k = max(ks)
    snapshot_metadata = None
    if retrieval_snapshot_path is None:
        questions = [str(case["question"]) for case in cases]
        embedding_model, query_vectors = embed_texts(questions)
        retrieved_by_case = []
        for query_vector in query_vectors:
            matches = search_vectors(document_id, embedding_model, query_vector, max_k)
            retrieved_by_case.append([int(match["chunk_index"]) for match in matches])
        retrieval_mode = "live_embedding"
    else:
        embedding_model, retrieved_by_case, snapshot_metadata = load_retrieval_snapshot(
            retrieval_snapshot_path,
            cases,
            cases_path,
            document_id,
            max_k,
        )
        retrieval_mode = "saved_real_retrieval_snapshot"

    if manual_scores_path is None:
        report = build_retrieval_report(cases, retrieved_by_case, ks)
    else:
        manual_scores = load_manual_scores(manual_scores_path, cases)
        report = build_four_layer_report(cases, retrieved_by_case, ks, manual_scores)
    return {
        "document_id": document_id,
        "embedding_model": embedding_model,
        "ks": list(ks),
        "retrieval_mode": retrieval_mode,
        "input_sha256": {
            "cases": file_sha256(cases_path),
            "manual_scores": file_sha256(manual_scores_path) if manual_scores_path else None,
            "retrieval_snapshot": (
                file_sha256(retrieval_snapshot_path) if retrieval_snapshot_path else None
            ),
        },
        "retrieval_snapshot_metadata": snapshot_metadata,
        **report,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行 RAG-CMS 检索 Recall@K 与充分证据命中评测")
    parser.add_argument("--document-id", required=True, help="已完成向量化的文档 ID")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH, help="评测用例 JSON")
    parser.add_argument(
        "--manual-scores",
        type=Path,
        help=f"答案覆盖与引用忠实性人工评分 JSON，例如 {DEFAULT_MANUAL_SCORES_PATH}",
    )
    parser.add_argument(
        "--retrieval-snapshot",
        type=Path,
        help="重放已保存的真实检索顺序；传入后不会调用 Embedding 服务",
    )
    parser.add_argument("--output", type=Path, help="将完整 JSON 报告写入指定文件")
    parser.add_argument("--k", type=int, nargs="+", default=[1, 3], help="需要计算的 K 值")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if any(k < 1 for k in args.k):
        raise SystemExit("--k 必须是大于等于 1 的整数")
    report = run_retrieval_evaluation(
        args.document_id,
        args.cases,
        args.k,
        args.manual_scores,
        args.retrieval_snapshot,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output is not None:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
