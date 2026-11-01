"""Synthetic original-source tamper controls; no actual model or World."""
from __future__ import annotations

import asyncio
import io
import json
from copy import deepcopy

import pytest

from adapters.mineflayer.l_mp11_live_l2_shadow import (
    BoundedLiveL2,
    JournaledLiveLlamaProvider,
    LiveL2Rejected,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import ProviderExpression, RelayEngine
from test_l_mp11_live_l2_shadow import output
from test_l_mp11_live_previous_action import ACTIONS, MARKERS, accept, new_ledger, snapshot
from tools.l_mp11_feedback_original_audit import audit_feedback_originals


def originals(tmp_path):
    def provider(req, *, mode):
        return ProviderExpression(text=json.dumps(output(req)),
                                  provenance=Provenance("llama.cpp", "synthetic-only"))
    gate = BoundedLiveL2(RelayEngine(provider))
    ledger = new_ledger()
    windows = []
    for n in (1, 2):
        source = accept(ledger, n)
        asyncio.run(gate.propose_after(ledger, freeze_root=tmp_path))
        frozen = json.loads((tmp_path / f"l2-frozen-{n}.json").read_text())
        assert frozen["proposal"]["proposal_sha256"] == gate.proposals[-1].proposal_sha256
        windows.append({"paper_prefix_length": source.paper_prefix_length})
    return json.loads(json.dumps({
        "session_id": ledger.session_id,
        "mp11_g3": {"paper_world_uuid": ledger.world_uuid,
                     "subject_uuid": ledger.subject_uuid, "paper_markers": MARKERS},
        "mp11_g2": {"typed_s16_actions": [
            {"action_id": a, "native_seq": 25*n}
            for n, a in enumerate(ACTIONS, 1)]},
        "l_mp11_live_prefix": {"observations": windows},
        "l_mp11_live_l2": gate.public_report(),
    })), snapshot(3)


def test_original_text_sha_feedback_and_source_reconstructed(tmp_path):
    report, raw = originals(tmp_path)
    assert audit_feedback_originals(report, raw)["h1_to_feedback_to_h2_sha_verified"]
    feedback = json.loads(report["l_mp11_live_l2"]["attempt_originals"][1]
                          ["request"]["context"][2]["value_json"])
    h1 = report["l_mp11_live_l2"]["proposals"][0]
    assert feedback["previous_explanation"] == h1["explanation"]
    assert feedback["previous_falsification_test"] == h1["falsification_test"]
    assert feedback["previous_source_action_id"] == ACTIONS[0]
    assert feedback["target_action_id"] == ACTIONS[1]


@pytest.mark.parametrize("bad", ["text", "sha", "request", "clock", "source", "numeric"])
def test_independent_audit_refuses_tampered_originals(tmp_path, bad):
    report, raw = originals(tmp_path)
    report = deepcopy(report)
    live = report["l_mp11_live_l2"]
    if bad == "text":
        live["attempt_originals"][0]["result"]["text"] = "{}"
    elif bad == "sha":
        live["proposals"][0]["proposal_sha256"] = "a"*64
    elif bad == "request":
        live["attempt_originals"][1]["request"]["context"].pop()
    elif bad == "clock":
        live["attempt_originals"][1]["started_monotonic_ns"] = 1
    elif bad == "source":
        raw = raw.replace(b"tick=100", b"tick=101", 1)
    else:
        live["proposals"][1]["numeric_evidence_refs"][0]["value_m"] = .05
    with pytest.raises((ValueError, KeyError)):
        audit_feedback_originals(report, raw)


def test_reused_freeze_fails_before_next_proposal(tmp_path):
    originals(tmp_path)
    gate = BoundedLiveL2(RelayEngine(lambda req, **k: ProviderExpression(
        text=json.dumps(output(req)), provenance=Provenance("llama.cpp", "synthetic"))))
    ledger = new_ledger()
    accept(ledger, 1)
    with pytest.raises(FileExistsError):
        asyncio.run(gate.propose_after(ledger, freeze_root=tmp_path))
    assert gate.failed_closed and not gate.proposals
    with pytest.raises(LiveL2Rejected):
        asyncio.run(gate.propose_after(ledger, freeze_root=tmp_path))


def test_malformed_http_bytes_preserved_before_decode(tmp_path, monkeypatch):
    import urllib.request
    raw = b'{invalid-original-response\xff'
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: io.BytesIO(raw))
    provider = JournaledLiveLlamaProvider(journal_root=tmp_path,
        endpoint="http://127.0.0.1:8080/v1/chat/completions", model="synthetic")
    with pytest.raises(UnicodeError):
        provider._call({"max_tokens": 512})
    assert (tmp_path / "llama-response-1.raw.json").read_bytes() == raw
    assert "error" in json.loads((tmp_path / "llama-http-1.json").read_text())


def test_cancelled_open_latches_no_next_action_or_retry():
    async def check():
        gate = BoundedLiveL2(RelayEngine(lambda *a, **k: None))
        ledger = new_ledger()
        accept(ledger, 1)
        import unittest.mock
        with unittest.mock.patch("asyncio.to_thread", side_effect=asyncio.CancelledError):
            with pytest.raises(asyncio.CancelledError):
                await gate.propose_after(ledger)
        assert gate.failed_closed and not gate.proposals
        with pytest.raises(LiveL2Rejected):
            await gate.propose_after(ledger)
    asyncio.run(check())
