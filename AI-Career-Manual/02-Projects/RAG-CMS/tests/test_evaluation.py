import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.eval_retrieval import run_retrieval_evaluation
from app.evaluation import build_retrieval_report, load_evaluation_cases, mean_recall_at_k, recall_at_k


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

    def test_builds_per_case_and_summary_report(self) -> None:
        cases = [
            {"id": 1, "question": "问题一", "relevant_chunk_indexes": [1]},
            {"id": 2, "question": "问题二", "relevant_chunk_indexes": [1, 2]},
        ]

        report = build_retrieval_report(cases, [[1, 0], [2, 0]], [1, 2])

        self.assertEqual(report["results"][0]["recall_at_1"], 1.0)
        self.assertEqual(report["results"][1]["recall_at_2"], 0.5)
        self.assertEqual(report["summary"]["mean_recall_at_1"], 0.75)

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
        embed.assert_called_once_with(["A", "B"])
        self.assertEqual(search.call_count, 2)


if __name__ == "__main__":
    unittest.main()
