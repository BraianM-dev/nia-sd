import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
