"""C16 gated physical one-shot harness qualification with decoded fake sessions.

NO localhost server is opened by these fixtures and NO Mineflayer process runs.
A fixture classification is never real-world source/goal/Action attestation.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import warnings
from dataclasses import fields
from pathlib import Path

import pytest

from adapters.mineflayer.goal_witness import Region
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_VERSION,
    MineflayerStreamDecoder,
)
from adapters.mineflayer.qualify_goal_live import (
    CONFIRM,
    C16Result,
    OneShotQualification,
    manifest,
    preflight,
    read_spatial_spec,
)

SESSION = "c16-test-session"
HOME = (0.0, 64.0, 1.0)
TARGET = (0.25, 64.0, 1.0)
ALTERNATIVE = (-0.25, 64.0, 1.0)


def goal_regions() -> tuple[Region, Region]:
    return (
        Region((0.15, 63.0, 0.85), (0.35, 66.0, 1.15)),
        Region((-0.35, 63.0, 0.85), (-0.15, 66.0, 1.15)),
    )


def started_dict() -> dict:
    return {
        "type": "adapter_started", "session_id": SESSION, "seq": 0,
        "mineflayer_version": MINEFLAYER_VERSION,
        "config": {
            "host": "127.0.0.1", "port": 25565,
            "username": "RelaySelfC16", "version": None,
        },
    }


def observation(position: tuple[float, float, float], kind: str) -> dict:
    return {
        "type": "observation", "session_id": SESSION, "seq": -1,
        "kind": kind,
        "snapshot": {
            "health": 10, "food": 10, "food_saturation": 4,
            "oxygen_level": None,
            "position": {"x": position[0], "y": position[1], "z": position[2]},
            "time": None, "inventory": [], "nearby_entities": [],
            "nearby_entities_coverage": {
                "source_scope": "mineflayer_entity_registry",
                "max_distance": 16, "max_entities": 16,
                "candidate_count": 0, "truncated": False,
            },
        },
    }


def acknowledgement(which: str, *, applied: bool = True) -> dict:
    return {
        "type": "effect_result",
        "session_id": SESSION,
        "seq": -1,
        "action_id": f"c16-{which}-{SESSION}",
        "effect": "set_control" if which == "forward" else "clear_controls",
        "result": "applied" if applied else "rejected",
        "error": None if applied else "synthetic denied ACK",
    }


def raw_messages(*, ending: tuple[float, float, float] = TARGET,
                 movement: tuple[float, float, float] | None = None) -> list[dict]:
    vals = [
        started_dict(),
        observation(HOME, "spawn"),
        observation(HOME, "probe"),
        acknowledgement("forward"),
        observation(movement if movement is not None else ending, "move"),
        acknowledgement("stop"),
        observation(ending, "probe"),
        observation(ending, "probe"),
    ]
    return resequence(vals)


def resequence(vals: list[dict]) -> list[dict]:
    for i, x in enumerate(vals):
        x["seq"] = i
    return vals


class FakeOwned:
    def __init__(self, records: list[dict]):
        decoder = MineflayerStreamDecoder()
        self._started = decoder.decode(json.dumps(records[0]))
        # Individual decoded objects preserve source fields/refs; stream decoding
        # remains the existing strict Mineflayer decoder, NOT a toy message class.
        self._events = [decoder.decode(json.dumps(e)) for e in records[1:]]
        self.sends: list[tuple] = []

    @property
    def started(self):
        return self._started

    async def receive(self):
        if not self._events:
            raise RuntimeError("fixture source EOF")
        return self._events.pop(0)

    async def send_observe(self) -> None:
        self.sends.append(("observe",))

    async def send_set_control(self, action_id: str, *,
                               control: str, state: bool) -> None:
        self.sends.append(("set_control", action_id, control, state))

    async def send_clear_controls(self, action_id: str) -> None:
        self.sends.append(("clear_controls", action_id))


def run_fixture(rows: list[dict]) -> tuple[C16Result, FakeOwned]:
    fake = FakeOwned(rows)
    out = asyncio.run(OneShotQualification().run(
        fake, goal=goal_regions()[0], alternative=goal_regions()[1],
        timeout_s=1.5,
    ))
    return out, fake


def test_frozen_manifest_and_c15_stacked_dependency():
    m = manifest()
    assert m["version"] == "AC-C-C16-ONE-SHOT-PHYSICAL-ENDPOINT-v1"
    assert m["owner"]["stacked_on_c15_head"] == (
        "5e738596b805522d8516b43fa1b7ee001bfc5b2b"
    )
    assert m["physical_admission"]["default"] == "DRY_BLOCKED_NO_PROCESS"
    assert m["protocol"]["new_protocol_commands"] == 0
    assert m["output"]["physical_qualification_default"] == "NOT_RUN"
    assert m["output"]["learned_signed_negative"] == "BLOCKED_UNDETERMINED"


def test_default_preflight_is_zero_process_and_zero_socket():
    result = preflight(
        execute=False, confirmation=None, world_dir=None,
        expected_level_sha256=None, spatial_spec_path=None,
        host="127.0.0.1", port=25565,
    )
    assert isinstance(result, C16Result)
    assert result.classification == "BLOCKED_WORLD_OR_AUTHORITY_UNVERIFIED"
    assert result.reason == "DRY_BLOCKED_NO_PROCESS"
    assert result.source_session is None
    assert result.automatic_learning_updates == 0


def test_no_operator_confirmation_even_when_explicit_run_flag_set():
    result = preflight(
        execute=True, confirmation=None, world_dir=None,
        expected_level_sha256=None, spatial_spec_path=None,
        host="127.0.0.1", port=25565,
    )
    assert result.reason == "MISSING_EXPLICIT_OPERATOR_CONFIRMATION"


def test_world_file_is_required_to_be_regular_and_sha_matched(tmp_path: Path):
    region_path = tmp_path / "regions.json"
    goal, alt = goal_regions()
    region_path.write_text(json.dumps({
        "goal": {"low": list(goal.low), "high": list(goal.high)},
        "alternative": {"low": list(alt.low), "high": list(alt.high)},
    }), encoding="utf-8")
    world = tmp_path / "world"
    world.mkdir()
    level = world / "level.dat"
    level.write_bytes(b"synthetic-world-fixture-only")
    expected = hashlib.sha256(level.read_bytes()).hexdigest()
    common = dict(
        execute=True, confirmation=CONFIRM, world_dir=world,
        spatial_spec_path=region_path, host="127.0.0.1",
        port=25565, check_tcp=False,
    )
    assert preflight(
        **common, expected_level_sha256="0"*64
    ).reason == "LEVEL_DAT_IDENTITY_MISMATCH"
    valid = preflight(**common, expected_level_sha256=expected)
    assert valid == (goal, alt)
    assert preflight(**{
        **common, "world_dir": tmp_path / "missing",
        "expected_level_sha256": expected,
    }).reason == "UNVERIFIED_WORLD_DIR"


def test_foreign_host_and_port_are_denied_before_any_socket():
    for host, port in (("localhost", 25565), ("8.8.8.8", 25565),
                       ("127.0.0.1", 0), ("127.0.0.1", 65536)):
        reason = preflight(
            execute=True, confirmation=CONFIRM,
            world_dir=None, expected_level_sha256=None,
            spatial_spec_path=None, host=host, port=port,
        ).reason
        assert reason == "LOOPBACK_SERVER_ONLY"


def test_spatial_spec_must_explicitly_define_disjoint_c15_regions(tmp_path: Path):
    path = tmp_path / "spec.json"
    goal, alt = goal_regions()
    path.write_text(json.dumps({
        "goal": {"low": list(goal.low), "high": list(goal.high)},
        "alternative": {"low": list(alt.low), "high": list(alt.high)},
    }), encoding="utf-8")
    assert read_spatial_spec(path) == (goal, alt)
    path.write_text(json.dumps({
        "goal": {"low": list(goal.low), "high": list(goal.high)},
        "alternative": {"low": list(goal.low), "high": list(goal.high)},
    }), encoding="utf-8")
    with pytest.raises(ValueError):
        read_spatial_spec(path)


@pytest.mark.parametrize(("ending", "expected"), [
    (TARGET, "GOAL_REGION_OBSERVED"),
    (ALTERNATIVE, "ALTERNATIVE_REGION_OBSERVED"),
])
def test_canonical_actions_and_poststop_two_probes_yield_spatial_only(
    ending: tuple[float, float, float], expected: str,
):
    result, fake = run_fixture(raw_messages(ending=ending))
    assert result.classification == expected
    assert result.start_action_state == "OUTCOME"
    assert result.stop_action_state == "OUTCOME"
    assert result.reason == "SPATIAL_ENDPOINT_ONLY_NOT_GOAL_OR_CAUSAL_PROOF"
    assert result.evidence == tuple(f"{SESSION}:{i}" for i in range(8))
    assert result.movement_horizontal == pytest.approx(0.25)
    assert fake.sends == [
        ("observe",),
        ("set_control", f"c16-forward-{SESSION}", "forward", True),
        ("clear_controls", f"c16-stop-{SESSION}"),
        ("observe",), ("observe",),
    ]
    assert result.physical_world_server_association_verified is False
    assert result.signed_negative_label == "BLOCKED_UNDETERMINED"
    assert result.automatic_learning_updates == 0
    for forbidden in ("z", "correct", "skill", "habit", "learning"):
        assert forbidden not in {f.name for f in fields(result)}


def adverse_case(name: str) -> list[dict]:
    vals = raw_messages()
    if name == "missing_baseline":
        vals.pop(2)
    elif name == "missing_post_probe":
        vals.pop()
    elif name == "wrong_action_id":
        vals[3]["action_id"] = "other-action"
    elif name == "rejected_ack":
        vals[3]["result"] = "rejected"
        vals[3]["error"] = "rejected fixture"
    elif name == "forced_move":
        vals.insert(4, observation(TARGET, "forcedMove"))
    elif name == "unstable_probes":
        vals[-1]["snapshot"]["position"]["x"] = 0.34
    elif name == "out_of_region":
        vals[-2]["snapshot"]["position"]["x"] = 0.08
        vals[-1]["snapshot"]["position"]["x"] = 0.08
    elif name == "movement_below_minimum":
        vals[4]["snapshot"]["position"]["x"] = 0.02
    elif name == "movement_above_maximum":
        vals[4]["snapshot"]["position"]["x"] = 0.7
    elif name == "unknown_stop_ack":
        vals[5]["action_id"] = "other-stop"
    elif name == "goal_preexisting":
        vals[1] = observation(TARGET, "spawn")
        vals[2] = observation(TARGET, "probe")
    elif name == "terminal_position_exceeds_limit":
        vals[6]["snapshot"]["position"]["x"] = 1.0
        vals[7]["snapshot"]["position"]["x"] = 1.0
    elif name == "no_spawn":
        vals[1]["kind"] = "health"
    elif name == "stop_ack_rejected":
        vals[5]["result"] = "rejected"
        vals[5]["error"] = "synthetic rejected stop"
    else:
        raise AssertionError("unknown adversarial case")
    return resequence(vals)


ADVERSE = (
    "missing_baseline", "missing_post_probe", "wrong_action_id",
    "rejected_ack", "forced_move", "unstable_probes", "out_of_region",
    "movement_below_minimum", "movement_above_maximum", "unknown_stop_ack",
    "goal_preexisting", "terminal_position_exceeds_limit",
    "no_spawn", "stop_ack_rejected",
)


@pytest.mark.parametrize("name", ADVERSE)
def test_mocked_adverse_source_never_promotes_to_endpoint(name: str):
    rows = adverse_case(name)
    result, fake = run_fixture(rows)
    assert result.classification == "UNDETERMINED", name
    assert result.automatic_learning_updates == 0
    assert result.signed_negative_label == "BLOCKED_UNDETERMINED"
    assert not result.physical_world_server_association_verified
    assert len([x for x in fake.sends if x[0] == "set_control"]) <= 1


def test_timeout_and_stop_cleanup_are_fail_closed_without_retry():
    vals = raw_messages()
    vals.pop(4)  # no movement after applied ACK; later stop ACK is unexpected
    out, fake = run_fixture(resequence(vals))
    assert out.classification == "UNDETERMINED"
    assert len([x for x in fake.sends if x[0] == "set_control"]) == 1
    assert any(
        x[0] == "clear_controls" and "emergency" in x[1]
        for x in fake.sends
    )
    assert out.automatic_learning_updates == 0


def test_one_shot_reuse_is_denied_even_with_different_evidence():
    owner = OneShotQualification()
    fake = FakeOwned(raw_messages())
    goal, alt = goal_regions()
    first = asyncio.run(owner.run(fake, goal=goal, alternative=alt, timeout_s=1))
    assert first.classification == "GOAL_REGION_OBSERVED"
    fresh = FakeOwned(raw_messages(ending=ALTERNATIVE))
    denied = asyncio.run(owner.run(fresh, goal=goal, alternative=alt, timeout_s=1))
    assert denied.classification == "UNDETERMINED"
    assert denied.reason == "ONE_SHOT_REPLAY_DENIED"
    assert fresh.sends == []



def test_rejected_stop_ack_requires_one_emergency_clear() -> None:
    result, fake = run_fixture(adverse_case("stop_ack_rejected"))
    assert result.classification == "UNDETERMINED"
    clear_calls = [call for call in fake.sends if call[0] == "clear_controls"]
    assert len(clear_calls) == 2
    assert clear_calls[0][1] == f"c16-stop-{SESSION}"
    assert clear_calls[1][1] == f"c16-emergency-{SESSION}"
    assert not result.physical_world_server_association_verified


def test_forward_wall_watchdog_stops_when_source_ack_is_delayed() -> None:
    class DelayedForwardAck(FakeOwned):
        async def receive(self):
            if self._events and self._events[0].seq == 3:
                await asyncio.sleep(0.35)
            return await super().receive()

    fake = DelayedForwardAck(raw_messages())
    goal, alt = goal_regions()
    result = asyncio.run(
        OneShotQualification().run(fake, goal=goal, alternative=alt, timeout_s=1.0)
    )
    assert result.classification == "UNDETERMINED"
    assert "TIMED_OUT" in result.reason or "WATCHDOG" in result.reason
    assert fake.sends.count(("observe",)) == 1
    assert len([x for x in fake.sends if x[0] == "set_control"]) == 1
    emergency = [x for x in fake.sends if x[0] == "clear_controls"]
    assert emergency == [("clear_controls", f"c16-emergency-{SESSION}")]
    assert result.signed_negative_label == "BLOCKED_UNDETERMINED"



@pytest.mark.parametrize("body_field", ["health", "food"])
def test_unhealthy_spawn_prohibits_any_forward_action(body_field: str) -> None:
    rows = raw_messages()
    rows[1]["snapshot"][body_field] = 2
    result, fake = run_fixture(rows)
    assert result.classification == "UNDETERMINED"
    assert "UNSAFE_SPAWN_BODY" in result.reason
    assert not any(x[0] == "set_control" for x in fake.sends)
    assert result.automatic_learning_updates == 0


def fixture_report() -> dict:
    good = [
        run_fixture(raw_messages(ending=place))[0].classification
        for place in (TARGET, ALTERNATIVE)
    ]
    bad = [run_fixture(adverse_case(name))[0].classification
           for name in ADVERSE]
    return {
        "version": manifest()["version"],
        "mock_spatial_recognitions": sum(x != "UNDETERMINED" for x in good),
        "mock_adverse_undetermined": sum(x == "UNDETERMINED" for x in bad),
        "mock_adverse_false_positive": sum(x != "UNDETERMINED" for x in bad),
        "physical_world_observed": "NOT_RUN",
        "real_server_association_verified": False,
        "issued_real_actions": 0,
        "automatic_learning_updates": 0,
        "signed_negative_label": "BLOCKED_UNDETERMINED",
    }


def test_deterministic_machine_report_and_no_real_physical_action():
    data = fixture_report()
    assert data == fixture_report()
    assert data["mock_spatial_recognitions"] == 2
    assert data["mock_adverse_undetermined"] == len(ADVERSE)
    assert data["mock_adverse_false_positive"] == 0
    assert data["physical_world_observed"] == "NOT_RUN"


def test_emit_C16_result_for_exact_head_CI():
    warnings.warn(
        "C16_RESULT_JSON "+json.dumps(fixture_report(), sort_keys=True),
        UserWarning,
    )
