import json
from pathlib import Path
from typing import Iterable, Sequence


def load_evaluation_cases(path: Path) -> list[dict[str, object]]:
    """Load and validate the fields required by retrieval evaluation."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(cases, list) or not cases:
        raise ValueError("评测文件必须包含非空 cases 数组")

    validated: list[dict[str, object]] = []
    seen_ids: set[int] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("每个评测用例必须是对象")
        case_id = case.get("id")
        question = case.get("question")
        relevant = case.get("relevant_chunk_indexes")
        sufficient_sets = case.get("sufficient_evidence_sets")
        if not isinstance(case_id, int) or isinstance(case_id, bool) or case_id in seen_ids:
            raise ValueError("评测用例 id 必须是唯一整数")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"评测用例 {case_id} 的问题不能为空")
        if (
            not isinstance(relevant, list)
            or not relevant
            or not all(
                isinstance(index, int) and not isinstance(index, bool) and index >= 0
                for index in relevant
            )
            or len(set(relevant)) != len(relevant)
        ):
            raise ValueError(f"评测用例 {case_id} 必须包含相关 Chunk 序号")
        if not isinstance(sufficient_sets, list) or not sufficient_sets:
            raise ValueError(f"评测用例 {case_id} 必须包含非空充分证据集合")

        normalized_sets: list[tuple[int, ...]] = []
        for evidence_set in sufficient_sets:
            if (
                not isinstance(evidence_set, list)
                or not evidence_set
                or not all(
                    isinstance(index, int) and not isinstance(index, bool) and index >= 0
                    for index in evidence_set
                )
                or len(set(evidence_set)) != len(evidence_set)
            ):
                raise ValueError(f"评测用例 {case_id} 的每组充分证据必须包含非重复 Chunk 序号")
            if not set(evidence_set).issubset(relevant):
                raise ValueError(f"评测用例 {case_id} 的充分证据必须属于相关 Chunk 集合")
            normalized_sets.append(tuple(sorted(evidence_set)))
        if len(set(normalized_sets)) != len(normalized_sets):
            raise ValueError(f"评测用例 {case_id} 的充分证据集合不能重复")
        seen_ids.add(case_id)
        validated.append(case)
    return validated


def recall_at_k(
    retrieved_chunk_indexes: Sequence[int],
    relevant_chunk_indexes: Iterable[int],
    k: int,
) -> float:
    """Calculate the fraction of relevant chunks present in the first k results."""
    if k < 1:
        raise ValueError("k 必须大于等于 1")

    relevant = set(relevant_chunk_indexes)
    if not relevant:
        raise ValueError("相关 Chunk 集合不能为空")

    retrieved = set(retrieved_chunk_indexes[:k])
    return len(retrieved & relevant) / len(relevant)


def mean_recall_at_k(
    retrieved_by_case: Sequence[Sequence[int]],
    relevant_by_case: Sequence[Iterable[int]],
    k: int,
) -> float:
    """Calculate macro-average Recall@K, giving every evaluation case equal weight."""
    if len(retrieved_by_case) != len(relevant_by_case):
        raise ValueError("检索结果数量必须与评测用例数量一致")
    if not retrieved_by_case:
        raise ValueError("评测用例不能为空")

    recalls = [
        recall_at_k(retrieved, relevant, k)
        for retrieved, relevant in zip(retrieved_by_case, relevant_by_case)
    ]
    return sum(recalls) / len(recalls)


def sufficient_evidence_hit_at_k(
    retrieved_chunk_indexes: Sequence[int],
    sufficient_evidence_sets: Iterable[Iterable[int]],
    k: int,
) -> int:
    """Return 1 when the first k results fully contain any sufficient evidence set."""
    if k < 1:
        raise ValueError("k 必须大于等于 1")

    evidence_sets = [set(evidence_set) for evidence_set in sufficient_evidence_sets]
    if not evidence_sets or any(not evidence_set for evidence_set in evidence_sets):
        raise ValueError("充分证据集合及其中每一组都不能为空")

    retrieved = set(retrieved_chunk_indexes[:k])
    return int(any(evidence_set.issubset(retrieved) for evidence_set in evidence_sets))


def mean_sufficient_evidence_hit_at_k(
    retrieved_by_case: Sequence[Sequence[int]],
    sufficient_evidence_sets_by_case: Sequence[Iterable[Iterable[int]]],
    k: int,
) -> float:
    """Calculate the fraction of cases with at least one sufficient evidence set hit."""
    if len(retrieved_by_case) != len(sufficient_evidence_sets_by_case):
        raise ValueError("检索结果数量必须与评测用例数量一致")
    if not retrieved_by_case:
        raise ValueError("评测用例不能为空")

    hits = [
        sufficient_evidence_hit_at_k(retrieved, evidence_sets, k)
        for retrieved, evidence_sets in zip(retrieved_by_case, sufficient_evidence_sets_by_case)
    ]
    return sum(hits) / len(hits)


def build_retrieval_report(
    cases: Sequence[dict[str, object]],
    retrieved_by_case: Sequence[Sequence[int]],
    ks: Sequence[int],
) -> dict[str, object]:
    """Build per-case and macro Recall@K results from retrieved chunk indexes."""
    if len(cases) != len(retrieved_by_case):
        raise ValueError("检索结果数量必须与评测用例数量一致")
    if not ks or any(k < 1 for k in ks):
        raise ValueError("K 列表必须包含大于等于 1 的整数")

    relevant_by_case = [case["relevant_chunk_indexes"] for case in cases]
    sufficient_sets_by_case = [case["sufficient_evidence_sets"] for case in cases]
    results = []
    for case, retrieved, relevant, sufficient_sets in zip(
        cases,
        retrieved_by_case,
        relevant_by_case,
        sufficient_sets_by_case,
    ):
        recalls = {f"recall_at_{k}": recall_at_k(retrieved, relevant, k) for k in ks}
        evidence_hits = {
            f"sufficient_evidence_hit_at_{k}": sufficient_evidence_hit_at_k(
                retrieved,
                sufficient_sets,
                k,
            )
            for k in ks
        }
        results.append({
            "id": case["id"],
            "question": case["question"],
            "relevant_chunk_indexes": relevant,
            "sufficient_evidence_sets": sufficient_sets,
            "retrieved_chunk_indexes": list(retrieved),
            **recalls,
            **evidence_hits,
        })

    recall_summary = {
        f"mean_recall_at_{k}": mean_recall_at_k(retrieved_by_case, relevant_by_case, k)
        for k in ks
    }
    evidence_summary = {
        f"mean_sufficient_evidence_hit_at_{k}": mean_sufficient_evidence_hit_at_k(
            retrieved_by_case,
            sufficient_sets_by_case,
            k,
        )
        for k in ks
    }
    summary = {**recall_summary, **evidence_summary}
    return {"case_count": len(cases), "results": results, "summary": summary}
