from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INCLUDED_ROOTS = (".github", "apps", "content", "docs", "scripts")
INCLUDED_FILES = (
    ".gitignore",
    "README.md",
    "package.json",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
)
EXCLUDED_PARTS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "artifacts",
    "dist",
    "graphify-out",
    "node_modules",
    "release",
}
EXCLUDED_SUFFIXES = (".db", ".pyc", ".tsbuildinfo")
FIXED_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def is_included(path: Path) -> bool:
    relative = path.relative_to(PROJECT_ROOT)
    if any(part in EXCLUDED_PARTS or part.startswith("pytest-cache-files-") for part in relative.parts):
        return False
    if path.name == ".env" or path.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def source_files() -> list[Path]:
    files = [PROJECT_ROOT / name for name in INCLUDED_FILES]
    for root_name in INCLUDED_ROOTS:
        root = PROJECT_ROOT / root_name
        if root.exists():
            files.extend(path for path in root.rglob("*") if is_included(path))
    return sorted({path for path in files if is_included(path)}, key=lambda path: path.as_posix())


def zip_info(name: str) -> ZipInfo:
    info = ZipInfo(name, FIXED_TIMESTAMP)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def build_release(output: Path) -> Path:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files = source_files()
    manifest = {
        "format": 1,
        "files": [
            {
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in files
        ],
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")

    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            name = path.relative_to(PROJECT_ROOT).as_posix()
            archive.writestr(zip_info(name), path.read_bytes())
        archive.writestr(zip_info("PACKAGE-MANIFEST.json"), manifest_bytes)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a deterministic, clean GitHub upload archive.")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "release" / "fastapi-learning-lab.zip",
    )
    args = parser.parse_args()
    output = build_release(args.output)
    print(f"Created {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
