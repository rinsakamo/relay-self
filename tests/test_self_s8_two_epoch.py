"""S8 offline/synthetic TWO-epoch controlled World integration tests.

No user WSL2 host, Java/Node, actual Minecraft or model inference.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

import test_postmain_s42_world_contrast as s42
from adapters.mineflayer import self_s1_runtime as s1
from adapters.mineflayer import self_s8_trial as trial
from adapters.mineflayer.self_continuous_host import SessionBudget, SessionRunRejected
from adapters.mineflayer.self_s7_native_trial import CONSUMED_S6_GRANT
from adapters.mineflayer.self_s8_two_epoch import (
    CLEAR,
    SUMMON,
    S8InterventionRejected,
    S8TwoEpochIntervention,
    S8TwoEpochPlan,
)
from test_self_continuous_host import _fixture

REF = "https://github.com/rinsakamo/relay-self/issues/537#issuecomment-987654321"


class FakeStdin:
    def __init__(self, fail_at=None):
        self.commands = []
        self.drains = 0
        self.fail_at = fail_at

    def write(self, raw):
        self.commands.append(raw)

    async def drain(self):
        self.drains += 1
        if self.drains == self.fail_at:
            raise OSError("uncertain original server delivery")


def _controller(driver, *, fail_at=None):
    spawn = replace(s42._pair()[3], session_id=driver.host.session_id,
                    kind="spawn", seq=2)
    server = SimpleNamespace(returncode=None, stdin=FakeStdin(fail_at=fail_at))
    owner = S8TwoEpochIntervention(S8TwoEpochPlan(REF), spawn, driver.events)
    # Build synthetic fixture before asyncio.run; S42 builds retained state via
    # its own offline asyncio runner, which must not be nested in callbacks.
    owner._test_clearance_template = s42._pair()[1].observation
    return owner, server


def _rows(tmp_path):
    return [json.loads(x) for x in (tmp_path / "events.jsonl").read_text().splitlines()]


def _native_clearance(owner, *, zombies=(), foreign=False, truncated=False,
                      non_target=False, stale=False):
    """Actual native-message SHAPE, not an actual World/source receipt."""
    near = owner._test_clearance_template
    original = near.snapshot.nearby_entities[0]
    members = tuple(replace(original, entity_id=n) for n in zombies)
    if non_target:
        members += (replace(original, name="item", entity_id=42),)
    if truncated:
        bound = near.snapshot.nearby_entities_coverage.max_entities
        members = tuple(
            replace(original, entity_id=1000 + n, name="item")
            for n in range(bound)
        )
    coverage = replace(
        near.snapshot.nearby_entities_coverage,
        candidate_count=(len(members) + 1 if truncated else len(members)),
        truncated=truncated,
    )
    snapshot = replace(near.snapshot, nearby_entities=members,
                       nearby_entities_coverage=coverage)
    calls = []

    async def observe(request_id):
        calls.append(request_id)
        return replace(
            near, session_id=("foreign" if foreign else owner.sink.session_id),
            kind="probe", request_id=request_id,
            seq=(1 if stale else 100 + len(calls)),
            snapshot=snapshot,
        )

    observe.calls = calls
    return observe


def test_second_external_target_follows_closed_action_and_retained_memory(tmp_path):
    driver, probe, grant, execute, _, _ = _fixture(tmp_path)
    owner, server = _controller(driver)
    seen = []

    async def closed(step, receipt):
        assert any(x["kind"] == "action_outcome" for x in _rows(tmp_path))
        seen.append((step, receipt))
        await owner.after_action_closed(server, step, receipt, memory_count=1,
                                        clearance_probe=_native_clearance(owner))

    result = asyncio.run(driver.run(
        probe=probe, grant=grant, on_action=execute,
        on_session_started=lambda: owner.submit_first(server),
        on_outcome_closed=closed,
    ))
    assert result["closed_outcomes"] == 1
    assert owner.commands_attempted == 3
    assert owner.second_closed is False
    assert any(r["kind"] == "s9_clearance_native_verified" for r in _rows(tmp_path))
    assert seen
    assert server.stdin.commands == [
        (SUMMON + "\n").encode(), (CLEAR + "\n").encode(), (SUMMON + "\n").encode(),
    ]
    kinds = [x["kind"] for x in _rows(tmp_path)]
    assert kinds.index("action_outcome") < kinds.index("s8_epoch1_closed_memory_retained")
    assert kinds.count("s8_external_command_intent") == 3
    assert all(not x.get("command_executed_attested", False) for x in _rows(tmp_path))
    assert all(not x.get("goal_success_attested", False) for x in _rows(tmp_path))
    assert all(not x.get("habit_granted", False) for x in _rows(tmp_path))


def test_no_retained_memory_blocks_second_target_after_first_outcome(tmp_path):
    driver, probe, grant, execute, _, _ = _fixture(tmp_path)
    owner, server = _controller(driver)
    async def closed(step, receipt):
        await owner.after_action_closed(server, step, receipt, memory_count=0,
                                        clearance_probe=_native_clearance(owner))

    with pytest.raises(S8InterventionRejected, match="not retained"):
        asyncio.run(driver.run(
            probe=probe, grant=grant, on_action=execute,
            on_session_started=lambda: owner.submit_first(server),
            on_outcome_closed=closed,
        ))
    assert owner.commands_attempted == 1
    kinds = [x["kind"] for x in _rows(tmp_path)]
    assert "action_outcome" in kinds
    assert kinds[-1] == "session_failed"
    assert not any(x == "clear_tagged_epoch1" for x in (
        r.get("stage") for r in _rows(tmp_path)
    ))


def test_failed_outcome_never_submits_second_target(tmp_path):
    driver, probe, grant, _, _, _ = _fixture(tmp_path)
    owner, server = _controller(driver)
    async def wrong(_step):
        return {"fake": True}
    async def forbidden(_step, _receipt):
        pytest.fail("invalid terminal cannot trigger stage 2")

    with pytest.raises(SessionRunRejected):
        asyncio.run(driver.run(
            probe=probe, grant=grant, on_action=wrong,
            on_session_started=lambda: owner.submit_first(server),
            on_outcome_closed=forbidden,
        ))
    assert owner.commands_attempted == 1
    assert len(server.stdin.commands) == 1


def test_ambiguous_second_command_does_not_retry(tmp_path):
    driver, probe, grant, execute, _, _ = _fixture(tmp_path)
    owner, server = _controller(driver, fail_at=2)
    async def closed(step, receipt):
        await owner.after_action_closed(
            server, step, receipt, memory_count=1,
            clearance_probe=_native_clearance(owner),
        )

    with pytest.raises(OSError):
        asyncio.run(driver.run(
            probe=probe, grant=grant, on_action=execute,
            on_session_started=lambda: owner.submit_first(server),
            on_outcome_closed=closed,
        ))
    assert owner.commands_attempted == 2  # summon1 then ambiguous clear
    assert len(server.stdin.commands) == 2
    assert _rows(tmp_path)[-1]["no_replay"] is True


def test_second_action_requires_distinct_entity_and_action_id(tmp_path):
    driver, probe, grant, execute, _, _ = _fixture(tmp_path)
    owner, server = _controller(driver)
    captured = []
    async def closed(step, receipt):
        captured.append((step, receipt))
        await owner.after_action_closed(
            server, step, receipt, memory_count=1,
            clearance_probe=_native_clearance(owner),
        )

    asyncio.run(driver.run(
        probe=probe, grant=grant, on_action=execute,
        on_session_started=lambda: owner.submit_first(server),
        on_outcome_closed=closed,
    ))
    step, receipt = captured[0]
    with pytest.raises(S8InterventionRejected, match="distinct"):
        asyncio.run(owner.after_action_closed(server, step, receipt, memory_count=2,
                                        clearance_probe=_native_clearance(owner)))
    assert owner.second_closed is False
    assert len(server.stdin.commands) == 3


@pytest.mark.parametrize("ref", [
    "", "https://github.com/rinsakamo/relay-self/issues/537",
    "https://github.com/rinsakamo/relay-self/issues/537#issuecomment-0",
])
def test_external_reference_shape_rejected(ref):
    with pytest.raises(S8InterventionRejected):
        S8TwoEpochPlan(ref)


def test_s8_opt_in_requires_original_capture_before_world(tmp_path):
    with pytest.raises(SessionRunRejected, match="requires prospective S7"):
        asyncio.run(s1.run_physical(
            None, tmp_path, SessionBudget(), controlled_target=S8TwoEpochPlan(REF),
            capture_native_originals=False,
        ))


def test_dry_run_is_host_effect_free(monkeypatch, capsys):
    monkeypatch.setattr(trial.s1, "preflight", lambda *_:
                        pytest.fail("dry-run preflight must not run"))
    assert trial.main([]) == 0
    assert json.loads(capsys.readouterr().out)["classification"] == "S8_DRY_RUN_NO_EFFECTS"


def test_consumed_s6_authorization_cannot_be_reused(monkeypatch, capsys):
    monkeypatch.setattr(trial.s1, "preflight", lambda *_:
                        pytest.fail("consumed authority cannot reach host"))
    assert trial.main([
        "--run-disposable", "--confirm", trial.CONFIRM,
        "--standing-eula-confirmed",
        "--authorization-reference", CONSUMED_S6_GRANT,
        "--output-dir", "/tmp/nonexistent-operator-output",
    ]) == 2
    assert "S8_NEW_TWO_EPOCH_AUTHORITY_REQUIRED" in capsys.readouterr().out


def test_s6_worktree_repair_permission_also_spent(monkeypatch, capsys):
    monkeypatch.setattr(trial.s1, "preflight", lambda *_:
                        pytest.fail("spent S6 worktree grant cannot reach host"))
    assert trial.main([
        "--run-disposable", "--confirm", trial.CONFIRM,
        "--standing-eula-confirmed",
        "--authorization-reference",
        "https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6116304704",
        "--output-dir", "/tmp/nonexistent-operator-output",
    ]) == 2
    assert "S8_NEW_TWO_EPOCH_AUTHORITY_REQUIRED" in capsys.readouterr().out


def test_s8_bounded_caps_checked_before_preflight(monkeypatch, capsys):
    monkeypatch.setattr(trial.s1, "preflight", lambda *_:
                        pytest.fail("budget violation cannot reach host"))
    assert trial.main([
        "--run-disposable", "--confirm", trial.CONFIRM,
        "--standing-eula-confirmed", "--authorization-reference", REF,
        "--output-dir", "/tmp/nonexistent-operator-output",
        "--max-actions", "3",
    ]) == 2
    assert "S8_PHYSICAL_UNKNOWN_OR_BLOCKED" in capsys.readouterr().out


def test_offline_stub_does_not_infer_learning_or_goal(tmp_path, monkeypatch, capsys):
    output = tmp_path / "new"
    output.mkdir()
    called = []
    monkeypatch.setattr(trial.s1, "preflight", lambda *_: object())
    monkeypatch.setattr(trial, "assess_qualified_rsee_world", lambda *_:
                        SimpleNamespace(classification="FROZEN_WORLD_NATURAL_MOB_SPAWNING_DISABLED"))

    async def synthetic_run(_binding, _out, budget, *, controlled_target,
                            capture_native_originals):
        called.append(True)
        assert budget.max_actions == 2
        assert isinstance(controlled_target, S8TwoEpochPlan)
        assert capture_native_originals is True
        return {
            "node_exit": 0, "server_exit": 0, "closed_outcomes": 1,
            "s3_observed_memories": 1, "s8_distinct_second_target_closed": False,
        }

    monkeypatch.setattr(trial.s1, "run_physical", synthetic_run)
    assert trial.main([
        "--run-disposable", "--confirm", trial.CONFIRM,
        "--standing-eula-confirmed", "--authorization-reference", REF,
        "--output-dir", str(output),
    ]) == 0
    assert called == [True]
    result = json.loads(capsys.readouterr().out)
    assert result["two_closed_actions_observed"] is False
    assert result["memory_caused_action_attested"] is False
    assert result["science_go"] is False
    assert result["s11_habit_grants"] == 0



def test_old_zombie_persists_after_clear_second_summon_is_never_attempted(tmp_path):
    driver, probe, grant, execute, _, _ = _fixture(tmp_path)
    owner, server = _controller(driver)
    observed = _native_clearance(owner, zombies=(7,))

    async def closed(step, receipt):
        await owner.after_action_closed(
            server, step, receipt, memory_count=1, clearance_probe=observed,
        )

    with pytest.raises(S8InterventionRejected, match="S8_CLEAR_NOT_NATIVE_VERIFIED"):
        asyncio.run(driver.run(
            probe=probe, grant=grant, on_action=execute,
            on_session_started=lambda: owner.submit_first(server),
            on_outcome_closed=closed,
        ))
    assert len(observed.calls) == 4
    assert owner.commands_attempted == 2
    assert server.stdin.commands == [
        (SUMMON + "\n").encode(), (CLEAR + "\n").encode(),
    ]
    rows = _rows(tmp_path)
    assert any(r["kind"] == "s9_clearance_unverified" for r in rows)
    assert rows[-1]["no_replay"] is True


@pytest.mark.parametrize("failure", ["foreign", "stale", "mixed", "truncated"])
def test_clearance_rejects_foreign_stale_ambiguous_or_incomplete_source(tmp_path, failure):
    driver, probe, grant, execute, _, _ = _fixture(tmp_path)
    owner, server = _controller(driver)
    observed = _native_clearance(
        owner, foreign=failure == "foreign", stale=failure == "stale",
        zombies=(2, 4) if failure == "mixed" else (),
        truncated=failure == "truncated",
    )
    source = observed

    async def closed(step, receipt):
        await owner.after_action_closed(
            server, step, receipt, memory_count=1, clearance_probe=source,
        )

    with pytest.raises(S8InterventionRejected, match="S8_CLEAR_NOT_NATIVE_VERIFIED"):
        asyncio.run(driver.run(
            probe=probe, grant=grant, on_action=execute,
            on_session_started=lambda: owner.submit_first(server),
            on_outcome_closed=closed,
        ))
    assert owner.commands_attempted == 2
    assert server.stdin.commands[-1] == (CLEAR + "\n").encode()
    assert not any(
        r["stage"] == "epoch2_summon"
        for r in _rows(tmp_path)
        if r["kind"] == "s8_external_command_intent"
    )


def test_zero_zombie_with_unrelated_item_allows_single_second_summon(tmp_path):
    driver, probe, grant, execute, _, _ = _fixture(tmp_path)
    owner, server = _controller(driver)
    observed = _native_clearance(owner, non_target=True)

    async def closed(step, receipt):
        await owner.after_action_closed(
            server, step, receipt, memory_count=1, clearance_probe=observed,
        )

    asyncio.run(driver.run(
        probe=probe, grant=grant, on_action=execute,
        on_session_started=lambda: owner.submit_first(server),
        on_outcome_closed=closed,
    ))
    assert owner.commands_attempted == 3
    assert len(observed.calls) == 1
    verified = [
        r for r in _rows(tmp_path) if r["kind"] == "s9_clearance_native_verified"
    ]
    assert len(verified) == 1
    assert verified[0]["kill_ack_attested"] is False


def test_consumed_s8_grant_cannot_authorize_another_trial(monkeypatch, capsys):
    monkeypatch.setattr(trial.s1, "preflight", lambda *_:
                        pytest.fail("consumed S8 grant must not reach host"))
    assert trial.main([
        "--run-disposable", "--confirm", trial.CONFIRM,
        "--standing-eula-confirmed",
        "--authorization-reference",
        "https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6118976649",
        "--output-dir", "/tmp/nonexistent-operator-output",
    ]) == 2
    assert "S8_NEW_TWO_EPOCH_AUTHORITY_REQUIRED" in capsys.readouterr().out
