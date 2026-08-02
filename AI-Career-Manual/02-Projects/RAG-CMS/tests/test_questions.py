import asyncio
import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.main import QuestionRequest, ask_document


class AskDocumentTests(unittest.TestCase):
    def test_returns_answer_and_traceable_citations(self) -> None:
        matches = [
            {
                "document_id": "document-1",
                "chunk_index": 2,
                "content": "发布前必须完成回归测试。",
                "source_path": "document-1/source.md",
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
        search.assert_called_once_with("document-1", "embedding-model", [1.0, 0.0], 1)
        messages = invoke.call_args.args[0]["messages"]
        self.assertIn("[来源 1]", messages[1]["content"])
        self.assertIn("发布前必须完成回归测试。", messages[1]["content"])

    def test_rejects_whitespace_only_question(self) -> None:
        with self.assertRaises(HTTPException) as context:
            asyncio.run(ask_document("document-1", QuestionRequest(question="   ")))

        self.assertEqual(context.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
