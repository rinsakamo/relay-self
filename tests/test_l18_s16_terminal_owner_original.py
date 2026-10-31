"""L18 S49 original S16 owner producer; all tests synthetic, no World."""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

import test_l15_s49_original_goal_preflight as l15
from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.l18_s16_terminal_original import (
    L18TerminalOriginalRejected,
    S16_FILE,
    build_s16_owner_original,
    review_saved_s16_owner_original,
    write_s16_owner_original,
)
from adapters.mineflayer.python_protocol import MineflayerStreamDecoder
from relay_self.action_outcome import ActionOutcomeDisposition


def fixture():
    data = l15.s49_original_source()
    typed = MineflayerStreamDecoder()
    frames = [
        typed.decode(line.decode("utf-8"))
        for line in data["received_original"].splitlines(keepends=True)
    ]
    item = data["item"]
    terminal = item.action
    outcome = replace(
        item.outcome, action_ref="MOVE_BACKWARD",
        world_provenance=terminal.provenance,
    )
    a, b, c, d = frames[1], frames[2], frames[3], frames[4]
    movement = ((a.snapshot.position.x-d.snapshot.position.x)**2
                + (a.snapshot.position.z-d.snapshot.position.z)**2)**0.5
    consequence = WorldConsequence(
        action_id=terminal.action_id,
        binding_id=outcome.binding_id,
        action_ref="MOVE_BACKWARD",
        status=WorldConsequenceStatus.EXECUTED,
        session_id=outcome.session_id,
        before_observation=a,
        dispatch_receipt=b,
        cleanup_receipt=c,
        after_observation=d,
        movement_distance=movement,
        cleanup_attempted=True,
        error=None,
        provenance=terminal.provenance,
    )
    return terminal, outcome, consequence, data["received_original"].splitlines(
        keepends=True,
    )[1]


def test_s16_source_owner_original_matches_l13_contract_and_s7_original():
    action, outcome, consequence, pre = fixture()
    raw = build_s16_owner_original(
        terminal=action, outcome=outcome, consequence=consequence,
        original_pre_probe=pre, source_revision=0,
    )
    d = json.loads(raw)
    assert d["schema"] == "L13_S16_TERMINAL_SOURCE_V1"
    assert d["action_id"] == action.action_id
    assert d["session_id"] == outcome.session_id
    assert d["action_ref"] == "MOVE_BACKWARD"
    assert d["pre_probe_sha256"] == hashlib.sha256(pre).hexdigest()
    assert d["before_seq"] == 1 and d["after_seq"] == 4
    assert d["source_status"] == "executed"
    assert d["disposition"] == "outcome"
    assert d["source_revision"] == 0
    assert len(raw.splitlines()) == 1


def test_owner_writes_once_and_readback_remains_unqualified(tmp_path):
    terminal, outcome, consequence, pre = fixture()
    root = tmp_path / "new"
    root.mkdir()
    original = l15.s49_original_source()["received_original"]
    (root / "native_bridge_received_original.jsonl").write_bytes(original)
    meta = write_s16_owner_original(
        capture_root=root, terminal=terminal, outcome=outcome,
        consequence=consequence, source_revision=0,
    )
    result = review_saved_s16_owner_original(
        root=root, s16_index=meta, received_original=original,
        action_id=terminal.action_id, session_id=outcome.session_id,
        before_seq=1, after_seq=4,
    )
    assert result["s16_original_matches_original_pre_probe"]
    assert result["s16_original_sha256"] == meta["sha256"]
    assert result["qualified_real_l10_pairs"] == result["s10_updates"] == 0
    assert not result["independent_physical_authentication"]
    assert not result["independent_goal_original_present"]
    assert (root / S16_FILE).read_bytes() == build_s16_owner_original(
        terminal=terminal, outcome=outcome, consequence=consequence,
        original_pre_probe=pre, source_revision=0,
    )
    with pytest.raises(FileExistsError):
        write_s16_owner_original(
            capture_root=root, terminal=terminal, outcome=outcome,
            consequence=consequence,
        )


@pytest.mark.parametrize("fault", [
    "pre_changed", "wrong_action", "wrong_session", "wrong_ref",
    "unknown_disposition", "failed_consequence", "wrong_before",
    "wrong_cleanup", "wrong_world_owner", "source_revision_negative",
])
def test_incompatible_terminal_cannot_create_l13_source(fault):
    action, outcome, consequence, pre = fixture()
    revision = 0
    if fault == "pre_changed":
        pre = pre.replace(b'"request_id":', b'"request_id":"other","source":')
    elif fault == "wrong_action":
        outcome = replace(outcome, action_id="foreign")
    elif fault == "wrong_session":
        outcome = replace(outcome, session_id="foreign")
    elif fault == "wrong_ref":
        outcome = replace(outcome, action_ref="WAIT")
    elif fault == "unknown_disposition":
        outcome = replace(outcome, disposition=ActionOutcomeDisposition.UNKNOWN)
    elif fault == "failed_consequence":
        consequence = replace(consequence, status=WorldConsequenceStatus.FAILED,
                              error="no execution")
    elif fault == "wrong_before":
        consequence = replace(
            consequence, before_observation=replace(
                consequence.before_observation,
                seq=10,
            ),
        )
    elif fault == "wrong_cleanup":
        consequence = replace(
            consequence, cleanup_receipt=replace(
                consequence.cleanup_receipt,
                action_id="foreign",
            ),
        )
    elif fault == "wrong_world_owner":
        outcome = replace(
            outcome, world_provenance=replace(
                outcome.world_provenance, reference="foreign",
            ),
        )
    elif fault == "source_revision_negative":
        revision = -1
    with pytest.raises((ValueError, TypeError)):
        build_s16_owner_original(
            terminal=action, outcome=outcome, consequence=consequence,
            original_pre_probe=pre, source_revision=revision,
        )


@pytest.mark.parametrize("fault", [
    "source_byte_tamper", "source_original_mismatch", "index_sha",
    "index_action", "index_session", "index_source_revision",
    "index_false_auth", "foreign_before", "foreign_after",
    "missing_file", "symlink_file",
])
def test_saved_s16_original_negative_readback(tmp_path, fault):
    action, outcome, consequence, _ = fixture()
    root = tmp_path / "capture"
    root.mkdir()
    original = l15.s49_original_source()["received_original"]
    (root / "native_bridge_received_original.jsonl").write_bytes(original)
    index = write_s16_owner_original(
        capture_root=root, terminal=action, outcome=outcome,
        consequence=consequence, source_revision=0,
    )
    kw = {
        "root": root, "s16_index": index, "received_original": original,
        "action_id": action.action_id, "session_id": outcome.session_id,
        "before_seq": 1, "after_seq": 4,
    }
    path = root / S16_FILE
    if fault == "source_byte_tamper":
        path.write_bytes(path.read_bytes().replace(b'"before_seq":1', b'"before_seq":3'))
    elif fault == "source_original_mismatch":
        kw["received_original"] = original.replace(
            b'"request_id":', b'"request_id":"changed","spare":', 1,
        )
    elif fault == "index_sha":
        index["sha256"] = "0" * 64
    elif fault == "index_action":
        index["action_id"] = "foreign"
    elif fault == "index_session":
        index["session_id"] = "foreign"
    elif fault == "index_source_revision":
        index["source_revision_operator_declared"] = 99
    elif fault == "index_false_auth":
        index["original_physical_source_authenticated"] = True
    elif fault == "foreign_before":
        kw["before_seq"] = 2
    elif fault == "foreign_after":
        kw["after_seq"] = 5
    elif fault == "missing_file":
        path.unlink()
    elif fault == "symlink_file":
        alt = tmp_path / "elsewhere"
        alt.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(alt)
    with pytest.raises((ValueError, OSError, TypeError)):
        review_saved_s16_owner_original(**kw)


def test_s49_optin_on_terminal_passes_existing_owner_not_new_execution():
    import inspect

    from adapters.mineflayer.normal_action import NormalSessionActionExecutor
    from adapters.mineflayer.s49_normal_session_real_ci import qualify

    assert "on_terminal" in inspect.signature(NormalSessionActionExecutor.execute).parameters
    assert "l16_capture_root" in inspect.signature(qualify).parameters
