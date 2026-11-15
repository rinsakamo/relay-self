"""#860: fail-closed PRE-checkpoint neutral body STOP across an A/B cohort."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerEffectResult,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
    MineflayerTime,
)
from relay_self.checkpoint_stop_neutralization_dev import (
    StopNeutralizationError,
    StopParticipant,
    prepare_stop_before_autosave,
)
from relay_self.physical_issue_admission_dev import (
    NeutralStopProof,
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)


class StopSessionFake:
    """Source-typed Mineflayer reads, never runs Minecraft/Paper."""

    def __init__(
        self, session_id: str, gate: PhysicalIssueAdmission, self_id: str,
        *, fault: str | None = None,
    ):
        self.started = SimpleNamespace(session_id=session_id)
        self.gate = gate
        self.self_id = self_id
        self.fault = fault
        self.events: list[object] = []
        self.action_ids: list[str] = []
        self.probe_count = 0
        self.seq = 0

    def _next(self):
        self.seq += 1
        return self.seq

    async def send_clear_controls(self, action_id: str):
        self.gate.require_native_effect(
            self_id=self.self_id, native_session_id=self.started.session_id,
            effect="clear_controls", action_id=action_id,
        )
        if self.fault == "wrong_action":
            self.gate.require_native_effect(
                self_id=self.self_id, native_session_id=self.started.session_id,
                effect="clear_controls", action_id="unrelated-stop",
            )
        self.action_ids.append(action_id)
        sid = "foreign-world" if self.fault == "foreign_ack" else self.started.session_id
        result = "rejected" if self.fault == "stop_rejected" else "applied"
        self.events.append(MineflayerEffectResult(
            sid, self._next(), action_id, "clear_controls",
            result, "rejected_by_test" if result == "rejected" else None,
        ))

    async def send_observe(self, request_id=None):
        self.probe_count += 1
        day = 0
        tick = (100 if self.fault == "no_ticks" else
                100 + 3 * (self.probe_count - 1))
        x = 10.0
        if self.fault == "drift":
            x = 10.0 + 0.25 * (self.probe_count - 1)
        elif self.fault == "settles_late" and self.probe_count > 4:
            x = 10.23
        if self.fault == "clock_regression" and self.probe_count > 1:
            tick = 90
        session = ("foreign-world" if self.fault == "foreign_probe"
                   else self.started.session_id)
        self.events.append(MineflayerObservation(
            session, self._next(), "probe",
            MineflayerSnapshot(
                health=20, food=10, food_saturation=5, oxygen_level=20,
                position=MineflayerPosition(x, 64, 5),
                time=(None if self.fault == "missing_time" else
                      MineflayerTime(tick, day, True)),
                inventory=(), nearby_entities=(),
                nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
                    source_scope=MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                    max_distance=MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                    max_entities=MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
                    candidate_count=0, truncated=False,
                ),
            ),
            request_id if self.fault != "wrong_probe" else "foreign-request",
        ))

    async def receive(self):
        if self.events:
            return self.events.pop(0)
        await asyncio.sleep(0)
        raise EOFError("simulated absence of STOP evidence")


def _cohort(tmp_path: Path, *, fault_b: str | None = None):
    gate = PhysicalIssueAdmission(
        {"A": "native-a", "B": "native-b"},
        require_neutral_stop=True,
    )
    a = StopSessionFake("native-a", gate, "A")
    b = StopSessionFake("native-b", gate, "B", fault=fault_b)
    return gate, (StopParticipant("A", a), StopParticipant("B", b)), a, b


def test_full_a_b_stop_proofs_before_existing_checkpoint_close(tmp_path):
    gate, cohort, a, b = _cohort(tmp_path)
    ready = asyncio.run(prepare_stop_before_autosave(
        gate, participants=cohort, audit_dir=tmp_path, timeout_s=2.0,
    ))
    assert ready.verified_self_ids == ("A", "B")
    assert ready.physical_issue_blocked
    assert not ready.checkpoint_committed
    assert ready.fence_ref == "physical-cohort-1"
    assert gate.neutralization_complete
    assert gate.closed
    assert len(a.action_ids) == len(b.action_ids) == 1
    assert a.probe_count >= 4 and b.probe_count >= 4
    for path in ready.receipt_files:
        data = json.loads(path.read_text())
        assert data["state"] == "NEUTRAL_SETTLED_DEV"
        assert data["settled_world_tick"] - data["first_world_tick"] >= 8
        prepared = json.loads(
            Path(str(path).replace(".verified.json", ".prepared.json")).read_text()
        )
        assert prepared["state"] == "PREPARED_UNRESOLVED"
        assert prepared["stop_action_id"] == data["stop_action_id"]
    with pytest.raises(PhysicalIssueFenceError, match="closed"):
        with gate.lease(
            self_id="A", native_session_id="native-a",
            action_id="eat-after-stop", effect_family="EAT",
        ):
            pytest.fail("effect escaped")
    frozen = gate.close()
    assert frozen.fence_ref == ready.fence_ref
    gate.rotate_native_session(
        fence_ref=frozen.fence_ref, self_id="A",
        old_session_id="native-a", new_session_id="native-a-next",
    )
    with pytest.raises(PhysicalIssueFenceError, match="complete"):
        gate.release(frozen.fence_ref)
    gate.rotate_native_session(
        fence_ref=frozen.fence_ref, self_id="B",
        old_session_id="native-b", new_session_id="native-b-next",
    )
    gate.release(frozen.fence_ref)
    assert not gate.closed


@pytest.mark.parametrize("fault", [
    "drift", "no_ticks", "foreign_ack", "foreign_probe", "wrong_probe",
    "stop_rejected", "missing_time", "clock_regression", "wrong_action",
])
def test_bad_b_stop_keeps_entire_cohort_held(tmp_path, fault):
    gate, cohort, a, b = _cohort(tmp_path, fault_b=fault)
    with pytest.raises((StopNeutralizationError, PhysicalIssueFenceError)):
        asyncio.run(prepare_stop_before_autosave(
            gate, participants=cohort, audit_dir=tmp_path, timeout_s=0.65,
        ))
    assert gate.closed
    assert not gate.neutralization_complete
    assert len(a.action_ids) == 1
    assert len(b.action_ids) <= 1
    with pytest.raises(PhysicalIssueFenceError, match="HOLD"):
        gate.close()
    with pytest.raises(PhysicalIssueFenceError, match="operator recovery"):
        gate.rotate_native_session(
            fence_ref="physical-cohort-1", self_id="A",
            old_session_id="native-a", new_session_id="native-a-next",
        )


def test_no_preflight_refused_by_strict_physical_cohort(tmp_path):
    gate, cohort, _, _ = _cohort(tmp_path)
    with pytest.raises(PhysicalIssueFenceError, match="STOP required"):
        gate.close()
    assert gate.closed
    with pytest.raises(StopNeutralizationError, match="invalid"):
        asyncio.run(prepare_stop_before_autosave(
            PhysicalIssueAdmission({"A": "native-a", "B": "native-b"}),
            participants=cohort, audit_dir=tmp_path,
        ))


def test_active_eat_blocks_stop_before_any_native_clear(tmp_path):
    gate, cohort, a, b = _cohort(tmp_path)
    with gate.lease(
        self_id="A", native_session_id="native-a",
        action_id="inflight-eat", effect_family="EAT",
    ):
        with pytest.raises(PhysicalIssueFenceError, match="in-flight"):
            asyncio.run(prepare_stop_before_autosave(
                gate, participants=cohort, audit_dir=tmp_path,
            ))
    assert gate.closed
    assert not a.action_ids and not b.action_ids
    assert not list(tmp_path.glob("stop-*.prepared.json"))


def test_forged_incomplete_roster_refused_before_physical_gate(tmp_path):
    gate, cohort, _, _ = _cohort(tmp_path)
    with pytest.raises(StopNeutralizationError, match="roster"):
        asyncio.run(prepare_stop_before_autosave(
            gate, participants=cohort[:1], audit_dir=tmp_path,
        ))
    assert not gate.closed
    assert not list(tmp_path.glob("stop-*"))



def test_initial_post_stop_residual_motion_then_8_tick_stillness_is_accepted(tmp_path):
    gate, cohort, a, b = _cohort(tmp_path, fault_b="settles_late")
    ready = asyncio.run(prepare_stop_before_autosave(
        gate, participants=cohort, audit_dir=tmp_path, timeout_s=2.0,
    ))
    assert gate.neutralization_complete
    assert a.probe_count >= 7
    # Drifting after initial settling forces a second later stable window.
    assert b.probe_count >= 10
    assert len(ready.receipt_files) == 2
    receipt_b = json.loads(ready.receipt_files[1].read_text())
    assert receipt_b["first_position"]["x"] == 10.23
    assert receipt_b["settled_position"]["x"] == 10.23
    assert receipt_b["settled_world_tick"] - receipt_b["first_world_tick"] >= 8



def test_stale_prepared_stop_audit_blocks_next_world_cut(tmp_path):
    # PREPARED evidence without a completed same-identity receipt cannot be skipped.
    old = tmp_path / "stop-A-oldsession.prepared.json"
    old.write_text('{"state":"PREPARED_UNRESOLVED"}')
    gate, cohort, a, b = _cohort(tmp_path)
    with pytest.raises(StopNeutralizationError, match="earlier STOP PREPARED_UNRESOLVED"):
        asyncio.run(prepare_stop_before_autosave(
            gate, participants=cohort, audit_dir=tmp_path,
        ))
    assert gate.closed
    assert not a.action_ids and not b.action_ids
    with pytest.raises(PhysicalIssueFenceError, match="HOLD"):
        gate.close()


def test_physical_owner_independently_rejects_forged_one_window_proof(tmp_path):
    gate = PhysicalIssueAdmission(
        {"A": "native-a"}, require_neutral_stop=True,
    )
    fake = StopSessionFake("native-a", gate, "A")

    async def forged_one_window():
        token = gate.begin_neutralization()
        with gate.stop_lease(
            fence_ref=token, self_id="A", native_session_id="native-a",
            stop_action_id="stop-A",
        ):
            await fake.send_clear_controls("stop-A")
            ack = await fake.receive()
            records = []
            for label in ("initial", "early", "later"):
                await fake.send_observe(label)
                records.append(await fake.receive())
            initial, early, later = records
            # There is enough time between early and later, but initial to
            # early was only three World ticks; that cannot bypass stage 1.
            later = replace(later, snapshot=replace(
                later.snapshot, time=MineflayerTime(112, 0, True),
            ))
            with pytest.raises(PhysicalIssueFenceError, match="initial 8-tick"):
                gate.confirm_neutral_stop(
                    fence_ref=token, self_id="A",
                    proof=NeutralStopProof("stop-A", ack, initial, early, later),
                )
        assert gate.closed
        with pytest.raises(PhysicalIssueFenceError, match="HOLD"):
            gate.close()

    asyncio.run(forged_one_window())
