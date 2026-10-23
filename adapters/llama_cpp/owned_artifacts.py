"""Product-owned local artifact hashing, extracted from S55; no process launch."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path


class InvalidLocalQualification(ValueError):
    """Missing or mismatched local model evidence."""


def hash_gguf(path: Path | None, expected: str | None) -> dict[str, object]:
    if expected is not None and not re.fullmatch(r"[a-fA-F0-9]{64}", expected):
        raise InvalidLocalQualification("64-hex SHA256 expected")
    if path is None:
        if expected:
            raise InvalidLocalQualification("model file required for SHA256 bound")
        return {"file_sha256": None, "bytes": None, "loaded_by_backend": False}
    if not isinstance(path, Path) or not path.is_file() or path.suffix.lower() != ".gguf":
        raise InvalidLocalQualification("readable local GGUF file required")
    digest = hashlib.sha256()
    n = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            n += len(block)
            digest.update(block)
    h = digest.hexdigest()
    if expected and h != expected.lower():
        raise InvalidLocalQualification("local GGUF bytes do not match expected SHA256")
    return {
        "file_sha256": h, "bytes": n,
        "matched_expected_hash": expected is not None,
        "loaded_by_backend": False,
    }

