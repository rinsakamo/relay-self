"""Stage26 private local llama-server Bearer token contract (DEV only).

The secret is held in a local 0600 key file. Never place it in CLI argv,
a report, evidence files, process stdout or serialized cognitive sources.
This is a scoped client-auth barrier, NOT proof against same-UID readers,
compromised local processes, or network clients that know the key.
"""
from __future__ import annotations

import os
import stat
import string
from pathlib import Path


class Stage26PrivateAuthError(ValueError):
    """Cannot establish locally owned, strong single-key authorization."""


def load_stage26_private_api_key(path: Path) -> str:
    if not isinstance(path, Path) or not path.is_absolute():
        raise Stage26PrivateAuthError("absolute private API key file required")
    try:
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or (info.st_mode & 0o077) != 0
            or info.st_uid != os.geteuid()
        ):
            raise Stage26PrivateAuthError(
                "private API key must be a 0600-or-stricter owned regular file"
            )
        raw = path.read_bytes()
    except OSError as exc:
        raise Stage26PrivateAuthError(
            "cannot read private API key file"
        ) from exc
    if raw.endswith(b"\n"):
        raw = raw[:-1]
    if (
        not 48 <= len(raw) <= 192
        or any(
            chr(byte) not in (string.ascii_letters + string.digits + "-_")
            for byte in raw
        )
    ):
        raise Stage26PrivateAuthError(
            "private API key must be one 48-192 character URL-safe random token"
        )
    # 48+ characters are necessary but not proof of random generation.
    return raw.decode("ascii")


def stage26_bearer_headers(api_key: str) -> dict[str, str]:
    """Internal-only auth headers, never stored in model request source JSON."""
    if not isinstance(api_key, str) or not api_key:
        raise Stage26PrivateAuthError("missing Stage26 private API key")
    return {"Authorization": "Bearer " + api_key}
