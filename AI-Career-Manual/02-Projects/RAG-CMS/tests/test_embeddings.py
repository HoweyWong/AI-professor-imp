import unittest
from unittest.mock import patch

from app.embeddings import embed_texts


class EmbedTextsTests(unittest.TestCase):
    def test_splits_inputs_into_provider_safe_batches(self) -> None:
        texts = [f"text-{index}" for index in range(21)]

        def fake_invoke(batch, _base_url, _api_key, _model):
            return [[float(text.split("-")[1])] for text in batch]

        with patch(
            "app.embeddings.embedding_settings",
            return_value=("https://example.test/v1", "test-key", "test-model"),
        ), patch(
            "app.embeddings.invoke_embedding_batch", side_effect=fake_invoke
        ) as invoke:
            model, vectors = embed_texts(texts)

        self.assertEqual(model, "test-model")
        self.assertEqual(len(vectors), 21)
        self.assertEqual(
            [len(call.args[0]) for call in invoke.call_args_list],
            [10, 10, 1],
        )


if __name__ == "__main__":
    unittest.main()
