import json
import unittest
from pathlib import Path
from zipfile import ZipFile

from scripts.package_release import build_release


class PackageReleaseTest(unittest.TestCase):
    def test_archive_contains_sources_and_excludes_local_outputs(self) -> None:
        output = Path.cwd() / "release" / ".package-test.zip"
        try:
            build_release(output)

            with ZipFile(output) as archive:
                names = archive.namelist()
                self.assertIn("README.md", names)
                self.assertIn("apps/web/src/App.tsx", names)
                self.assertIn("apps/api/.env.example", names)
                self.assertIn("PACKAGE-MANIFEST.json", names)
                self.assertEqual(names, sorted(names[:-1]) + ["PACKAGE-MANIFEST.json"])
                forbidden = ("node_modules/", ".venv/", "dist/", "generated/", "graphify-out/", "artifacts/", "release/")
                self.assertFalse(any(any(part in name for part in forbidden) for name in names))
                manifest = json.loads(archive.read("PACKAGE-MANIFEST.json"))
                self.assertEqual(len(manifest["files"]), len(names) - 1)
        finally:
            output.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
