"""Stage26 fail-closed original HTTP bytes + terminal token/finish proof.

No real model is invoked. Fake HTTP source has exact wire bytes.
"""
from __future__ import annotations

import hashlib
import json
from unittest.mock import patch

import pytest

from adapters.llama_cpp.relay_engine import (
    LlamaCppProviderError,
    LlamaCppProviderProtocolError,
    LlamaCppRelayProvider,
)
from relay_self.relay_engine import CognitionMode
from test_llama_cpp_relay_engine import FakeResponse, bounded_request, chat_response


def _audited(tmp_path):
    provider = LlamaCppRelayProvider(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="synthetic-model-NOT-GEMMA", timeout=1.0,
    )
    root = tmp_path / "response-source"
    root.mkdir(mode=0o700)
    provider.enable_stage26_raw_audit(root)
    return provider


def _response(*, usage=None, finish="stop"):
    if usage is None:
        usage = {"prompt_tokens": 13, "completion_tokens": 7,
                 "total_tokens": 20}
    return chat_response(
        '{"status":"resolved","choice_id":"cave"}',
        usage=usage, finish_reason=finish,
    )


def test_stage26_raw_source_bytes_and_digest_rechecked(tmp_path):
    provider = _audited(tmp_path)
    req = bounded_request()
    source = _response()
    raw = json.dumps(source).encode("utf-8")
    with patch("urllib.request.urlopen", return_value=FakeResponse(source)) as stub:
        decided = provider(req, mode=CognitionMode.BOUNDED)
    assert stub.call_count == 1
    assert decided.choice_id == "cave"
    receipt = provider.stage26_raw_receipt(req.request_id)
    from pathlib import Path

    assert Path(receipt.response_path).read_bytes() == raw
    assert receipt.response_sha256 == hashlib.sha256(raw).hexdigest()
    request_source = Path(receipt.request_path).read_bytes()
    assert json.loads(request_source)["model"] == "synthetic-model-NOT-GEMMA"
    assert receipt.request_sha256 == hashlib.sha256(request_source).hexdigest()
    assert receipt.response_bytes == len(raw)
    assert decided.call_facts.finish_reason == "stop"
    assert decided.call_facts.total_tokens == 20
    with patch("urllib.request.urlopen") as duplicate:
        with pytest.raises(FileExistsError):
            provider(req, mode=CognitionMode.BOUNDED)
    duplicate.assert_not_called()
    with pytest.raises(LlamaCppProviderError):
        provider.enable_stage26_raw_audit(tmp_path / "response-source")


@pytest.mark.parametrize("usage,finish", [
    (None, None),
    ({"prompt_tokens": 13}, "stop"),
    ({"completion_tokens": 7, "total_tokens": 20}, "stop"),
    ({"prompt_tokens": 13, "completion_tokens": 7}, "stop"),
    ({"prompt_tokens": 13, "completion_tokens": 7, "total_tokens": 21}, "stop"),
    ({"prompt_tokens": 13, "completion_tokens": 7, "total_tokens": 20}, None),
    ({"prompt_tokens": 13, "completion_tokens": 7, "total_tokens": 20}, "length"),
])
def test_stage26_rejects_missing_or_invalid_token_finish_but_keeps_original_source(
    tmp_path, usage, finish,
):
    provider = _audited(tmp_path)
    body = chat_response(
        '{"status":"resolved","choice_id":"cave"}',
        usage=usage, finish_reason=finish,
    )
    req = bounded_request()
    with patch("urllib.request.urlopen", return_value=FakeResponse(body)):
        with pytest.raises(LlamaCppProviderProtocolError):
            provider(req, mode=CognitionMode.BOUNDED)
    receipt = provider.stage26_raw_receipt(req.request_id)
    assert receipt.response_bytes > 0


def test_stage26_rejects_modified_original_response_after_commit(tmp_path):
    provider = _audited(tmp_path)
    req = bounded_request()
    with patch("urllib.request.urlopen", return_value=FakeResponse(_response())):
        provider(req, mode=CognitionMode.BOUNDED)
    receipt = provider.stage26_raw_receipt(req.request_id)
    from pathlib import Path

    Path(receipt.response_path).write_bytes(b'{"modified":true}')
    with pytest.raises(LlamaCppProviderError, match="checksum"):
        provider.stage26_raw_receipt(req.request_id)


def test_stage26_stores_original_malformed_http_json_before_rejecting(tmp_path):
    provider = _audited(tmp_path)
    req = bounded_request()

    class InvalidResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self, *_):
            return b"{invalid JSON"

    with patch("urllib.request.urlopen", return_value=InvalidResponse()):
        with pytest.raises(LlamaCppProviderError):
            provider(req, mode=CognitionMode.BOUNDED)
    receipt = provider.stage26_raw_receipt(req.request_id)
    from pathlib import Path

    assert Path(receipt.response_path).read_bytes() == b"{invalid JSON"


def test_stage26_fail_if_auditor_was_not_armed(tmp_path):
    provider = LlamaCppRelayProvider(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="synthetic", timeout=1.0,
    )
    with pytest.raises(LlamaCppProviderError, match="not enabled"):
        provider.stage26_raw_receipt(bounded_request().request_id)
