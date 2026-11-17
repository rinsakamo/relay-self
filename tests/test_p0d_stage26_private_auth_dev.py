"""Stage26 private client authentication contract: offline and fail-closed.

Mocks don't prove authentic llama.cpp security or real Windows client isolation.
"""
from __future__ import annotations

import json
import os
import secrets
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from experiments.p0d_real_preset_checkpoint_dev import (
    RealPresetCheckpointRefusal,
    run_real_two_self_preset_checkpoint,
)
from experiments.p0d_stage26_local_model_preflight import (
    Stage26ModelPreflightHold,
    inspect_stage26_model_source,
)
from relay_self.relay_engine import CognitionMode
from relay_self.resident_llama_inference_lane_dev import LlamaCppSingleSlotWitness
from relay_self.stage26_private_model_auth_dev import (
    Stage26PrivateAuthError,
    load_stage26_private_api_key,
)
from test_llama_cpp_relay_engine import FakeResponse, bounded_request, chat_response
from test_p0d_stage26_local_model_preflight import (
    FakeSlotResponse,
    fixture_sources,
)


def private_key(tmp_path: Path) -> Path:
    key = tmp_path / "private-llama.key"
    key.write_text(secrets.token_urlsafe(48) + "\n", encoding="ascii")
    key.chmod(0o600)
    return key


def test_private_file_and_secret_validation(tmp_path):
    key = private_key(tmp_path)
    assert len(load_stage26_private_api_key(key)) >= 48
    key.chmod(0o644)
    with pytest.raises(Stage26PrivateAuthError):
        load_stage26_private_api_key(key)
    key.chmod(0o600)
    with pytest.raises(Stage26PrivateAuthError):
        load_stage26_private_api_key(Path("relative.key"))
    key.write_text("too-short\n")
    with pytest.raises(Stage26PrivateAuthError):
        load_stage26_private_api_key(key)
    key.write_text("X" * 48 + "\nSECOND-KEY\n")
    with pytest.raises(Stage26PrivateAuthError):
        load_stage26_private_api_key(key)
    key.unlink()
    key.symlink_to(tmp_path / "anything")
    with pytest.raises(Stage26PrivateAuthError):
        load_stage26_private_api_key(key)


def test_private_bearer_headers_apply_to_both_l1_post_and_slot_get(tmp_path):
    key = private_key(tmp_path)
    secret = load_stage26_private_api_key(key)
    provider = LlamaCppRelayProvider(
        endpoint="http://127.0.0.1:8080/v1/chat/completions",
        model="synthetic-BOUNDED", api_key_file=key,
    )
    assert provider.stage26_private_auth_enabled
    seen = []

    def reply(request, timeout=None):
        del timeout
        seen.append(request)
        assert request.get_header("Authorization") == "Bearer " + secret
        if request.get_method() == "GET":
            return FakeSlotResponse([{"id": 0, "is_processing": False}])
        return FakeResponse(chat_response(
            '{"status":"resolved","choice_id":"cave"}',
            usage={"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
        ))

    with patch("urllib.request.urlopen", side_effect=reply) as urlopen:
        slot = LlamaCppSingleSlotWitness(
            provider=provider, backend_ref="stage26-private",
        ).require_idle()
        decision = provider(bounded_request(), mode=CognitionMode.BOUNDED)
    assert len(seen) == 2
    assert urlopen.call_count == 2
    assert slot.n_slots == 1 and not slot.is_processing
    assert decision.choice_id == "cave"
    assert all("Authorization" in request.headers for request in seen)
    assert secret not in json.dumps({
        "model": provider.model, "endpoint": provider.endpoint,
        "slot": slot.source_ref, "decision": decision.choice_id,
    })


def _authenticated_fake_server(request, *, secret, always_accept=False):
    # A real configured llama-server should reject all anonymous and
    # wrong-key probes at auth BEFORE parsing a malformed POST.
    got = request.get_header("Authorization")
    if not always_accept and got != "Bearer " + secret:
        raise urllib.error.HTTPError(
            request.full_url, 401, "Unauthorized", {}, None,
        )
    if request.get_method() == "POST":
        raise AssertionError("authenticated mock should not receive a POST")
    return FakeSlotResponse([{"id": 0, "is_processing": False}])


def test_original_server_argv_key_source_and_unauthorized_negative_guard(tmp_path):
    args = fixture_sources(tmp_path)
    key = private_key(tmp_path)
    cmdline = args["proc_root"] / "42" / "cmdline"
    cmdline.write_bytes(
        cmdline.read_bytes()
        + b"--api-key-file\x00" + os.fsencode(key)
        + b"\x00--cors-origins\x00localhost\x00"
    )
    args["api_key_file"] = key
    secret = load_stage26_private_api_key(key)
    seen = []

    def reply(request, timeout=None):
        del timeout
        seen.append((request.get_method(), request.get_header("Authorization")))
        return _authenticated_fake_server(request, secret=secret)

    with patch("urllib.request.urlopen", side_effect=reply):
        receipt = inspect_stage26_model_source(**args)
    assert receipt.dedicated_api_key_file_attested
    assert receipt.authenticated_slot_verified
    assert receipt.anonymous_slot_denied
    assert receipt.wrong_key_slot_denied
    assert receipt.anonymous_completion_denied
    assert seen == [
        ("GET", "Bearer " + secret),
        ("GET", None),
        ("GET", "Bearer stage26-invalid-credential"),
        ("POST", None),
    ]
    assert not receipt.external_client_absence_attested
    assert not receipt.gpu_wide_exclusivity_attested


@pytest.mark.parametrize("failure", [
    "no-auth-guard", "wrong-key-file", "unsafe-cors", "bad-private-mode",
])
def test_private_preflight_refuses_source_or_auth_guard_failure(tmp_path, failure):
    args = fixture_sources(tmp_path)
    key = private_key(tmp_path)
    cmdline = args["proc_root"] / "42" / "cmdline"
    source = cmdline.read_bytes()
    source += b"--api-key-file\x00" + os.fsencode(key)
    source += b"\x00--cors-origins\x00localhost\x00"
    if failure == "wrong-key-file":
        source = source.replace(os.fsencode(key), b"/foreign/private.key")
    elif failure == "unsafe-cors":
        source = source.replace(b"localhost", b"*")
    elif failure == "bad-private-mode":
        key.chmod(0o644)
    cmdline.write_bytes(source)
    args["api_key_file"] = key
    secret = load_stage26_private_api_key(key) if failure != "bad-private-mode" else ""

    def reply(request, timeout=None):
        del timeout
        return _authenticated_fake_server(
            request, secret=secret,
            always_accept=failure == "no-auth-guard",
        )

    with patch("urllib.request.urlopen", side_effect=reply):
        with pytest.raises((Stage26PrivateAuthError, Stage26ModelPreflightHold)):
            inspect_stage26_model_source(**args)


def test_real_stage26_without_private_key_holds_before_world(tmp_path):
    import asyncio

    with pytest.raises(RealPresetCheckpointRefusal, match="private model API key"):
        asyncio.run(run_real_two_self_preset_checkpoint(
            paper_jar=tmp_path / "absent-paper.jar",
            paper_sha256="0" * 64,
            plugin_jar=tmp_path / "absent-plugin.jar",
            plugin_sha256="0" * 64,
            scratch_parent=tmp_path,
            accepted_eula=True, real_world_dev_grant=True,
            real_gemma_l1=True,
            gemma_l1_endpoint="http://127.0.0.1:8080/v1/chat/completions",
            gemma_l1_model="stage26-gemma",
        ))
    assert not list(tmp_path.glob("p0d-real-preset-cut-*"))
