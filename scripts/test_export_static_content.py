import json
import tempfile
import unittest
from pathlib import Path

from scripts.export_static_content import PROJECT_ROOT, export_static_content


class ExportStaticContentTest(unittest.TestCase):
    def test_exports_course_coverage_and_runner_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = export_static_content(Path(directory) / "generated")

            course = json.loads((output / "course.json").read_text(encoding="utf-8"))
            self.assertEqual(course["id"], "fastapi-complete-guide")
            self.assertEqual(len(course["modules"]), 14)
            self.assertEqual(len(course["lessons"]), 111)
            self.assertTrue(all(lesson["execution"]["invocation"] for lesson in course["lessons"]))

            coverage = json.loads((output / "coverage.json").read_text(encoding="utf-8"))
            self.assertEqual(len(coverage["entries"]), 105)

            for name in ("harness.py", "pyodide_shim.py"):
                self.assertEqual(
                    (output / "runner" / name).read_bytes(),
                    (PROJECT_ROOT / "apps" / "runner" / name).read_bytes(),
                )


if __name__ == "__main__":
    unittest.main()
