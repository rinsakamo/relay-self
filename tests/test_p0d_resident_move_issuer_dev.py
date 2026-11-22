"""#904 Stage23: selected canonical resident MOVE + original WAL and source faults.

Only Python simulated native streams. No real Paper/Gemma, Skill success,
independent B Paper damage/movement causation, or target tolerance accepted.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
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
from experiments.cognitive_physical_executor_dev import (
    PhysicalDevGrant,
    PhysicalGrantStage,
)
from experiments.cognitive_physical_move_issue_dev import PhysicalMoveRefusal
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.physical_action_journal import (
    PhysicalActionJournal,
    PhysicalJournalError,
    PhysicalJournalUnresolved,
)
from relay_self.physical_action_port import (
    PhysicalActionBinding,
    PhysicalCapability,
    PhysicalReadback,
    propose_bound_physical_action,
)
from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


def _probe(native: str, seq: int, request: str, tick: int, x: float):
    return MineflayerObservation(
        native, seq, "probe",
        MineflayerSnapshot(
            health=20, food=16, food_saturation=5, oxygen_level=20,
            position=MineflayerPosition(x, 64, 2),
            time=MineflayerTime(tick % 24000, tick // 24000, True),
            inventory=(), nearby_entities=(),
            nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
                MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
                0, False,
            ),
        ), request,
    )


def _selected(root: Path, sid="A", native="native-A", action_id="move-A"):
    source = Provenance("dev-original-self", sid)
    owner = IntentCommitment()
    owner.commit("intent-" + sid, objective="WALK_RELATIVE", at_ns=1,
                 provenance=source)
    skill = SkillExecution.start(
        "skill-" + sid, skill_id="MOVE",
        intent_commitment=owner, at_ns=2, provenance=source,
    )
    previous = _probe(native, 1, "prior-probe", 100, 1.0)
    current = _probe(native, 2, "move-probe", 101, 1.0)
    binding = PhysicalActionBinding(
        ScopeRef(sid, native),
        "intent-" + sid, "WALK_RELATIVE",
        "MOVE", 1, skill.execution_id, action_id,
        "MOVE", 1, "locomotion", "RELATIVE", "relative:forward",
        current.seq, current.request_id, current.provenance,
    )
    supervisor = ActionSupervisor()
    proposal = propose_bound_physical_action(
        binding,
        capability=PhysicalCapability("MOVE", 1, "locomotion", "RELATIVE", True),
        readback=PhysicalReadback(
            binding.scope, current.provenance, current.seq,
            current.request_id, (binding.target_ref,), True,
        ),
        intent_owner=owner, skill_execution=skill,
        supervisor=supervisor, at_ns=3, provenance=source,
    )
    directory = root / ("wal-" + sid)
    directory.mkdir()
    journal = PhysicalActionJournal.create(
        directory / "physical.json", self_id=sid,
    )

    def grant(stage: PhysicalGrantStage):
        return PhysicalDevGrant(
            stage=stage,
            authority_id="operator-" + stage.value,
            provenance=Provenance(
                "operator-" + stage.value.lower(), native + ":2",
            ),
            intent_id=binding.intent_id,
            action_id=binding.action_id,
            session_id=native,
            probe_seq=binding.native_seq,
            probe_request_id=binding.native_request_id,
            selected_target_ref=binding.target_ref,
            granted=True,
        )

    return dict(
        proposal=proposal, previous_probe=previous, current_probe=current,
        propose_grant=grant(PhysicalGrantStage.PROPOSE),
        issue_grant=grant(PhysicalGrantStage.ISSUE),
        intent_owner=owner, skill_execution=skill,
        supervisor=supervisor, journal=journal, at_ns=4, provenance=source,
        grant_real_world=True, acknowledge_dev_unverified_principal=True,
        pulse_seconds=0.15, evidence_timeout_s=1.5,
    )


class ScriptedNative(MineflayerProcessSession):
    """Actual class identity, but an entirely synthetic native byte source."""

    def __init__(self, native="native-A", *, bad_stop=False):
        self._started_for_test = SimpleNamespace(session_id=native)
        self.events = []
        self.seq = 2
        self.tick = 101
        self.x = 1.0
        self.bad_stop = bad_stop
        self.gate = None
        self.start_received = asyncio.Event()
        self.stop_received = asyncio.Event()
        self.sent_commands = []

    @property
    def started(self):
        return self._started_for_test

    @property
    def process_returncode(self):
        return None

    async def send_set_control(self, action_id, *, control, state):
        self.gate(self.started.session_id, "set_control", action_id)
        assert control == "forward" and state is True
        self.sent_commands.append((action_id, control, state))
        self.seq += 1
        self.events.append(MineflayerEffectResult(
            self.started.session_id, self.seq, action_id, "set_control",
            "applied", None,
        ))
        self.x += 0.8
        self.start_received.set()

    async def send_clear_controls(self, action_id):
        self.gate(self.started.session_id, "clear_controls", action_id)
        self.sent_commands.append((action_id, "clear_controls", False))
        self.seq += 1
        self.events.append(MineflayerEffectResult(
            self.started.session_id, self.seq,
            "forged-stop" if self.bad_stop else action_id,
            "clear_controls", "applied", None,
        ))
        self.stop_received.set()

    async def send_observe(self, request_id):
        self.seq += 1
        self.tick += 9
        self.events.append(_probe(
            self.started.session_id, self.seq,
            request_id, self.tick, self.x,
        ))

    async def receive(self):
        if not self.events:
            raise EOFError("missing synthetic native source")
        return self.events.pop(0)


@pytest.mark.parametrize("count", [2, 10, 100])
def test_original_resident_move_can_run_while_peers_stay_active(tmp_path, count):
    ids = tuple(f"S{i:03d}" for i in range(count))
    sessions = {sid: "native-" + sid for sid in ids}
    gate = PhysicalIssueAdmission(
        sessions, resident_mode=True, allow_resident_move=True,
    )
    a = ids[0]
    s = ScriptedNative(sessions[a])
    s.gate = lambda native, effect, action: gate.require_native_effect(
        self_id=a, native_session_id=native,
        effect=effect, action_id=action,
    )
    args = _selected(tmp_path, sid=a, native=sessions[a], action_id="move-" + a)

    async def scenario():
        task = asyncio.create_task(gate.issue_move(s, **args))
        await s.start_received.wait()
        fence = gate.quarantine_resident(self_id=a, native_session_id=s.started.session_id)
        assert fence.active_action_ids == ("move-" + a,)
        with pytest.raises(PhysicalIssueFenceError, match="blocked"):
            gate.require_native_effect(
                self_id=a, native_session_id=s.started.session_id,
                effect="set_control", action_id="move-" + a + "-start",
            )
        b = ids[-1]
        with gate.lease(
            self_id=b, native_session_id=sessions[b],
            action_id="peer-EAT", effect_family="EAT",
        ):
            gate.require_native_effect(
                self_id=b, native_session_id=sessions[b],
                effect="consume_held", action_id="peer-EAT",
            )
        result = await task
        assert result.terminal.state is ActionState.OUTCOME
        assert result.displacement_m >= 0.8
        assert s.stop_received.is_set()
        assert result.skill_success_attested is False
        assert result.paper_causal_attribution is False
        assert not args["journal"].unresolved
        retired = gate.retire_resident(
            self_id=a, native_session_id=s.started.session_id,
            fence_ref=fence.fence_ref, physical_wal_file=args["journal"].path,
        )
        assert retired.physical_wal_clear
        assert gate.resident_states[a] == "OFFLINE"
        assert gate.resident_states[b] == "ONLINE"
        with pytest.raises(PhysicalIssueFenceError):
            gate.require_native_effect(
                self_id=a, native_session_id=s.started.session_id,
                effect="clear_controls", action_id="move-" + a + "-stop",
            )

    asyncio.run(scenario())


def test_original_wal_move_is_fsynced_before_motion_and_restorable(tmp_path):
    args = _selected(tmp_path)
    proposal = args["proposal"]
    journal = args["journal"]
    probe = args["current_probe"]
    journal.prepare_move(proposal.binding, probe)
    restored = PhysicalActionJournal.restore(journal.path, self_id="A")
    assert restored.unresolved
    assert restored.records[-1]["action_id"] == "move-A"
    assert restored.records[-1]["status"] == "PREPARED_UNRESOLVED"
    assert restored.records[-1]["control"] == "forward"
    with pytest.raises(PhysicalJournalUnresolved):
        restored.require_clear()
    with pytest.raises(PhysicalJournalUnresolved):
        restored.prepare_move(proposal.binding, probe)
    with pytest.raises(PhysicalJournalUnresolved):
        journal.require_clear()


def test_original_issuer_native_children_are_exact_and_one_shot(tmp_path):
    args = _selected(tmp_path)
    journal = args["journal"]
    gate = PhysicalIssueAdmission(
        {"A": "native-A", "B": "native-B"},
        resident_mode=True, allow_resident_move=True,
    )
    with gate.lease(
        self_id="A", native_session_id="native-A",
        action_id="move-A", effect_family="MOVE",
    ):
        with pytest.raises(PhysicalIssueFenceError, match="capability"):
            gate.require_native_effect(
                self_id="A", native_session_id="native-A",
                effect="set_control", action_id="move-A-start",
            )
        journal.prepare_move(args["proposal"].binding, args["current_probe"])
        gate.bind_native_children(
            self_id="A", native_session_id="native-A",
            lease_action_id="move-A", parent_action_id="move-A",
            family="MOVE", journal=journal,
        )
        for effect, action in (
            ("set_control", "another-parent-start"),
            ("clear_controls", "move-A-start"),
            ("set_control", "move-A-stop"),
            ("set_control", "move-A-unknown"),
        ):
            with pytest.raises(PhysicalIssueFenceError, match="capability"):
                gate.require_native_effect(
                    self_id="A", native_session_id="native-A",
                    effect=effect, action_id=action,
                )
        gate.require_native_effect(
            self_id="A", native_session_id="native-A",
            effect="set_control", action_id="move-A-start",
        )
        with pytest.raises(PhysicalIssueFenceError, match="capability"):
            gate.require_native_effect(
                self_id="A", native_session_id="native-A",
                effect="set_control", action_id="move-A-start",
            )
        with pytest.raises(PhysicalIssueFenceError, match="rebind"):
            gate.bind_native_children(
                self_id="A", native_session_id="native-A",
                lease_action_id="move-A", parent_action_id="move-A",
                family="MOVE", journal=journal,
            )
        gate.require_native_effect(
            self_id="A", native_session_id="native-A",
            effect="clear_controls", action_id="move-A-stop",
        )
        with pytest.raises(PhysicalIssueFenceError, match="capability"):
            gate.require_native_effect(
                self_id="A", native_session_id="native-A",
                effect="clear_controls", action_id="move-A-stop",
            )


def test_original_issuer_deferred_eat_and_attack_children_match_original_wal(tmp_path):
    args = _selected(tmp_path)
    gate = PhysicalIssueAdmission(
        {"A": "native-A"}, resident_mode=True, allow_resident_move=True,
    )
    # Without canonical PREPARED, an arbitrary L1 selected parent may NOT
    # register native EAT/ATTACK children.
    for family, effect in (("EAT", "consume_held"), ("ATTACK", "attack_entity")):
        with gate.lease(
            self_id="A", native_session_id="native-A",
            action_id="l1-admission", effect_family=family,
            defer_selected_children=True,
        ):
            with pytest.raises(PhysicalIssueFenceError, match="capability"):
                gate.require_native_effect(
                    self_id="A", native_session_id="native-A",
                    effect=effect, action_id="forged-other-parent",
                )
            with pytest.raises(PhysicalIssueFenceError, match="PREPARED"):
                gate.bind_native_children(
                    self_id="A", native_session_id="native-A",
                    lease_action_id="l1-admission",
                    parent_action_id="forged-other-parent",
                    family=family, journal=args["journal"],
                )


def test_original_move_uncertain_keeps_wal_and_blocks_a_retirement(tmp_path):
    gate = PhysicalIssueAdmission(
        {"A": "native-A", "B": "native-B"},
        resident_mode=True, allow_resident_move=True,
    )
    s = ScriptedNative("native-A", bad_stop=True)
    s.gate = lambda native, effect, action: gate.require_native_effect(
        self_id="A", native_session_id=native,
        effect=effect, action_id=action,
    )
    args = _selected(tmp_path)

    async def scenario():
        with pytest.raises((PhysicalMoveRefusal, PhysicalJournalError)):
            await gate.issue_move(s, **args)
        assert args["journal"].unresolved
        original = PhysicalActionJournal.restore(args["journal"].path, self_id="A")
        assert original.unresolved
        fence = gate.quarantine_resident(self_id="A", native_session_id="native-A")
        with pytest.raises(PhysicalJournalUnresolved):
            gate.retire_resident(
                self_id="A", native_session_id="native-A",
                fence_ref=fence.fence_ref,
                physical_wal_file=args["journal"].path,
            )
        with gate.lease(
            self_id="B", native_session_id="native-B",
            action_id="peer-action", effect_family="EAT",
        ):
            gate.require_native_effect(
                self_id="B", native_session_id="native-B",
                effect="consume_held", action_id="peer-action",
            )

    asyncio.run(scenario())


def test_original_move_no_net_is_settled_failure_not_unresolved_or_success(tmp_path):
    gate = PhysicalIssueAdmission(
        {"A": "native-A", "B": "native-B"},
        resident_mode=True, allow_resident_move=True,
    )
    s = ScriptedNative("native-A")
    original_send = s.send_set_control

    async def no_motion(action_id, *, control, state):
        await original_send(action_id, control=control, state=state)
        s.x = 1.0

    s.send_set_control = no_motion
    s.gate = lambda native, effect, action: gate.require_native_effect(
        self_id="A", native_session_id=native,
        effect=effect, action_id=action,
    )
    args = _selected(tmp_path)

    async def scenario():
        receipt = await gate.issue_move(s, **args)
        assert receipt.terminal.state is ActionState.OUTCOME
        assert receipt.displacement_m == 0.0
        assert receipt.skill_success_attested is False
        assert receipt.paper_causal_attribution is False
        assert receipt.native_start_dispatch_monotonic_ns > 0
        assert len(s.sent_commands) == 2  # One start and one STOP, never retry.
        saved = PhysicalActionJournal.restore(args["journal"].path, self_id="A")
        assert not saved.unresolved
        assert saved.records[-1]["status"] == "NATIVE_MOVE_NO_NET_DISPLACEMENT"
        fence = gate.quarantine_resident(self_id="A", native_session_id="native-A")
        retired = gate.retire_resident(
            self_id="A", native_session_id="native-A",
            fence_ref=fence.fence_ref, physical_wal_file=args["journal"].path,
        )
        assert retired.physical_wal_clear
        assert gate.resident_states["A"] == "OFFLINE"
        assert gate.resident_states["B"] == "ONLINE"
        with gate.lease(
            self_id="B", native_session_id="native-B",
            action_id="peer-action", effect_family="EAT",
        ):
            gate.require_native_effect(
                self_id="B", native_session_id="native-B",
                effect="consume_held", action_id="peer-action",
            )

    asyncio.run(scenario())


@pytest.mark.parametrize("state", [False, True])
def test_opt_in_move_never_leaks_into_global_or_default_resident(state):
    gate = PhysicalIssueAdmission(
        {"A": "native-A", "B": "native-B"}, resident_mode=state,
    )
    with pytest.raises(PhysicalIssueFenceError, match="MOVE"):
        with gate.lease(
            self_id="A", native_session_id="native-A",
            action_id="move-A", effect_family="MOVE",
        ):
            pytest.fail("unqualified MOVE acquired original native issuer")


def test_canonical_move_row_rejects_fake_settle_timing(tmp_path):
    args = _selected(tmp_path)
    journal = args["journal"]
    binding = args["proposal"].binding
    journal.prepare_move(binding, args["current_probe"])
    receipt = PhysicalActionJournal.restore(journal.path, self_id="A")
    assert receipt.unresolved
    p1 = _probe("native-A", 5, "stop-initial", 120, 1.8)
    p2 = _probe("native-A", 6, "stop-first", 124, 1.8)
    p3 = _probe("native-A", 7, "stop-settled", 136, 1.8)
    source = Provenance("original-test", "move")
    proposal = args["proposal"].proposal.authorize(
        at_ns=4, provenance=source, authority="operator-propose",
    )
    supervisor = args["supervisor"]
    supervisor.issue(
        proposal, at_ns=5, deadline_ns=100, provenance=source,
    )
    terminal = supervisor.record_outcome(
        binding.action_id, at_ns=6, provenance=source,
    )
    with pytest.raises(PhysicalJournalError, match="8\\+8"):
        journal.close_move(
            binding, args["current_probe"],
            MineflayerEffectResult("native-A", 3, "move-A-start", "set_control", "applied", None),
            MineflayerEffectResult("native-A", 4, "move-A-stop", "clear_controls", "applied", None),
            p1, p2, p3, terminal, supervisor,
        )
    assert journal.unresolved
