"""U20 scoped negative gates and synthetic HTTP source replay.

No live HTTP, Paper, Native, GPU or World is used by these tests.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import urllib.request
from pathlib import Path

import pytest

from experiments.i_unified_u20_original_b_world_launch_dev import (
    U20OriginalWorldHold,
    _require_isolated_u20_paths,
    run_u20_original_b_world_once,
)
from experiments.i_unified_u20_stage26_raw_provider_dev import (
    U20Stage26RawBoundedProvider,
    U20Stage26RawHold,
)
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionMode,
    DecisionStatus,
)


def test_u20_no_grants_do_not_copy_launch_or_contact_model(tmp_path):
    target = tmp_path / "never-created"
    evidence = tmp_path / "never-evidence"
    with pytest.raises(U20OriginalWorldHold, match="explicit one-run"):
        asyncio.run(run_u20_original_b_world_once(
            generation=tmp_path / "not-present",
            restored=tmp_path / "no-source",
            execution_dir=target, evidence_dir=evidence,
            paper_jar=tmp_path / "paper.jar",
            plugin_jar=tmp_path / "witness.jar",
            gguf=tmp_path / "model.gguf", llama_pid=-1,
            model_alias="no-real-model", llama_endpoint="not-a-url",
            real_world_dev_granted=False, model_post_granted=False,
            accepted_eula=False,
        ))
    assert not target.exists()
    assert not evidence.exists()


def test_u20_source_and_executable_paths_must_be_disjoint(tmp_path):
    archive = tmp_path / "original-archive"
    recovered = tmp_path / "restored-original"
    archive.mkdir()
    recovered.mkdir()
    _require_isolated_u20_paths(
        archive, recovered, tmp_path / "new-world",
        tmp_path / "new-evidence",
    )
    with pytest.raises(U20OriginalWorldHold, match="fresh separated"):
        _require_isolated_u20_paths(
            archive, recovered, recovered / "inside-archive",
            tmp_path / "evidence",
        )
    with pytest.raises(U20OriginalWorldHold, match="fresh separated"):
        _require_isolated_u20_paths(
            archive, recovered, tmp_path / "new-world",
            tmp_path / "new-world" / "nested-evidence",
        )
    existing = tmp_path / "already-existing"
    existing.mkdir()
    with pytest.raises(U20OriginalWorldHold, match="fresh separated"):
        _require_isolated_u20_paths(
            archive, recovered, existing, tmp_path / "new-evidence",
        )


def test_u20_stage26_real_http_entity_source_attaches_to_request_id(
    tmp_path, monkeypatch,
):
    """Mock HTTP transport only; raw input/output is still originally written."""
    request = BoundedChoiceRequest(
        request_id="stage26-original-B-1",
        instruction="Pick the current bounded option",
        intent_id=None, focus=None,
        choices=(BoundedChoice("1", "MOVE"), BoundedChoice("2", "DEFER")),
        context=(), think_allowed=False,
    )
    body = json.dumps({
        "choices": [{
            "message": {"content": json.dumps({
                "status": "resolved", "choice_id": "1",
            })},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 11, "completion_tokens": 6,
            "total_tokens": 17,
        },
    }, separators=(",", ":")).encode()
    sent = []

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def read(self, *_args):
            return body

    def fake_urlopen(req, *, timeout):
        assert isinstance(req, urllib.request.Request)
        assert timeout > 0
        sent.append(req.data)
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    raw_dir = tmp_path / "real-http-shape-synthetic-test"
    raw_dir.mkdir()
    provider = U20Stage26RawBoundedProvider(
        endpoint="http://127.0.0.1:30000/v1/chat/completions",
        model="synthetic-test", raw_dir=raw_dir,
    )
    choice = provider(request, mode=CognitionMode.BOUNDED)
    assert choice.status is DecisionStatus.RESOLVED
    assert choice.choice_id == "1"
    receipt = provider.stage26_raw_receipt(request.request_id)
    assert sent == [Path(receipt.request_path).read_bytes()]
    assert Path(receipt.response_path).read_bytes() == body
    assert receipt.request_sha256 == hashlib.sha256(sent[0]).hexdigest()
    assert receipt.response_sha256 == hashlib.sha256(body).hexdigest()
    assert receipt.response_bytes == len(body)
    with pytest.raises(U20Stage26RawHold, match="cannot replay"):
        provider(request, mode=CognitionMode.BOUNDED)
    assert len(sent) == 1
    with pytest.raises(U20Stage26RawHold, match="no completed"):
        provider.stage26_raw_receipt("foreign-request")
    Path(receipt.response_path).write_bytes(body + b"tampered")
    with pytest.raises(U20Stage26RawHold, match="bytes changed"):
        provider.stage26_raw_receipt(request.request_id)


def test_u20_provider_refuses_non_stage26_requests_without_network(tmp_path):
    source = tmp_path / "empty-http"
    source.mkdir()
    provider = U20Stage26RawBoundedProvider(
        endpoint="http://127.0.0.1:30000/v1/chat/completions",
        model="synthetic-test", raw_dir=source,
    )
    with pytest.raises(U20Stage26RawHold, match="only actual Stage26"):
        provider(object(), mode=CognitionMode.OPEN)
    assert provider.attempted == 0
    assert list(source.iterdir()) == []
