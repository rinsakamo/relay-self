from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    "README.md",
    "LICENSE",
    "SECURITY.md",
    ".editorconfig",
    ".gitattributes",
    ".ai/README.md",
    "pyproject.toml",
    "src/relay_self/__init__.py",
    "src/relay_self/action.py",
    "src/relay_self/action_supervision.py",
    "src/relay_self/intent.py",
    "tests/test_action_lifecycle.py",
    "tests/test_action_supervision.py",
    "tests/test_intent_commitment.py",
    "docs/ontology.md",
    "docs/architecture.md",
    "docs/runtime-principles.md",
    "docs/development-principles.md",
    "docs/evaluation.md",
    "docs/ci.md",
    "docs/issues.md",
    "docs/contracts/action-lifecycle.md",
    "docs/contracts/action-supervision.md",
    "docs/contracts/intent-commitment.md",
    "docs/migration-from-relaylm.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/ci.yml",
    ".github/ISSUE_TEMPLATE/work.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
]

MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
CONFLICT_MARKER_RE = re.compile(r"^(<<<<<<<|>>>>>>>)(?:\s|$)", re.MULTILINE)
TEXT_SUFFIXES = {".md", ".py", ".yml", ".yaml", ".toml", ".txt"}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def check_required_paths(errors: list[str]) -> None:
    for relative in REQUIRED_PATHS:
        if not (ROOT / relative).exists():
            fail(errors, f"missing required repository path: {relative}")


def iter_markdown_files() -> list[Path]:
    return sorted(path for path in ROOT.rglob("*.md") if ".git" not in path.parts)


def normalize_markdown_target(raw: str) -> str | None:
    target = raw.strip()
    if not target:
        return None

    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()

    # Markdown permits an optional title after a URL. RelaySelf uses simple
    # repository-local links, so only the first whitespace-delimited token is
    # treated as the path when a title is present.
    if " " in target and not target.startswith(("http://", "https://")):
        target = target.split(" ", 1)[0]

    lowered = target.lower()
    if lowered.startswith(("http://", "https://", "mailto:")):
        return None
    if target.startswith("#"):
        return None

    target = target.split("#", 1)[0].split("?", 1)[0]
    target = unquote(target)
    return target or None


def check_markdown_links(errors: list[str]) -> None:
    for markdown in iter_markdown_files():
        text = markdown.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = normalize_markdown_target(raw_target)
            if target is None:
                continue

            resolved = (markdown.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                fail(
                    errors,
                    f"local Markdown link escapes repository: "
                    f"{markdown.relative_to(ROOT)} -> {raw_target}",
                )
                continue

            if not resolved.exists():
                fail(
                    errors,
                    f"broken local Markdown link: "
                    f"{markdown.relative_to(ROOT)} -> {raw_target}",
                )


def check_conflict_markers(errors: list[str]) -> None:
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        if CONFLICT_MARKER_RE.search(text):
            fail(errors, f"unresolved merge-conflict marker: {path.relative_to(ROOT)}")


def main() -> int:
    errors: list[str] = []
    check_required_paths(errors)
    check_markdown_links(errors)
    check_conflict_markers(errors)

    if errors:
        print("Repository contract check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Repository contract check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
