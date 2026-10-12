import json
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from main import Plugin


class SettingsTests(unittest.TestCase):
    def test_existing_local_ollama_config_moves_to_bundled_llama_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            plugin = Plugin()
            plugin.settings = {"narrator": {
                "provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "qwen2.5:3b",
            }}
            with patch("main.get_config_path", return_value=path):
                plugin._migrate_local_ollama_default()
            self.assertEqual(plugin.settings["narrator"]["provider"], "local-llama")
            self.assertEqual(plugin.settings["narrator"]["model"], "qwen2.5-1.5b-instruct-q4_k_m")
            self.assertEqual(json.loads(path.read_text())["narrator"]["provider"], "local-llama")

    def test_remote_ollama_endpoint_is_preserved(self):
        plugin = Plugin()
        plugin.settings = {"narrator": {
            "provider": "ollama", "endpoint": "http://192.168.1.20:11434", "model": "qwen2.5:3b",
        }}
        plugin._migrate_local_ollama_default()
        self.assertEqual(plugin.settings["narrator"]["provider"], "ollama")
        self.assertEqual(plugin.settings["narrator"]["endpoint"], "http://192.168.1.20:11434")

    def test_resource_check_reports_an_unavailable_provider_as_degraded(self):
        class UnavailableNarrator:
            @staticmethod
            async def probe():
                return {"ok": False, "message": "Falta la clave API"}

        plugin = Plugin()
        plugin.settings = {"narrator": {"provider": "openai"}, "tts": {"enabled": False}}
        plugin.narrator = UnavailableNarrator()
        result = asyncio.run(plugin.verify_resources())
        self.assertEqual(result["status"], "degraded")
        self.assertIn("Falta la clave API", result["details"][0])

    def test_settings_keep_bounded_per_game_voice_and_tone_profiles(self):
        plugin = Plugin()
        with tempfile.TemporaryDirectory() as temp:
            with patch("main.atomic_write_json"), patch("main.get_config_path", return_value=Path(temp) / "config.json"):
                saved = asyncio.run(plugin.settings_set({
                    "game_profiles": {
                        "steam:123": {"persona": "epico", "voice_model": "~/voices/narrator.onnx"},
                        "steam:ignored": {"persona": "unknown", "voice_model": ""},
                    },
                }))
        self.assertEqual(saved["game_profiles"], {
            "steam:123": {"persona": "epico", "voice_model": "~/voices/narrator.onnx"},
        })


if __name__ == "__main__":
    unittest.main()
