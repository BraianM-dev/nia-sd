import tempfile
import unittest
from pathlib import Path

from backend.helpers.context_store import NiaStore


class ContextStoreTests(unittest.TestCase):
    def test_events_and_duplicate_narrations_are_persisted_per_game(self):
        with tempfile.TemporaryDirectory() as temp:
            store = NiaStore(Path(temp) / "nia.sqlite3")
            store.record_event("steam:1", "death")
            store.record_event("steam:1", "checkpoint")
            store.record_event("steam:2", "death")
            self.assertEqual(store.game_stats("steam:1")["deaths"], 1)
            self.assertEqual(store.game_stats("steam:1")["checkpoints"], 1)
            self.assertEqual(store.game_stats("steam:2")["deaths"], 1)
            self.assertTrue(store.add_narration("steam:1", "death", "A unique line"))
            self.assertFalse(store.add_narration("steam:1", "death", " A UNIQUE  line "))
            self.assertEqual(store.recent_narrations("steam:1"), ["A unique line"])


if __name__ == "__main__":
    unittest.main()
