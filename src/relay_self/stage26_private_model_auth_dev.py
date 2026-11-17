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
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit


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


def require_stage26_private_auth_guards(endpoint: str) -> None:
    """Before Paper, prove *anonymous* model access is rejected by server.

    Three negative probes never submit an accepted inference. One-time checks
    bound an honest locally owned dedicated server; they do not prove that a
    future client with the private key cannot connect.
    """
    uri = urlsplit(endpoint)
    if (
        uri.scheme != "http" or uri.hostname != "127.0.0.1"
        or uri.port is None or uri.port < 1024
        or uri.path != "/v1/chat/completions"
        or uri.username or uri.password or uri.query or uri.fragment
    ):
        raise Stage26PrivateAuthError(
            "private inference-client guard requires strict IPv4 loopback endpoint"
        )
    slots = f"http://127.0.0.1:{uri.port}/slots"
    trials = (
        urllib.request.Request(
            slots, method="GET", headers={"Accept": "application/json"},
        ),
        urllib.request.Request(
            slots, method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer stage26-deliberately-invalid",
            },
        ),
        urllib.request.Request(
            endpoint, method="POST", data=b"{}",
            headers={"Content-Type": "application/json"},
        ),
    )
    for request in trials:
        try:
            with urllib.request.urlopen(request, timeout=2.0):
                pass
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                continue
            raise Stage26PrivateAuthError(
                "llama-server model access denied with non-auth HTTP status"
            ) from exc
        except (OSError, ValueError) as exc:
            raise Stage26PrivateAuthError(
                "private inference-client guard is unavailable"
            ) from exc
        raise Stage26PrivateAuthError(
            "llama-server admitted an unauthenticated/wrong-key request"
        )
