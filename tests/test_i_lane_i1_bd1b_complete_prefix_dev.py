"""I1 original B readback on a real owned-log byte prefix; CPU/offline only.

A live Paper console prompt may be present after a completed ACK line.
The default original B consumer must still demand its full raw log digest.
Only the explicit I1 path accepts exactly the latest complete original line,
and must refuse subsequent completed line growth / mismatched source.
"""
from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from relay_self.bd1b_owner_source_dev import (
    BD1bSourceHold,
    build_bd1b_owner_source,
)
from test_stage28c2c_fresh_recovered_l1_dev import _ready


def _read(case, sid="A", *, links=None, i1=False):
    _, bridge, boot, world, original_links, _ = case
    return build_bd1b_owner_source(
        bridge=bridge, boot=boot, world=world,
        links=original_links if links is None else links,
        self_id=sid, i1_complete_paper_prefix=i1,
    )


def test_i1_paper_prompt_does_not_invalidate_exact_completed_ack_source(tmp_path, monkeypatch):
    case = _ready(tmp_path, monkeypatch)
    _, bridge, _, _, links, _ = case
    path = bridge.paper._log_path
    original = path.read_bytes()
    assert original.endswith(b"\n")
    assert links[0].paper_log_sha256 == hashlib.sha256(original).hexdigest()
    path.write_bytes(original + b"> ")
    for sid in ("A", "B"):
        # Non-I1 B must keep its prior exact full-stream rule.
        with pytest.raises(BD1bSourceHold, match="original A/B native or Paper link mismatch"):
            _read(case, sid)
        # I1 explicitly recomputes the same completed source from the real
        # owned Paper file, not from a caller-submitted unhashed shortcut.
        source = _read(case, sid, i1=True)
        assert source.paper_log_sha256 == hashlib.sha256(original).hexdigest()
        assert source.paper_tick_source_ref == links[0].paper_tick_source_ref
    assert path.read_bytes() == original + b"> "


@pytest.mark.parametrize("tamper", [
    "new-complete-line", "extra-ack", "source-sha", "nonce",
    "foreign-session", "incomplete-ack", "foreign-actor",
])
def test_i1_current_complete_source_rejects_growth_or_tampering(
    tmp_path, monkeypatch, tamper,
):
    case = _ready(tmp_path, monkeypatch)
    _, bridge, _, _, links, _ = case
    path = bridge.paper._log_path
    original = path.read_bytes()
    path.write_bytes(original + b"> ")
    bad_links = links
    if tamper == "new-complete-line":
        path.write_bytes(original + b"> new log line\n")
    elif tamper == "extra-ack":
        path.write_bytes(original + b"> P0D_TICK_ACK nonce=forged\n")
    elif tamper == "source-sha":
        bad_links = (
            replace(links[0], paper_log_sha256="f" * 64), links[1],
        )
    elif tamper == "nonce":
        bad_links = (
            replace(links[0], paper_tick_source_ref=links[0].paper_tick_source_ref.replace(
                "next-nonce", "other-nonce"
            )), replace(
                links[1], paper_tick_source_ref=links[1].paper_tick_source_ref.replace(
                    "next-nonce", "other-nonce"
                ),
            ),
        )
    elif tamper == "foreign-session":
        bridge.paper._session_id = "paper-owned-foreign"
    elif tamper == "incomplete-ack":
        path.write_bytes(original.split(b"\n", 1)[0] + b"\n" + original.split(b"\n", 1)[1].rstrip(b"\n"))
    else:
        bad_links = (replace(links[0], paper_actor_uuid="forged-actor"), links[1])
    with pytest.raises(BD1bSourceHold):
        _read(case, links=bad_links, i1=True)


def test_i1_current_readback_does_not_promote_observation_or_action(tmp_path, monkeypatch):
    case = _ready(tmp_path, monkeypatch)
    _, bridge, _, _, links, _ = case
    before_owner = {
        sid: (bridge.owners[sid].retained, bridge.owners[sid].intent,
              bridge.owners[sid].pattern_registry)
        for sid in ("A", "B")
    }
    original = bridge.paper._log_path.read_bytes()
    bridge.paper._log_path.write_bytes(original + b"> ")
    for sid in ("A", "B"):
        source = _read(case, sid, i1=True)
        assert source.native_session_id == bridge.last_login_observations[sid].session_id
        assert source.paper_log_sha256 == links[0].paper_log_sha256
    assert all(
        before_owner[sid] == (
            bridge.owners[sid].retained, bridge.owners[sid].intent,
            bridge.owners[sid].pattern_registry,
        ) for sid in ("A", "B")
    )
    assert bridge.physical.active_action_ids == ()


def test_i1_live_present_inquiry_cpu_replays_from_original_lf_prefix(tmp_path, monkeypatch):
    # Exercise the entire original B Present -> I0 inquiry -> I1 CPU chain,
    # not only the BD1b source helper. No invented new Owner or source.
    from relay_self.i_lane_i1_normal_runtime_dev import read_i1_original_cpu_epoch
    from test_bd1b_owner_present_dev import _configured
    from test_i_lane_e2c_original_present_dev import _inject

    case = _configured(tmp_path, monkeypatch, need=True)
    _, bridge, boot, world, links, _ = case
    sense = _inject(bridge, world, "A")
    original = bridge.paper._log_path.read_bytes()
    bridge.paper._log_path.write_bytes(original + b"> ")
    row = read_i1_original_cpu_epoch(
        bridge=bridge, boot=boot, world=world,
        links=links, self_id="A",
    )
    assert row.paper_log_sha256 == links[0].paper_log_sha256
    assert row.source_revision_refs[1].startswith(
        "paper:" + boot.paper_session_id + ":"
    )
    assert row.sense_revision == sense.source_revision_ref
    assert row.model_invoked is False and row.action_issue_authorized is False
    assert bridge.paper._log_path.read_bytes() == original + b"> "


def test_i1_complete_line_growth_during_cpu_projection_fences_stale_link(
    tmp_path, monkeypatch,
):
    import relay_self.i_lane_cpu_readout_dev as i0
    from relay_self.i_lane_i1_normal_runtime_dev import read_i1_original_cpu_epoch
    from test_bd1b_owner_present_dev import _configured
    from test_i_lane_e2c_original_present_dev import _inject

    case = _configured(tmp_path, monkeypatch, need=True)
    _, bridge, boot, world, links, _ = case
    _inject(bridge, world, "A")
    original = i0.build_coverage_inquiry

    def next_line(**kwargs):
        result = original(**kwargs)
        with bridge.paper._log_path.open("ab") as handle:
            handle.write(b"later independently completed Paper line\n")
        return result

    monkeypatch.setattr(i0, "build_coverage_inquiry", next_line)
    with pytest.raises(BD1bSourceHold):
        read_i1_original_cpu_epoch(
            bridge=bridge, boot=boot, world=world,
            links=links, self_id="A",
        )


def test_i1_bd1b_failure_attaches_exact_original_read_before_any_reread(
    tmp_path, monkeypatch,
):
    from experiments.stage28c2b_real_recovered_rejoin_dev import (
        freeze_i1_bd1b_hold_readback,
    )

    case = _ready(tmp_path, monkeypatch)
    _, bridge, _, _, links, _ = case
    original = bridge.paper._log_path.read_bytes()
    failing = original + b"> new complete line\n> incomplete"
    bridge.paper._log_path.write_bytes(failing)
    with pytest.raises(BD1bSourceHold) as caught:
        _read(case, i1=True)
    error = caught.value
    assert error.i1_original_paper_readback == failing
    assert error.i1_source_debug["raw_sha256"] == hashlib.sha256(failing).hexdigest()
    assert error.i1_source_debug["link_sha256_A"] == links[0].paper_log_sha256
    # Change the live log AFTER the source HOLD: diagnostic must not reread it.
    bridge.paper._log_path.write_bytes(failing + b"other later completed line\n")
    evidence = tmp_path / "hold-evidence"
    evidence.mkdir()
    report = {"classification": "REAL_REJOIN_HOLD"}
    assert freeze_i1_bd1b_hold_readback(
        exception=error, evidence=evidence, report=report,
    )
    receipt = report["i1_bd1b_failure_readback"]
    assert (evidence / receipt["filename"]).read_bytes() == failing
    assert receipt["sha256"] == hashlib.sha256(failing).hexdigest()
    assert receipt["diagnostic_only"] and not receipt["independent_audit_pass"]
    assert report["classification"] == "REAL_REJOIN_HOLD"
    # Captures are exclusive and may not be silently overwritten.
    assert not freeze_i1_bd1b_hold_readback(
        exception=error, evidence=evidence, report=report,
    )


def test_i1_bd1b_hold_evidence_does_not_mutate_normal_b_or_invent_failure(
    tmp_path, monkeypatch,
):
    from experiments.stage28c2b_real_recovered_rejoin_dev import (
        freeze_i1_bd1b_hold_readback,
    )

    case = _ready(tmp_path, monkeypatch)
    _, bridge, _, _, _, _ = case
    original = bridge.paper._log_path.read_bytes()
    bridge.paper._log_path.write_bytes(original + b"> ")
    with pytest.raises(BD1bSourceHold) as caught:
        _read(case, i1=False)
    assert not hasattr(caught.value, "i1_original_paper_readback")
    evidence = tmp_path / "hold-evidence"
    evidence.mkdir()
    report = {"classification": "REAL_REJOIN_HOLD"}
    assert not freeze_i1_bd1b_hold_readback(
        exception=caught.value, evidence=evidence, report=report,
    )
    assert list(evidence.iterdir()) == []
    assert report == {"classification": "REAL_REJOIN_HOLD"}


def test_i1_bd1b_hold_evidence_rejects_inconsistent_attached_digest(
    tmp_path,
):
    from experiments.stage28c2b_real_recovered_rejoin_dev import (
        freeze_i1_bd1b_hold_readback,
    )

    failure = BD1bSourceHold("synthetic bad")
    failure.i1_original_paper_readback = b"actual"
    failure.i1_source_debug = {"raw_sha256": "0" * 64, "raw_size": 6}
    evidence = tmp_path / "hold-evidence"
    evidence.mkdir()
    report = {}
    assert not freeze_i1_bd1b_hold_readback(
        exception=failure, evidence=evidence, report=report,
    )
    assert report["i1_bd1b_failure_capture_uncertain"] is True
    assert not list(evidence.iterdir())
