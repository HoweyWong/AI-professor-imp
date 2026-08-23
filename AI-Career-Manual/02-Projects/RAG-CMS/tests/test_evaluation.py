import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.eval_retrieval import load_retrieval_snapshot, run_retrieval_evaluation
from app.evaluation import (
    answer_point_coverage,
    build_four_layer_report,
    build_retrieval_report,
    load_evaluation_cases,
    load_manual_scores,
    mean_recall_at_k,
    mean_sufficient_evidence_hit_at_k,
    recall_at_k,
    sufficient_evidence_hit_at_k,
)


class RecallAtKTests(unittest.TestCase):
    def test_returns_one_when_all_relevant_chunks_are_retrieved(self) -> None:
        self.assertEqual(recall_at_k([2, 1, 0], [1, 2], k=2), 1.0)

    def test_changes_when_k_increases(self) -> None:
        retrieved = [0, 2, 1]

        self.assertEqual(recall_at_k(retrieved, [1, 2], k=1), 0.0)
        self.assertEqual(recall_at_k(retrieved, [1, 2], k=2), 0.5)
        self.assertEqual(recall_at_k(retrieved, [1, 2], k=3), 1.0)

    def test_rejects_empty_relevant_chunks(self) -> None:
        with self.assertRaisesRegex(ValueError, "不能为空"):
            recall_at_k([0, 1], [], k=1)

    def test_calculates_macro_average(self) -> None:
        actual = mean_recall_at_k(
            retrieved_by_case=[[0, 1], [2, 0]],
            relevant_by_case=[[0], [1, 2]],
            k=1,
        )

        self.assertEqual(actual, 0.75)

    def test_rejects_mismatched_case_counts(self) -> None:
        with self.assertRaisesRegex(ValueError, "数量一致"):
            mean_recall_at_k([[0]], [[0], [1]], k=1)

    def test_sufficient_evidence_hit_accepts_any_complete_alternative(self) -> None:
        self.assertEqual(sufficient_evidence_hit_at_k([2, 0], [[1, 3], [2]], k=1), 1)

    def test_sufficient_evidence_hit_requires_the_complete_group(self) -> None:
        self.assertEqual(sufficient_evidence_hit_at_k([2, 2], [[1, 2]], k=2), 0)

    def test_sufficient_evidence_hit_changes_when_k_completes_a_group(self) -> None:
        retrieved = [1, 3, 0]

        self.assertEqual(sufficient_evidence_hit_at_k(retrieved, [[1, 3]], k=1), 0)
        self.assertEqual(sufficient_evidence_hit_at_k(retrieved, [[1, 3]], k=2), 1)

    def test_sufficient_evidence_hit_rejects_empty_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "不能为空"):
            sufficient_evidence_hit_at_k([0], [[]], k=1)

    def test_calculates_mean_sufficient_evidence_hit(self) -> None:
        actual = mean_sufficient_evidence_hit_at_k(
            retrieved_by_case=[[1], [2]],
            sufficient_evidence_sets_by_case=[[[1]], [[2, 3]]],
            k=1,
        )

        self.assertEqual(actual, 0.5)

    def test_calculates_answer_point_coverage(self) -> None:
        self.assertEqual(answer_point_coverage([0], expected_point_count=2), 0.5)

    def test_builds_four_layer_report_from_manual_scores(self) -> None:
        cases_path = Path(__file__).resolve().parents[1] / "evals" / "week-02-cases.json"
        scores_path = (
            Path(__file__).resolve().parents[1] / "evals" / "week-03-manual-scores.json"
        )
        retrieved = [
            [0, 3, 1],
            [0, 3, 1],
            [1, 2, 3],
            [1, 0, 3],
            [1, 3, 0],
            [1, 3, 2],
            [2, 1, 0],
            [1, 2, 0],
            [0, 3, 1],
            [3, 0, 1],
        ]
        cases = load_evaluation_cases(cases_path)
        manual_scores = load_manual_scores(scores_path, cases)

        report = build_four_layer_report(cases, retrieved, [3], manual_scores)

        self.assertAlmostEqual(report["summary"]["mean_recall_at_3"], 0.9166666667)
        self.assertEqual(report["summary"]["mean_sufficient_evidence_hit_at_3"], 1.0)
        self.assertAlmostEqual(report["summary"]["mean_answer_point_coverage"], 0.8833333333)
        self.assertEqual(report["summary"]["citation_faithfulness_rate"], 0.9)
        self.assertEqual(report["results"][3]["manual_evaluation"]["answer_point_coverage"], 0.5)
        self.assertFalse(report["results"][4]["manual_evaluation"]["citation_faithful"])
        self.assertEqual(report["answer_and_citation_scoring_method"], "manual")

    def test_load_manual_scores_rejects_missing_case(self) -> None:
        cases = [
            {"id": 1, "expected_points": ["A"]},
            {"id": 2, "expected_points": ["B"]},
        ]
        content = '{"scores": [' \
                  '{"case_id": 1, "covered_point_indexes": [0],' \
                  ' "citation_faithful": true, "unsupported_claims": [],' \
                  ' "notes": "通过"}]}'
        with TemporaryDirectory() as directory:
            path = Path(directory) / "scores.json"
            path.write_text(content, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "完整覆盖全部评测用例"):
                load_manual_scores(path, cases)

    def test_load_manual_scores_rejects_contradictory_faithfulness(self) -> None:
        cases = [{"id": 1, "expected_points": ["A"]}]
        content = '{"scores": [' \
                  '{"case_id": 1, "covered_point_indexes": [0],' \
                  ' "citation_faithful": true, "unsupported_claims": ["无依据"],' \
                  ' "notes": "矛盾"}]}'
        with TemporaryDirectory() as directory:
            path = Path(directory) / "scores.json"
            path.write_text(content, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "相互矛盾"):
                load_manual_scores(path, cases)

    def test_builds_per_case_and_summary_report(self) -> None:
        cases = [
            {
                "id": 1,
                "question": "问题一",
                "relevant_chunk_indexes": [1],
                "sufficient_evidence_sets": [[1]],
            },
            {
                "id": 2,
                "question": "问题二",
                "relevant_chunk_indexes": [1, 2],
                "sufficient_evidence_sets": [[1, 2]],
            },
        ]

        report = build_retrieval_report(cases, [[1, 0], [2, 0]], [1, 2])

        self.assertEqual(report["results"][0]["recall_at_1"], 1.0)
        self.assertEqual(report["results"][1]["recall_at_2"], 0.5)
        self.assertEqual(report["summary"]["mean_recall_at_1"], 0.75)
        self.assertEqual(report["results"][0]["sufficient_evidence_hit_at_1"], 1)
        self.assertEqual(report["results"][1]["sufficient_evidence_hit_at_2"], 0)
        self.assertEqual(report["summary"]["mean_sufficient_evidence_hit_at_1"], 0.5)

    def test_loads_alternative_sufficient_evidence_sets(self) -> None:
        content = '{"cases": [' \
                  '{"id": 3, "question": "数据库变更需要什么？",' \
                  ' "relevant_chunk_indexes": [0, 1],' \
                  ' "sufficient_evidence_sets": [[0], [1]]}]}'
        with TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(content, encoding="utf-8")

            cases = load_evaluation_cases(path)

        self.assertEqual(cases[0]["sufficient_evidence_sets"], [[0], [1]])

    def test_load_rejects_sufficient_evidence_outside_relevant_chunks(self) -> None:
        content = '{"cases": [' \
                  '{"id": 1, "question": "A", "relevant_chunk_indexes": [0],' \
                  ' "sufficient_evidence_sets": [[1]]}]}'
        with TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(content, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "必须属于相关 Chunk"):
                load_evaluation_cases(path)

    def test_load_rejects_empty_sufficient_evidence_set(self) -> None:
        content = '{"cases": [' \
                  '{"id": 1, "question": "A", "relevant_chunk_indexes": [0],' \
                  ' "sufficient_evidence_sets": [[]]}]}'
        with TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(content, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "每组充分证据"):
                load_evaluation_cases(path)

    def test_load_rejects_duplicate_case_ids(self) -> None:
        content = '{"cases": [' \
                  '{"id": 1, "question": "A", "relevant_chunk_indexes": [0],' \
                  ' "sufficient_evidence_sets": [[0]]},' \
                  '{"id": 1, "question": "B", "relevant_chunk_indexes": [1],' \
                  ' "sufficient_evidence_sets": [[1]]}]}'
        with TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(content, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "唯一整数"):
                load_evaluation_cases(path)

    @patch("app.eval_retrieval.search_vectors")
    @patch("app.eval_retrieval.embed_texts")
    def test_runs_retrieval_evaluation_without_calling_chat_model(self, embed, search) -> None:
        embed.return_value = ("embedding-model", [[1.0], [2.0]])
        search.side_effect = [
            [{"chunk_index": 0}, {"chunk_index": 1}],
            [{"chunk_index": 2}, {"chunk_index": 1}],
        ]
        content = '{"cases": [' \
                  '{"id": 1, "question": "A", "relevant_chunk_indexes": [0],' \
                  ' "sufficient_evidence_sets": [[0]]},' \
                  '{"id": 2, "question": "B", "relevant_chunk_indexes": [1, 2],' \
                  ' "sufficient_evidence_sets": [[1, 2]]}]}'
        with TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(content, encoding="utf-8")

            report = run_retrieval_evaluation("document-1", path, [1, 2])

        self.assertEqual(report["summary"]["mean_recall_at_1"], 0.75)
        self.assertEqual(report["summary"]["mean_recall_at_2"], 1.0)
        self.assertEqual(report["summary"]["mean_sufficient_evidence_hit_at_1"], 0.5)
        self.assertEqual(report["summary"]["mean_sufficient_evidence_hit_at_2"], 1.0)
        embed.assert_called_once_with(["A", "B"])
        self.assertEqual(search.call_count, 2)

    @patch("app.eval_retrieval.search_vectors")
    @patch("app.eval_retrieval.embed_texts")
    def test_replays_saved_retrieval_snapshot_without_external_calls(self, embed, search) -> None:
        project = Path(__file__).resolve().parents[1]

        report = run_retrieval_evaluation(
            "10da35e7-0b7b-4541-9d95-dc70dffc5240",
            project / "evals" / "week-02-cases.json",
            [1, 3],
            project / "evals" / "week-03-manual-scores.json",
            project / "evals" / "week-03-retrieval-snapshot.json",
        )

        self.assertEqual(report["retrieval_mode"], "saved_real_retrieval_snapshot")
        self.assertAlmostEqual(report["summary"]["mean_recall_at_3"], 0.9166666667)
        self.assertEqual(report["summary"]["mean_sufficient_evidence_hit_at_3"], 1.0)
        self.assertEqual(
            report["retrieval_snapshot_metadata"]["run_id"],
            "week-02-real-retrieval-2026-08-06",
        )
        embed.assert_not_called()
        search.assert_not_called()

    def test_retrieval_snapshot_rejects_a_different_document(self) -> None:
        project = Path(__file__).resolve().parents[1]
        cases_path = project / "evals" / "week-02-cases.json"
        cases = load_evaluation_cases(cases_path)

        with self.assertRaisesRegex(ValueError, "document_id"):
            load_retrieval_snapshot(
                project / "evals" / "week-03-retrieval-snapshot.json",
                cases,
                cases_path,
                "different-document",
                3,
            )

    def test_retrieval_snapshot_rejects_a_different_k(self) -> None:
        project = Path(__file__).resolve().parents[1]
        cases_path = project / "evals" / "week-02-cases.json"
        cases = load_evaluation_cases(cases_path)

        with self.assertRaisesRegex(ValueError, "Top-4"):
            load_retrieval_snapshot(
                project / "evals" / "week-03-retrieval-snapshot.json",
                cases,
                cases_path,
                "10da35e7-0b7b-4541-9d95-dc70dffc5240",
                4,
            )


if __name__ == "__main__":
    unittest.main()
