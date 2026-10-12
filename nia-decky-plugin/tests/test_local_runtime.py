import hashlib
import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.helpers.local_runtime import LocalRuntime, safe_extract_tar


class LocalRuntimeTests(unittest.TestCase):
    def test_safe_extract_accepts_regular_runtime_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive_path = root / "runtime.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                payload = b"test executable"
                info = tarfile.TarInfo("bin/llama-server")
                info.mode = 0o755
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))

            destination = root / "out"
            safe_extract_tar(archive_path, destination)
            self.assertEqual((destination / "bin/llama-server").read_bytes(), b"test executable")
            self.assertTrue((destination / "bin/llama-server").stat().st_mode & 0o100)

    def test_safe_extract_rejects_parent_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive_path = root / "unsafe.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                payload = b"outside"
                info = tarfile.TarInfo("../escape")
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))

            with self.assertRaises(ValueError):
                safe_extract_tar(archive_path, root / "out")
            self.assertFalse((root / "escape").exists())

    def test_download_reuses_a_complete_verified_partial_file(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = LocalRuntime(Path(temp))
            partial = runtime.root / "complete.part"
            partial.write_bytes(b"already complete")
            digest = hashlib.sha256(partial.read_bytes()).hexdigest()
            with patch("backend.helpers.local_runtime.urlopen", side_effect=AssertionError("network call")):
                runtime._download_verified("https://example.invalid/file", partial, digest, 1024,
                                           "test", 0, 100, min_bytes=1)
            self.assertEqual(runtime.status()["progress"], 100)

    def test_remove_refuses_to_delete_during_an_install(self):
        class RunningTask:
            @staticmethod
            def done():
                return False

        with tempfile.TemporaryDirectory() as temp:
            runtime = LocalRuntime(Path(temp))
            runtime._install_task = RunningTask()
            with self.assertRaises(RuntimeError):
                runtime.remove()


if __name__ == "__main__":
    unittest.main()
