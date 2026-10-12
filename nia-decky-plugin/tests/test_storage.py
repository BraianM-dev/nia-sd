import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.helpers.storage import ensure_default_config


class StorageTests(unittest.TestCase):
    def test_existing_config_permissions_are_restricted_on_load(self):
        if os.name != "posix":
            self.skipTest("Los permisos POSIX no aplican en esta plataforma")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            path.write_text(json.dumps({"narrator": {"api_key": "local-secret"}}), encoding="utf-8")
            os.chmod(path, 0o644)
            with patch("backend.helpers.storage.get_config_path", return_value=path):
                result = ensure_default_config({"narrator": {"api_key": ""}})
            self.assertEqual(result["narrator"]["api_key"], "local-secret")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
