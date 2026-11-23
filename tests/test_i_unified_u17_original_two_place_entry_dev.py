"""U18: no fabricated S1 callback may enter the real two-MOVE flow."""
from __future__ import annotations

import asyncio
import hashlib
import inspect
from types import SimpleNamespace

import pytest

from experiments.i_unified_u17_original_two_place_trial_dev import (
    U17OriginalS1Settled,
    _verified_pre_s2_paper_prefix,
    run_original_u17_two_place_trial_dev,
)
from relay_self.i_lane_i4a_s1_owned_native_runner_dev import (
    issue_original_s1_place_on_owned_native_dev,
)
from relay_self.i_lane_i4a_s2_owned_native_runner_dev import (
    I4AS2OwnedNativeHold,
    continue_original_s1_to_s2_owned_native_dev,
)


def test_u18_real_s1_calls_original_model_actionport_and_wal_not_external_callback():
    assert inspect.iscoroutinefunction(run_original_u17_two_place_trial_dev)
    assert inspect.iscoroutinefunction(issue_original_s1_place_on_owned_native_dev)
    assert inspect.iscoroutinefunction(continue_original_s1_to_s2_owned_native_dev)
    params = set(inspect.signature(
        run_original_u17_two_place_trial_dev,
    ).parameters)
    assert {
        "bridge", "restored", "s1_operator_permit", "s2_operator_permit",
        "grant_for_action",
    }.issubset(params)
    assert not {"original_s1", "session", "native_sender", "physical_issuer"} & params
    assert U17OriginalS1Settled.__dataclass_fields__["loop"] is not None


def test_u18_no_original_bridge_cannot_enter_model_or_native(tmp_path):
    calls = []

    def forbidden_grants(_binding):
        calls.append("unexpected")
        raise AssertionError("forged S1 must never run")

    with pytest.raises(I4AS2OwnedNativeHold, match="isolated Original B"):
        asyncio.run(run_original_u17_two_place_trial_dev(
            bridge=object(), self_id="B", evidence_dir=tmp_path,
            restored=object(), grant_for_action=forbidden_grants,
            s1_operator_permit=None, s2_operator_permit=None,
            provenance=None, real_world_granted=True,
        ))
    assert calls == []


def test_pre_s2_paper_prefix_accepts_console_redraw_at_record_boundary():
    records = b"starting Paper\nPRESENT RelayB\n"
    raw = records + b"> "
    s1_window = SimpleNamespace(
        log_prefix_size=len(raw), log_prefix_sha256=hashlib.sha256(raw).hexdigest(),
    )
    assert _verified_pre_s2_paper_prefix(raw, s1_window) == records
    assert _verified_pre_s2_paper_prefix(
        raw + b"\r  \rPRESENT RelayB\n", s1_window,
    ).startswith(records)
    for invalid in (raw + b"partial record", raw.replace(b"RelayB", b"RelayC")):
        with pytest.raises(I4AS2OwnedNativeHold, match="not append-only"):
            _verified_pre_s2_paper_prefix(invalid, s1_window)
