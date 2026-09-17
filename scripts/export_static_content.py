from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "apps" / "web" / "public" / "generated"
RUNNER_FILES = ("harness.py", "pyodide_shim.py")


def export_static_content(output: Path = DEFAULT_OUTPUT) -> Path:
    """Write the API's course and coverage payloads plus runner files for a static build."""
    api_root = str(PROJECT_ROOT / "apps" / "api")
    if api_root not in sys.path:
        sys.path.insert(0, api_root)
    from app.services.content import get_course, get_coverage

    output = output.resolve()
    runner_output = output / "runner"
    runner_output.mkdir(parents=True, exist_ok=True)
    (output / "course.json").write_text(get_course().model_dump_json(), encoding="utf-8")
    (output / "coverage.json").write_text(get_coverage().model_dump_json(), encoding="utf-8")
    for name in RUNNER_FILES:
        shutil.copyfile(PROJECT_ROOT / "apps" / "runner" / name, runner_output / name)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Export course content for the static GitHub Pages build.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    print(export_static_content(parser.parse_args().output))


if __name__ == "__main__":
    main()
