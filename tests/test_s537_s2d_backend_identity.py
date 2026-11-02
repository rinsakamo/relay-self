"""S2-D identity preflight negatives: no process/model or GPU is launched."""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.s537_s2d_backend_identity import (
    BackendIdentityRejected,
    verify_local_backend,
)


@pytest.mark.parametrize("fault", ["missing_pid", "missing_binary", "invalid_sha", "alias"])
def test_backend_preflight_fails_before_world_or_http(tmp_path, fault):
    binary = tmp_path / "llama-server"
    gguf = tmp_path / "model.gguf"
    binary.write_bytes(b"synthetic invalid backend, do not execute")
    gguf.write_bytes(b"synthetic invalid model")
    args = {
        "pid": 99999999,
        "binary": binary,
        "gguf": gguf,
        "binary_sha256": "0" * 64,
        "gguf_sha256": "1" * 64,
        "alias": "gemma-dev",
        "port": 19434,
    }
    if fault == "missing_pid":
        args["pid"] = -1
    elif fault == "missing_binary":
        args["binary"] = tmp_path / "missing"
    elif fault == "invalid_sha":
        args["gguf_sha256"] = "bad"
    elif fault == "alias":
        args["alias"] = "/bad with spaces"
    with pytest.raises(BackendIdentityRejected):
        verify_local_backend(**args)


def test_backend_identity_does_not_trust_an_unrelated_running_pid(tmp_path):
    binary = Path("/bin/false")
    gguf = tmp_path / "fixture.gguf"
    gguf.write_bytes(b"fixture; not a model")
    with pytest.raises(BackendIdentityRejected):
        verify_local_backend(
            pid=1, binary=binary, gguf=gguf,
            binary_sha256="0" * 64, gguf_sha256="0" * 64,
            alias="fixture-model", port=19283,
        )
