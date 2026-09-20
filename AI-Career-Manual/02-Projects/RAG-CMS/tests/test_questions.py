import asyncio
import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.main import (
    MultiDocumentQuestionRequest,
    QuestionRequest,
    ask_document,
    ask_documents,
)
from app.retrieval import search_documents


class AskDocumentTests(unittest.TestCase):
    def test_returns_answer_and_traceable_citations(self) -> None:
        matches = [
            {
                "document_id": "document-1",
                "chunk_index": 2,
                "content": "发布前必须完成回归测试。",
                "source_path": "document-1/source.md",
                "original_filename": "release.md",
                "start_offset": 20,
                "end_offset": 34,
                "score": 0.91,
            }
        ]
        model_response = {
            "choices": [{"message": {"content": "发布前需要完成回归测试。[来源 1]"}}]
        }
        environment = {
            "LLM_BASE_URL": "https://example.test/v1",
            "LLM_API_KEY": "test-key",
            "LLM_MODEL": "test-model",
        }

        with patch.dict(os.environ, environment, clear=False), \
                patch("app.main.embed_texts", return_value=("embedding-model", [[1.0, 0.0]])), \
                patch("app.main.search_vectors", return_value=matches) as search, \
                patch("app.main.invoke_model", return_value=model_response) as invoke:
            result = asyncio.run(
                ask_document("document-1", QuestionRequest(question=" 发布前要做什么？ ", top_k=1))
            )

        self.assertEqual(result["answer"], "发布前需要完成回归测试。[来源 1]")
        self.assertEqual(result["question"], "发布前要做什么？")
        self.assertEqual(result["citations"][0]["chunk_index"], 2)
        self.assertEqual(result["citations"][0]["original_filename"], "release.md")
        search.assert_called_once_with("document-1", "embedding-model", [1.0, 0.0], 1)
        messages = invoke.call_args.args[0]["messages"]
        self.assertIn("[来源 1]", messages[1]["content"])
        self.assertIn("发布前必须完成回归测试。", messages[1]["content"])

    def test_rejects_whitespace_only_question(self) -> None:
        with self.assertRaises(HTTPException) as context:
            asyncio.run(ask_document("document-1", QuestionRequest(question="   ")))

        self.assertEqual(context.exception.status_code, 422)

    def test_returns_global_top_k_across_documents(self) -> None:
        per_document = {
            "document-1": [
                {"document_id": "document-1", "score": 0.95},
                {"document_id": "document-1", "score": 0.40},
            ],
            "document-2": [
                {"document_id": "document-2", "score": 0.90},
                {"document_id": "document-2", "score": 0.80},
            ],
        }

        with patch("app.retrieval.search_vectors", side_effect=lambda document_id, *_: per_document[document_id]):
            matches = search_documents(
                ["document-1", "document-2"], "embedding-model", [1.0], 2
            )

        self.assertEqual(
            [match["document_id"] for match in matches],
            ["document-1", "document-2"],
        )
        self.assertEqual([match["score"] for match in matches], [0.95, 0.90])

    def test_multi_document_question_deduplicates_ids_and_preserves_sources(self) -> None:
        matches = [
            {
                "document_id": "document-2",
                "chunk_index": 4,
                "content": "开发环境前端使用 staging 构建。",
                "source_path": "document-2/source.md",
                "original_filename": "关键命令.md",
                "start_offset": 40,
                "end_offset": 58,
                "score": 0.93,
            }
        ]
        model_response = {
            "choices": [{"message": {"content": "使用 staging 构建。[来源 1]"}}]
        }
        environment = {
            "LLM_BASE_URL": "https://example.test/v1",
            "LLM_API_KEY": "test-key",
            "LLM_MODEL": "test-model",
        }

        with patch.dict(os.environ, environment, clear=False), \
                patch("app.main.embed_texts", return_value=("embedding-model", [[1.0, 0.0]])), \
                patch("app.main.search_documents", return_value=matches) as search, \
                patch("app.main.invoke_model", return_value=model_response):
            result = asyncio.run(
                ask_documents(MultiDocumentQuestionRequest(
                    document_ids=[" document-1 ", "document-2", "document-1"],
                    question="前端怎么构建？",
                    top_k=2,
                ))
            )

        self.assertEqual(result["document_ids"], ["document-1", "document-2"])
        self.assertEqual(result["citations"][0]["document_id"], "document-2")
        self.assertEqual(result["citations"][0]["original_filename"], "关键命令.md")
        search.assert_called_once_with(
            ["document-1", "document-2"], "embedding-model", [1.0, 0.0], 2
        )

    def test_multi_document_question_rejects_blank_document_id(self) -> None:
        request = MultiDocumentQuestionRequest(
            document_ids=["document-1", "  "], question="问题"
        )

        with self.assertRaises(HTTPException) as context:
            asyncio.run(ask_documents(request))

        self.assertEqual(context.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
