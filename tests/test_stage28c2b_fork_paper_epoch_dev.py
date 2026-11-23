"""Stage28c2b: synthetic new Paper process ACK, clock epoch and L1 gate.

These are offline owned-process *fixtures*, not a real Minecraft World trial.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from relay_self.owned_paper_world_dev import OwnedPaperWorld, PaperTickReceipt
from relay_self.resident_llama_inference_lane_dev import LlamaSlotIdleReceipt
from relay_self.stage28_cognitive_recovery_gate_dev import (
    Stage28NativePaperBodyLink,
    Stage28RecoveryHold,
    stage28_require_fresh_l1_eligibility,
)
from relay_self.stage28c2b_execution_copy_dev import create_execution_copy
from relay_self.stage28c2b_fork_paper_epoch_dev import (
    Stage28ForkEpochHold,
    observe_new_fork_paper_epoch,
)
from relay_self.world_resident_lifecycle_dev import NativeLoginEvidence
from test_stage28c2_recovered_resident_owner_dev import _context


def _source(tmp_path: Path, monkeypatch):
    generation, restored, original = _context(tmp_path, monkeypatch)
    copy = create_execution_copy(
        generation, restored, tmp_path / "executable-copy",
        expected_world_id="world-1",
        expected_source_branch_id="source",
        expected_committed_sha256=original.source_commit_sha256,
        expected_fork_branch_id=original.restored_branch_id,
    )
    return copy


def _owned_paper_from_synthetic_log(
    copy, *,
    tick: int = 3, source_session: str = "paper-owned-new-session",
    log_contains_marker: bool = True, tick_ref: str | None = None,
):
    paper = object.__new__(OwnedPaperWorld)
    paper.server_dir = copy.directory.resolve()
    paper.world_dir = (copy.directory / "world").resolve()
    paper.world_id = copy.recovered.plan.source_world_id
    paper.branch_id = copy.recovered.plan.fork_branch_id
    paper._process = SimpleNamespace(pid=9001, poll=lambda: None)
    paper._session_id = source_session
    paper._uncertain = False
    paper._log_path = copy.directory / "synthetic-owned-paper.log"
    boot, nonce = "new-boot-id", "new-nonce"
    paper._log_path.write_text(
        "P0D_TICK_READY boot=new-boot-id source=PAPER_MAIN_THREAD\n"
        + (f"P0D_TICK_ACK nonce={nonce} boot={boot} session={source_session} "
           f"world={paper.world_id} tick={tick} source=PAPER_MAIN_THREAD\n"
           if log_contains_marker else "")
    )
    paper.tick_readback = lambda sid: PaperTickReceipt(
        sid, tick, tick_ref or (
            f"paper-main-thread:p0d:{boot}:{nonce}:sha256:" + "a" * 64
        ),
    )
    return paper


def _new_logins(plan, world, tick):
    return tuple(NativeLoginEvidence(
        sid, idx, world.world_id, world.branch_id,
        world.paper_session_id, world.epoch,
        "new-native-" + sid, tick,
        "original-native-probe-" + sid,
        True, True, True, True, True,
    ) for idx, sid in enumerate(plan.roster, start=1))


def _body_links(world, boot, logins):
    return tuple(Stage28NativePaperBodyLink(
        sid, p.native_session_id, p.observation_ref,
        p.observed_world_tick, p.paper_session_id,
        boot.paper_boot_id, "independent-paper-resident-boot",
        world.world_tick, boot.paper_tick_source_ref,
        "c" * 64, "actor-" + sid,
    ) for sid, p in zip(("A", "B"), logins))


def _idle():
    return LlamaSlotIdleReceipt(
        "new-gpu-owned-process", 0, 1, False, "GET /slots:0:idle",
    )


def _boot(copy, paper, *, historical=()):
    old = tuple(dict(copy.recovered.plan.old_native_sessions).values())
    return observe_new_fork_paper_epoch(
        copy, paper, historical_native_sessions=historical or (
            *old, "native-earlier-A",
        ),
    )


def test_stage28c2b_new_paper_tick_below_saved_tick_is_valid(
    tmp_path, monkeypatch,
):
    copy = _source(tmp_path, monkeypatch)
    paper = _owned_paper_from_synthetic_log(copy, tick=3)
    world, boot = _boot(copy, paper)
    assert world.world_tick == 3
    assert copy.recovered.plan.declared_world_tick == 110
    assert boot.source_declared_tick == 110
    assert boot.boot_tick == 3
    assert boot.old_ticks_directly_comparable is False
    assert boot.replay_authorized is False
    assert boot.physical_action_issue_authorized is False
    assert boot.committed_sha256 == copy.recovered.plan.source_committed_sha256
    assert boot.paper_session_id == paper.owned_session_id
    assert boot.paper_pid == 9001
    assert set(boot.historical_native_sessions) == {
        "native-retired-A", "native-retired-B", "native-earlier-A",
    }
    logins = _new_logins(copy.recovered.plan, world, 4)
    receipt = stage28_require_fresh_l1_eligibility(
        copy.recovered.plan, world=world,
        logins=logins, idle=_idle(), boot=boot,
        links=_body_links(world, boot, logins),
    )
    assert receipt.l1_reevaluation_eligible
    assert receipt.source_saved_world_tick == 110
    assert receipt.new_process_boot_tick == 3
    assert receipt.source_and_new_ticks_comparable is False
    assert receipt.physical_action_issue_authorized is False


@pytest.mark.parametrize("failure", [
    "wrong-original-world", "wrong-fork-branch",
    "wrong-executable-world", "wrong-paper-root", "unstarted-paper",
    "missing-original-history", "bad-session", "no-ack", "wrong-tick-source",
])
def test_stage28c2b_paper_epoch_source_refuses_foreign_boot(
    tmp_path, monkeypatch, failure,
):
    copy = _source(tmp_path, monkeypatch)
    paper = _owned_paper_from_synthetic_log(copy)
    if failure == "wrong-original-world":
        paper.world_id = "foreign-world"
    elif failure == "wrong-fork-branch":
        paper.branch_id = "foreign-branch"
    elif failure == "wrong-executable-world":
        paper.world_dir = tmp_path
    elif failure == "wrong-paper-root":
        paper.server_dir = tmp_path
    elif failure == "unstarted-paper":
        paper._process = None
    elif failure == "missing-original-history":
        with pytest.raises(Stage28ForkEpochHold):
            observe_new_fork_paper_epoch(
                copy, paper, historical_native_sessions=("native-retired-A",),
            )
        return
    elif failure == "bad-session":
        paper._session_id = "foreign-session"
    elif failure == "no-ack":
        paper._log_path.write_text("P0D_TICK_READY boot=new-boot-id source=PAPER_MAIN_THREAD\n")
    elif failure == "wrong-tick-source":
        paper.tick_readback = lambda sid: PaperTickReceipt(sid, 3, "fake:3")
    with pytest.raises(Stage28ForkEpochHold):
        _boot(copy, paper)


@pytest.mark.parametrize("failure", [
    "recycled-first-a", "duplicate-native", "old-owner-session",
    "wrong-paper-session", "wrong-fork", "wrong-epoch",
    "negative-native-world-time", "busy-gpu", "source-commit-mismatch",
    "boot-ref-mismatch", "world-tick-before-boot", "foreign-paper-boot",
])
def test_stage28c2b_l1_eligibility_rejects_stale_or_foreign_clock(
    tmp_path, monkeypatch, failure,
):
    copy = _source(tmp_path, monkeypatch)
    paper = _owned_paper_from_synthetic_log(copy, tick=3)
    world, boot = _boot(copy, paper)
    logins = _new_logins(copy.recovered.plan, world, 4)
    idle = _idle()
    if failure == "recycled-first-a":
        logins = (replace(logins[0], native_session_id="native-earlier-A"), logins[1])
    elif failure == "duplicate-native":
        logins = (logins[0], replace(logins[1], native_session_id=logins[0].native_session_id))
    elif failure == "old-owner-session":
        logins = (replace(logins[0], native_session_id="native-retired-A"), logins[1])
    elif failure == "wrong-paper-session":
        logins = (replace(logins[0], paper_session_id="paper-owned-foreign"), logins[1])
    elif failure == "wrong-fork":
        world = replace(world, branch_id="foreign-fork")
    elif failure == "wrong-epoch":
        logins = (replace(logins[0], world_epoch=0), logins[1])
    elif failure == "negative-native-world-time":
        logins = (replace(logins[0], observed_world_tick=-1), logins[1])
    elif failure == "busy-gpu":
        idle = replace(idle, is_processing=True)
    elif failure == "source-commit-mismatch":
        boot = replace(boot, committed_sha256="f" * 64)
    elif failure == "boot-ref-mismatch":
        boot = replace(boot, paper_tick_source_ref="foreign-source")
    elif failure == "world-tick-before-boot":
        world = replace(world, world_tick=2)
    else:
        boot = replace(boot, paper_boot_id="old-boot")
    with pytest.raises(Stage28RecoveryHold):
        stage28_require_fresh_l1_eligibility(
            copy.recovered.plan, world=world, logins=logins,
            idle=idle, boot=boot,
            links=_body_links(world, boot, logins),
        )


def test_stage28c2b_missing_boot_proof_cannot_authorize_l1(tmp_path, monkeypatch):
    copy = _source(tmp_path, monkeypatch)
    paper = _owned_paper_from_synthetic_log(copy)
    world, _ = _boot(copy, paper)
    logins = _new_logins(copy.recovered.plan, world, 4)
    with pytest.raises(TypeError):
        stage28_require_fresh_l1_eligibility(
            copy.recovered.plan, world=world, logins=logins, idle=_idle(),
        )
