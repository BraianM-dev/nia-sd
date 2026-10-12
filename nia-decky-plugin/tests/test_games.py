import tempfile
import unittest
from pathlib import Path

from backend.helpers.games import scan_installed_games


class GameCatalogTests(unittest.TestCase):
    def test_custom_root_lists_game_folder_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "Heroic"
            game = root / "Example Adventure"
            game.mkdir(parents=True)
            result = scan_installed_games([str(root)])
            found = [item for item in result if item["title"] == "Example Adventure"]
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["platform"], "Heroic")

    def test_custom_steam_library_reads_app_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            library = Path(temp) / "SteamLibrary"
            apps = library / "steamapps"
            (apps / "common" / "Sample Game").mkdir(parents=True)
            (apps / "appmanifest_1234.acf").write_text(
                '"AppState" { "appid" "1234" "name" "Sample Game" "installdir" "Sample Game" }',
                encoding="utf-8",
            )
            result = scan_installed_games([str(library)])
            match = next(item for item in result if item["id"] == "steam:1234")
            self.assertEqual(match["title"], "Sample Game")
            self.assertEqual(match["platform"], "Steam")

    def test_missing_roots_return_a_catalog(self):
        result = scan_installed_games(["/path/that/does/not/exist"])
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
