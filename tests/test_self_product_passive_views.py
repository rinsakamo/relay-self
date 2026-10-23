"""S49 -> existing SelfBody/SelfWorld read-only DEV join; no physical runner."""
from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from adapters.mineflayer import s49_normal_session_real_ci, self_demo
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_product_passive_views import (
    DEV_SELF_ID,
    PassiveSelfViews,
    PassiveSelfViewsRejected,
    verify_passive_source_join,
)
from relay_self.provenance import Provenance
from test_self_live_think import native_probe


def probe(seq: int, *, sid: str = "p-native", positive: bool = True):
    native = native_probe(seq, 2.0, sid=sid)
    if not positive:
        native = replace(
            native,
            snapshot=replace(
                native.snapshot,
                nearby_entities=(),
                nearby_entities_coverage=replace(
                    native.snapshot.nearby_entities_coverage, candidate_count=0,
                ),
            ),
        )
    return native


def test_three_native_probes_join_existing_body_world_without_policy_change():
    observer = PassiveSelfViews()
    for seq, positive in ((8, True), (19, False), (47, True)):
        observer.observe(probe(seq, positive=positive))
    rows = observer.rows()
    assert len(rows) == 3
    assert [r["native_seq"] for r in rows] == [8, 19, 47]
    assert [r["observed_world_entities"] for r in rows] == [1, 0, 1]
    for r in rows:
        assert r["self_id"] == DEV_SELF_ID
        assert r["body_world_exact_source_join"] is True
        assert r["session_id"] == "p-native"
        assert r["body_source_ref"] == (
            f"native-probe:p-native:{r['native_seq']}:{r['request_id']}"
        )
        assert r["world_source_ref"] == (
            f"present:p-native:{r['native_seq']}:{r['request_id']}"
        )
        assert r["health_observed"] is not None
        assert r["food_observed"] is not None
        assert r["world_safe"] is None
        assert r["unobserved_world_absent"] is None
        assert not r["action_issued"] and not r["action_authorized"]
        assert r["model_calls"] == r["s10_commits"] == r["memory_writes"] == 0
    assert observer.summary()["native_probes_joined"] == 3
    assert observer.summary()["observer_errors"] == []
    assert observer.summary()["source_qualified"] is False


@pytest.mark.parametrize("attack", [
    "duplicate", "stale", "foreign", "uncorrelated", "bad_provenance",
    "missing_kind", "extra_fourth",
])
def test_native_source_and_bounded_epoch_negatives(attack):
    owner = PassiveSelfViews()
    owner.observe(probe(8))
    if attack == "duplicate":
        invalid = probe(8)
    elif attack == "stale":
        invalid = probe(7)
    elif attack == "foreign":
        invalid = probe(19, sid="foreign")
    elif attack == "uncorrelated":
        invalid = replace(probe(19), request_id="unsolicited")
    elif attack == "bad_provenance":
        class ForeignProvenance(MineflayerObservation):
            @property
            def provenance(self):
                return Provenance("mineflayer", "different:19")

        original = probe(19)
        invalid = ForeignProvenance(
            session_id=original.session_id, seq=original.seq, kind=original.kind,
            snapshot=original.snapshot, request_id=original.request_id,
        )
    elif attack == "missing_kind":
        invalid = replace(probe(19), kind="health", request_id=None)
    else:
        owner.observe(probe(19))
        owner.observe(probe(47))
        invalid = probe(58)
    with pytest.raises((PassiveSelfViewsRejected, ValueError)):
        owner.observe(invalid)
    assert owner.summary()["native_probes_joined"] == (
        3 if attack == "extra_fourth" else 1
    )


def test_original_s49_callback_only_runs_passive_projection(monkeypatch, tmp_path):
    seen = []

    async def fake_original_s49(report_path, server_log, *, live_probe=None):
        assert live_probe is not None
        for seq in (8, 19, 47):
            await live_probe(probe(seq))
            seen.append(seq)
        return 0

    monkeypatch.setattr(s49_normal_session_real_ci, "qualify", fake_original_s49)
    result = asyncio.run(self_demo._run_disposable(
        tmp_path / "report.json", tmp_path / "server.log",
        passive_self_views=True,
    ))
    assert result == 0
    assert seen == [8, 19, 47]
    source = tmp_path / "self_views.jsonl"
    lines = [json.loads(x) for x in source.read_text().splitlines()]
    assert len(lines) == 4
    assert [r["native_seq"] for r in lines[:3]] == [8, 19, 47]
    summary = lines[-1]
    assert summary["native_probes_joined"] == 3
    assert summary["extra_native_probes"] == 0
    assert summary["action_issuer"] == "EXISTING_S49_ONLY"
    assert summary["source_qualified"] is False
    assert summary["s10_commits"] == 0
    assert not (tmp_path / "report.json").exists()  # stub did not forge an S49 report


def test_passive_errors_never_veto_original_l0(monkeypatch, tmp_path):
    async def fake_original_s49(report_path, server_log, *, live_probe=None):
        for native in (probe(8), probe(8), probe(19)):
            await live_probe(native)
        return 0

    monkeypatch.setattr(s49_normal_session_real_ci, "qualify", fake_original_s49)
    assert asyncio.run(self_demo._run_disposable(
        tmp_path / "report.json", tmp_path / "server.log",
        passive_self_views=True,
    )) == 0
    lines = [json.loads(x) for x in (tmp_path / "self_views.jsonl").read_text().splitlines()]
    assert lines[-1]["native_probes_joined"] == 2
    assert lines[-1]["observer_errors"] == ["PassiveSelfViewsRejected"]
    # Outer DEV receipt must subsequently refuse to call this qualified.
    assert lines[-1]["source_qualified"] is False


@pytest.mark.parametrize("kwargs", [
    {"stage_r_dev": True},
    {"raw_capture_root": Path("/tmp/raw")},
    {"self_world_live": True},
])
def test_nonexclusive_modes_fail_before_original_owner(monkeypatch, tmp_path, kwargs):
    async def unreachable(*args, **params):
        raise AssertionError("original S49 should not be called")

    monkeypatch.setattr(s49_normal_session_real_ci, "qualify", unreachable)
    with pytest.raises(self_demo.DemoRejected):
        asyncio.run(self_demo._run_disposable(
            tmp_path / "report.json", tmp_path / "server.log",
            passive_self_views=True, **kwargs,
        ))
    assert not (tmp_path / "self_views.jsonl").exists()


def test_passive_option_requires_dev_mode():
    with pytest.raises(SystemExit) as err:
        self_demo.main(["--self-passive-views", "--smoke"])
    assert err.value.code == 2


def _source_report_and_rows():
    observer = PassiveSelfViews()
    seqs = (8, 19, 47)
    for seq in seqs:
        observer.observe(probe(seq))
    native = {
        "session_id": "p-native",
        "source_pair_trace": [
            {"event_seq": seq - 1, "probe_seq": seq,
             "probe_entities": [{"id": seq, "name": "zombie"}]}
            for seq in seqs
        ],
    }
    return native, [*observer.rows(), observer.summary()]


def test_native_report_and_self_views_validated_without_source_qualification():
    native, rows = _source_report_and_rows()
    assert verify_passive_source_join(native, rows)
    assert rows[-1]["source_qualified"] is False


@pytest.mark.parametrize("attack", (
    "foreign_session", "wrong_probe_seq", "wrong_event_id",
    "invented_positive", "false_safety", "action_authority",
    "hidden_model", "s10_commit", "foreign_source_ref",
    "missing_row", "observer_error", "pretend_attested",
))
def test_sidecar_substitutions_never_promote_source(attack):
    native, rows = _source_report_and_rows()
    native, rows = deepcopy(native), deepcopy(rows)
    if attack == "foreign_session":
        rows[0]["session_id"] = "another"
    elif attack == "wrong_probe_seq":
        rows[0]["native_seq"] = 9
    elif attack == "wrong_event_id":
        native["source_pair_trace"][0]["event_seq"] = 999
    elif attack == "invented_positive":
        rows[0]["observed_world_entities"] = 9
    elif attack == "false_safety":
        rows[0]["world_safe"] = True
    elif attack == "action_authority":
        rows[0]["action_authorized"] = True
    elif attack == "hidden_model":
        rows[-1]["model_calls"] = 1
    elif attack == "s10_commit":
        rows[0]["s10_commits"] = 1
    elif attack == "foreign_source_ref":
        rows[0]["world_source_ref"] = "present:other"
    elif attack == "missing_row":
        rows.pop(0)
    elif attack == "observer_error":
        rows[-1]["observer_errors"] = ["ValueError"]
    elif attack == "pretend_attested":
        rows[-1]["source_qualified"] = True
    assert not verify_passive_source_join(native, rows)


@pytest.mark.parametrize("attack", ["epoch", "session", "source"])
def test_composition_rejects_body_world_mismatch(monkeypatch, attack):
    from adapters.mineflayer import self_product_passive_views as passive

    original = passive.compose_self_body_view

    def mismatched(**kwargs):
        body = original(**kwargs)
        if attack == "epoch":
            return replace(body, epoch_id="foreign-epoch")
        if attack == "session":
            return replace(body, session_id="foreign-session")
        return replace(body, observation=replace(
            body.observation, native_seq=999,
        ))

    monkeypatch.setattr(passive, "compose_self_body_view", mismatched)
    observer = PassiveSelfViews()
    with pytest.raises(ValueError):
        observer.observe(probe(8))
    assert observer.rows() == ()


@pytest.mark.parametrize("attack", [None, "sidecar", "source", "action"])
def test_outer_dev_receipt_checks_passive_join(monkeypatch, tmp_path, attack):
    from types import SimpleNamespace

    monkeypatch.setattr(self_demo.shutil, "which", lambda _: "/tool")
    monkeypatch.setattr(self_demo.subprocess, "run", lambda *a, **kw:
                        SimpleNamespace(returncode=0, stdout="version", stderr=""))

    async def owner(report, log, *, passive_self_views):
        assert passive_self_views is True
        native, rows = _source_report_and_rows()
        native.update(status="PASS", server_exit=0)
        if attack == "sidecar":
            rows[0]["world_source_ref"] = "foreign"
        elif attack == "source":
            native["session_id"] = "foreign"
        elif attack == "action":
            rows[0]["action_issued"] = True
        report.write_text(json.dumps(native))
        (report.parent / "self_views.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows)
        )
        return 0

    monkeypatch.setattr(self_demo, "_run_disposable", owner)
    from test_self_dev import args

    root = tmp_path / "receipt"
    result = self_demo._dev_run(args(root, self_passive_views=True))
    receipt = json.loads((root / "dev_receipt.json").read_text())
    assert result == (0 if attack is None else 1)
    assert receipt["dev_passive_self_views"] == (
        "SOURCE_JOINED_DEV_ONLY" if attack is None else "UNDETERMINED"
    )
    assert receipt["engineering_qualified"] is False
    assert receipt["science_success"] is False
