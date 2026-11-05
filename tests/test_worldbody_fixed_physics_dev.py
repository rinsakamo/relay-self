"""World-owned physical fatigue, direct SelfBody read, and pre-World guards."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer.worldbody_direct_selfbody import (
    DirectMoveExperience,
    DirectWorldBodyObservationRejected,
    rest_from_observed_motor_output,
    direct_move_experience,
)
from adapters.mineflayer.normal_action import NormalActionReceipt
from adapters.mineflayer.execution import WorldConsequenceStatus
from relay_self.action import ActionState
from relay_self.provenance import Provenance
from adapters.mineflayer.worldbody_paper_server import (
    WorldBodyStagingRejected,
    stage_fixed_worldbody,
)

JAVA = Path(
    "adapters/mineflayer/worldbody_physics_dev/src/main/java/"
    "io/github/rinsakamo/worldbody/RelayWorldBodyDev.java"
)


def sample(action: str, seq: int, distance: float) -> DirectMoveExperience:
    return DirectMoveExperience(
        session_id="session-fixed-world",
        action_id=action,
        native_seq=seq,
        action_distance_m=distance,
        source_ref=f"native-probe:session-fixed-world:{seq}:request-{seq}",
        observed_fields=("position_x", "position_y", "position_z", "health", "food"),
    )


def test_direct_move_loss_selects_rest_without_worldbody_truth():
    a = sample("move-one", 21, 0.62)
    b = sample("move-two", 52, 0.24)
    choice = rest_from_observed_motor_output(a, b)
    assert choice.rest_requested is True
    assert choice.reason == "OBSERVED_MOTOR_OUTPUT_LOSS"
    assert choice.output_ratio == pytest.approx(0.24 / 0.62)
    assert choice.worldbody_truth_accessed is False


def test_original_uncorrelated_s16_after_requires_new_native_present():
    # Reproduce original physical World #41996911111's observed import bug:
    # the S15 internal after-probe carries no request_id. It is NOT Present.
    from test_bug0_s49_food_refusal_priority import sample

    correlated = sample(food=20, seq=52)
    original_after = replace(correlated, seq=49, request_id=None)
    receipt = NormalActionReceipt(
        terminal=SimpleNamespace(state=ActionState.OUTCOME, action_id="move-a"),
        consequence=SimpleNamespace(
            action_id="move-a", session_id=correlated.session_id,
            status=WorldConsequenceStatus.EXECUTED,
            movement_distance=0.4, after_observation=original_after,
        ),
        source=Provenance("s49", "original"),
    )
    with pytest.raises(DirectWorldBodyObservationRejected):
        direct_move_experience(receipt, original_after)
    with pytest.raises(DirectWorldBodyObservationRejected):
        direct_move_experience(receipt, replace(correlated, seq=49))
    with pytest.raises(DirectWorldBodyObservationRejected):
        direct_move_experience(
            receipt, replace(correlated, session_id="foreign-session")
        )
    actual = direct_move_experience(receipt, correlated)
    assert actual.action_distance_m == 0.4
    assert actual.native_seq == 52
    assert actual.source_ref.startswith("native-probe:")
    assert actual.hidden_worldbody_fatigue_accessed is False
    assert actual.worldbody_rate_accessed is False


def test_direct_output_without_loss_is_wait_not_rest():
    a = sample("move-one", 21, 0.62)
    b = sample("move-two", 52, 0.62)
    c = rest_from_observed_motor_output(a, b)
    assert c.rest_requested is False
    assert c.reason == "NO_OUTPUT_LOSS_PROVEN"


@pytest.mark.parametrize("variant", (
    "same-action", "same-seq", "stale-seq", "foreign-session",
    "hidden-truth", "world-rate", "zero-distance", "huge-distance",
))
def test_direct_selfbody_rejects_undue_rest_source(variant):
    a = sample("move-one", 21, 0.62)
    b = sample("move-two", 52, 0.24)
    if variant == "same-action":
        b = replace(b, action_id=a.action_id)
    elif variant == "same-seq":
        b = replace(b, native_seq=21)
    elif variant == "stale-seq":
        b = replace(b, native_seq=20)
    elif variant == "foreign-session":
        b = replace(b, session_id="another-session")
    elif variant == "hidden-truth":
        b = replace(b, hidden_worldbody_fatigue_accessed=True)
    elif variant == "world-rate":
        b = replace(b, worldbody_rate_accessed=True)
    elif variant == "zero-distance":
        b = replace(b, action_distance_m=0)
    else:
        b = replace(b, action_distance_m=100)
    with pytest.raises(DirectWorldBodyObservationRejected):
        rest_from_observed_motor_output(a, b)


def test_world_authoritative_physics_never_exposes_self_mutation_or_sensor():
    code = JAVA.read_text(encoding="utf-8")
    assert "MOVE_FATIGUE_PER_METRE = 2.0" in code
    assert "STILL_RECOVERY_PER_SERVER_TICK = 0.003" in code
    assert "p.setWalkSpeed(SLOW_WALK_SPEED)" in code
    assert "p.setWalkSpeed(NORMAL_WALK_SPEED)" in code
    assert "getConfig().getDouble" not in code
    assert "getConfig().getInt" not in code
    assert "onCommand(" not in code
    assert "public double getFatigue" not in code
    assert "public void setFatigue" not in code
    assert "WORLDBODY_INTERNAL" in code
    assert "WorldBody" not in Path("src/relay_self/self_body.py").read_text()


@pytest.mark.parametrize("mode", ("missing-grant", "no-target-file", "no-plugin", "fake-jar"))
def test_worldbody_staging_fails_closed_before_server(tmp_path, monkeypatch, mode):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_WORLDBODY_DEV_ONLY", "1")
    if mode == "missing-grant":
        monkeypatch.delenv("S49_WORLDBODY_DEV_ONLY")
    if mode == "no-target-file":
        monkeypatch.delenv("S49_WB_PAPER_JAR", raising=False)
    if mode == "no-plugin":
        monkeypatch.delenv("S49_WB_PLUGIN_JAR", raising=False)
    if mode == "fake-jar":
        fake = tmp_path / "fake-paper.jar"
        fake.write_bytes(b"fake")
        monkeypatch.setenv("S49_WB_PAPER_JAR", str(fake))
    with pytest.raises(WorldBodyStagingRejected):
        stage_fixed_worldbody(tmp_path)
    assert not (tmp_path / "minecraft.jar").exists()


@pytest.mark.parametrize("variant", (
    "missing-flag", "paper-conflict", "rest-conflict", "eat-conflict",
    "wrong-type",
))
def test_original_s49_worldbody_exclusive_gate_blocks_before_world(
    tmp_path, monkeypatch, variant,
):
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_WORLDBODY_DEV_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    flags = {"worldbody_dev": True}
    if variant == "missing-flag":
        monkeypatch.delenv("S49_WORLDBODY_DEV_ONLY")
    elif variant == "paper-conflict":
        flags["bug0_p1_paper_dev"] = True
    elif variant == "rest-conflict":
        flags["bug0_rest_dev"] = True
    elif variant == "eat-conflict":
        flags["bug0_food_loop_dev"] = True
    elif variant == "wrong-type":
        flags["worldbody_dev"] = "yes"
    out = tmp_path / "blocked.json"
    code = asyncio.run(s49.qualify(out, tmp_path / "paper.log", **flags))
    row = __import__("json").loads(out.read_text())
    assert code == 2 and row["status"] == "BLOCKED"
    assert row["actual_native_actions"] == []
    assert not (tmp_path / "paper.log").exists()
