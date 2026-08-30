import unittest
from pathlib import Path


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent


class ContainerContractTests(unittest.TestCase):
    def test_image_uses_python_39_and_production_uvicorn_command(self) -> None:
        dockerfile = (PROJECT_DIRECTORY / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("FROM python:3.9-slim", dockerfile)
        self.assertIn('RAG_CMS_DATA_DIR=/app/data/documents', dockerfile)
        self.assertIn('"--host", "0.0.0.0"', dockerfile)
        self.assertNotIn("--reload", dockerfile)

    def test_compose_injects_configuration_and_mounts_data(self) -> None:
        compose = (PROJECT_DIRECTORY / "compose.yaml").read_text(encoding="utf-8")

        self.assertIn("LLM_API_KEY: ${LLM_API_KEY:-}", compose)
        self.assertIn("./data:/app/data", compose)
        self.assertIn('"8000:8000"', compose)

    def test_build_context_excludes_secrets_and_runtime_data(self) -> None:
        ignored = {
            line.strip()
            for line in (PROJECT_DIRECTORY / ".dockerignore").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }

        self.assertIn(".env", ignored)
        self.assertIn("data", ignored)
        self.assertIn(".venv", ignored)


if __name__ == "__main__":
    unittest.main()
