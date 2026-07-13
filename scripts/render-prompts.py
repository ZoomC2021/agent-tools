#!/usr/bin/env python3
"""Validate and materialize the deduplicated prompts tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "prompts"
MANIFEST = PROMPTS / "aliases.json"
ALLOWED_KEYS = {"path", "source", "sha256", "mode"}


class ManifestError(ValueError):
    pass


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_mode(path: Path) -> str:
    return "100755" if path.stat().st_mode & stat.S_IXUSR else "100644"


def safe_path(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ManifestError(f"invalid {field}: {value!r}")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        raise ManifestError(f"invalid {field}: {value!r}")
    return value


def load_manifest(prompts: Path = PROMPTS) -> list[dict[str, str]]:
    manifest_path = prompts / "aliases.json"
    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
        document = json.loads(manifest_text)
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read {manifest_path}: {exc}") from exc
    if not isinstance(document, dict) or set(document) != {"version", "aliases"}:
        raise ManifestError("manifest must contain only version and aliases")
    if document["version"] != 1 or not isinstance(document["aliases"], list):
        raise ManifestError("manifest version must be 1 and aliases must be a list")

    aliases = document["aliases"]
    paths: list[str] = []
    for item in aliases:
        if not isinstance(item, dict) or set(item) != ALLOWED_KEYS:
            raise ManifestError("each alias must contain path, source, sha256, and mode")
        alias = safe_path(item["path"], "path")
        source = safe_path(item["source"], "source")
        if alias == "aliases.json" or source == "aliases.json" or alias == source:
            raise ManifestError(f"invalid alias relationship: {alias} -> {source}")
        if item["mode"] not in ("100644", "100755"):
            raise ManifestError(f"invalid mode for {alias}: {item['mode']!r}")
        sha = item["sha256"]
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise ManifestError(f"invalid sha256 for {alias}")
        paths.append(alias)
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ManifestError("aliases must be uniquely ordered by path")
    expected_text = json.dumps(document, indent=2) + "\n"
    if manifest_text != expected_text:
        raise ManifestError("manifest must use deterministic two-space JSON formatting")
    return aliases


def validate(prompts: Path = PROMPTS) -> list[dict[str, str]]:
    aliases = load_manifest(prompts)
    alias_paths = {item["path"] for item in aliases}
    for item in aliases:
        alias = prompts / item["path"]
        source = prompts / item["source"]
        if alias.exists() or alias.is_symlink():
            raise ManifestError(f"alias must be absent from source tree: {item['path']}")
        if item["source"] in alias_paths:
            raise ManifestError(f"source is itself an alias: {item['source']}")
        if not source.is_file() or source.is_symlink():
            raise ManifestError(f"canonical source is not a regular file: {item['source']}")
        if digest(source) != item["sha256"]:
            raise ManifestError(f"sha256 mismatch for canonical source: {item['source']}")
        if file_mode(source) != item["mode"]:
            raise ManifestError(f"mode mismatch for canonical source: {item['source']}")
    return aliases


def render(output: Path, prompts: Path = PROMPTS) -> Path:
    aliases = validate(prompts)
    destination = output / "prompts"
    if destination.exists():
        raise ManifestError(f"destination already exists: {destination}")
    shutil.copytree(prompts, destination, copy_function=shutil.copy2)
    for item in aliases:
        target = destination / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prompts / item["source"], target)
        os.chmod(target, 0o755 if item["mode"] == "100755" else 0o644)
    return destination


def check(prompts: Path = PROMPTS) -> None:
    validate(prompts)
    with tempfile.TemporaryDirectory(prefix="render-prompts-check-") as tmp:
        render(Path(tmp), prompts)


def refresh(prompts: Path = PROMPTS) -> None:
    aliases = load_manifest(prompts)
    alias_paths = {item["path"] for item in aliases}
    for item in aliases:
        alias = prompts / item["path"]
        source = prompts / item["source"]
        if alias.exists() or alias.is_symlink():
            raise ManifestError(f"alias must be absent from source tree: {item['path']}")
        if item["source"] in alias_paths:
            raise ManifestError(f"source is itself an alias: {item['source']}")
        if not source.is_file() or source.is_symlink():
            raise ManifestError(f"canonical source is not a regular file: {item['source']}")
        item["sha256"] = digest(source)
        item["mode"] = file_mode(source)
    document = {"version": 1, "aliases": aliases}
    (prompts / "aliases.json").write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8"
    )
    validate(prompts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    render_parser = subparsers.add_parser("render", help="materialize a complete prompts tree")
    render_parser.add_argument("--output", type=Path, required=True)
    subparsers.add_parser("check", help="validate aliases and perform a temporary render")
    subparsers.add_parser("refresh", help="refresh alias hashes and modes after canonical edits")
    args = parser.parse_args()
    try:
        if args.command == "render":
            render(args.output)
        elif args.command == "refresh":
            refresh()
        else:
            check()
    except ManifestError as exc:
        parser.exit(1, f"render-prompts: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
