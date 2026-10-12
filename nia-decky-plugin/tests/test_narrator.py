import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from backend.helpers.context_store import NiaStore
from backend.helpers.narrator import NiaNarrator


class NarratorTests(unittest.TestCase):
    def test_offline_fallback_uses_game_and_recorded_event(self):
        with tempfile.TemporaryDirectory() as temp:
            store = NiaStore(Path(temp) / "nia.sqlite3")
            store.record_event("game:sample", "death")
            settings = {"narrator": {"provider": "template", "persona": "amable"}}
            narrator = NiaNarrator(lambda: settings, store)
            result = narrator._narrate_sync(
                {"id": "game:sample", "title": "Prueba del Bosque", "platform": "Heroic"},
                {"type": "death", "detail": ""},
                0,
            )
            self.assertIn("Prueba del Bosque", result["text"])
            self.assertIn("1", result["text"])
            self.assertIn("local", result["status"].lower())

    def test_cloud_provider_presets_send_openai_compatible_chat_requests(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            @staticmethod
            def read(_limit):
                return b'{"choices":[{"message":{"content":"La aventura sigue."}}]}'

        with tempfile.TemporaryDirectory() as temp:
            store = NiaStore(Path(temp) / "nia.sqlite3")
            narrator = NiaNarrator(lambda: {}, store)
            game = {"id": "game:api", "title": "Prueba", "platform": "Steam"}
            event = {"type": "checkpoint", "detail": "Torre"}
            for provider in ("openai", "grok", "deepseek", "gemini"):
                config = {"provider": provider, "api_key": "test-key", "max_tokens": 64}
                with self.subTest(provider=provider), patch(
                    "backend.helpers.narrator.urlopen", return_value=Response()
                ) as mocked:
                    text = narrator._request_model(config, game, event, {}, {}, 0)
                    request = mocked.call_args.args[0]
                    body = json.loads(request.data.decode("utf-8"))
                    self.assertEqual(text, "La aventura sigue.")
                    self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
                    self.assertTrue(request.get_full_url().endswith("/chat/completions"))
                    self.assertEqual(body["messages"][1]["content"].find("Torre") >= 0, True)
                    self.assertIn("max_completion_tokens" if provider == "openai" else "max_tokens", body)


if __name__ == "__main__":
    unittest.main()

