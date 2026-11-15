"""No real Mineflayer/Paper/LLM: bounded MOVE WAL and STOP negative tests."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterStarted,
    MineflayerEffectResult,
    MineflayerLaunchConfig,
    MineflayerPosition,
)
from experiments.cognitive_move_paper_witness_dev import (
    PaperMoveWitnessError,
    PaperMoveWitnessSession,
)
from experiments.cognitive_move_target_resolution import resolve_selected_move_target
from experiments.cognitive_physical_eat_issue_dev import (
    PhysicalEatGrant,
    PhysicalGrantStage,
)
from experiments.cognitive_physical_move_issue_dev import (
    PhysicalMoveRefusal,
    issue_selected_move_dev,
)
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.physical_action_journal import (
    PhysicalActionJournal,
    PhysicalJournalError,
    PhysicalJournalUnresolved,
    _validate,
)
from relay_self.physical_action_port import (
    PhysicalActionBinding,
    PhysicalCapability,
    PhysicalReadback,
    propose_bound_physical_action,
)
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution
from test_cognitive_minimal_minecraft_dev import observation
from test_cognitive_move_paper_witness_dev import _data as paper_data
from test_cognitive_move_paper_witness_dev import _qualified as paper_qualified
from test_cognitive_move_target_resolution import prepare, select
from test_cognitive_physical_eat_issue_dev import OwnedFakeNative
from test_cognitive_physical_eat_issue_dev import run as eat_run
from test_cognitive_physical_eat_issue_dev import setup as eat_setup


class MoveNative(OwnedFakeNative):
    def __init__(self, events, *, failure=None):
        super().__init__(events)
        self.failure = failure
        self._started = MineflayerAdapterStarted(
            "world-A", 0, "4.39.0", MineflayerLaunchConfig(),
        )

    async def send_look(self, action_id, *, yaw, pitch):
        assert self.journal is not None
        self.wal_at_first_native_send = json.loads(
            self.journal.path.read_text()
        )["body"]["actions"][-1]["status"]
        self.sent.append(("look", action_id, yaw, pitch))

    async def send_set_control(self, action_id, *, control, state):
        self.sent.append(("set_control", action_id, control, state))
        if self.failure == "cancel_after_forward":
            raise asyncio.CancelledError()

    async def send_clear_controls(self, action_id):
        self.sent.append(("clear_controls", action_id))

    async def send_observe(self, request_id=None):
        self.sent.append(("observe", request_id))


def shifted(obs, x):
    return replace(
        obs, snapshot=replace(
            obs.snapshot, position=MineflayerPosition(x, 64, 0),
        ),
    )


def setup(tmp_path, *, bad=None):
    native, scenario, percept, frame = prepare()
    selected = select(frame)
    target = resolve_selected_move_target(
        selected, frame=frame, percept=percept,
        current_probe=native, scenario=scenario,
    )
    previous = observation(
        11, session_id="world-A", request_id="previous-source", food=20,
    )
    owner = IntentCommitment()
    prov = Provenance("test-move-owner", "original")
    owner.commit("intent-M", objective="EXPLORE_WORLD", at_ns=1, provenance=prov)
    skill = SkillExecution.start(
        "skill-M", skill_id="MOVE", intent_commitment=owner,
        at_ns=2, provenance=prov,
    )
    supervisor = ActionSupervisor()
    binding = PhysicalActionBinding(
        scope=frame.scope, intent_id="intent-M", goal_id="EXPLORE_WORLD",
        skill_id="MOVE", skill_version=1,
        skill_execution_id="skill-M", action_id="action-M",
        capability_ref="MOVE", capability_version=1,
        body_channel="movement", target_kind="DESTINATION",
        target_ref=selected.option.target_ref, native_seq=native.seq,
        native_request_id=native.request_id,
        native_source=native.provenance,
    )
    readback = PhysicalReadback(
        frame.scope, native.provenance, native.seq, native.request_id,
        (binding.target_ref,), True,
    )
    proposal = propose_bound_physical_action(
        binding, capability=PhysicalCapability(
            "MOVE", 1, "movement", "DESTINATION", True,
        ), readback=readback, intent_owner=owner,
        skill_execution=skill, supervisor=supervisor, at_ns=3,
        provenance=prov,
    )
    journal = PhysicalActionJournal.create(
        tmp_path / "shared-physical.json", self_id="self-A",
    )
    look = MineflayerEffectResult(
        "world-A", 13, "action-M-look", "look", "applied", None,
    )
    forward = MineflayerEffectResult(
        "world-A", 14, "action-M-forward", "set_control", "applied", None,
    )
    progress = shifted(observation(
        15, kind="move", session_id="world-A", food=20,
    ), .5)
    stop = MineflayerEffectResult(
        "world-A", 16, "action-M-stop", "clear_controls", "applied", None,
    )
    first = shifted(observation(
        17, session_id="world-A", request_id="action-M-after-stop-00",
        food=20,
    ), .6)
    final = shifted(observation(
        18, session_id="world-A", request_id="action-M-after-stop-01",
        food=20,
    ), .61)
    events = [look, forward, progress, stop, first, final]
    if bad == "look_rejected":
        events[0] = replace(look, result="rejected", error="denied")
    elif bad == "forward_absent":
        events = [look]
    elif bad == "progress_wrong_direction":
        events[2] = shifted(progress, -.5)
    elif bad == "stop_rejected":
        events[3] = replace(stop, result="rejected", error="stop_denied")
    elif bad == "stop_probe_wrong_id":
        events[4] = replace(first, request_id="foreign-request")
    elif bad == "unstable_stop":
        events[5] = shifted(final, .85)
    elif bad == "no_second_stop_probe":
        events = events[:5]
    elif bad == "forced_move":
        events[2] = replace(progress, kind="forcedMove")
    elif bad == "vertical_stop_drift":
        events[5] = replace(
            final, snapshot=replace(
                final.snapshot, position=MineflayerPosition(.61, 64.2, 0),
            ),
        )
    elif bad == "foreign_source":
        events[2] = replace(progress, session_id="foreign-world")
    elif bad == "cancel_after_forward":
        events = [look]
    session = MoveNative(events, failure=bad)
    session.journal = journal
    grant1 = PhysicalEatGrant(
        PhysicalGrantStage.PROPOSE, "owner-propose",
        Provenance("test-physical-grant", "propose"),
        "intent-M", "action-M", "world-A", 12, "move-probe-12",
        binding.target_ref, True,
    )
    grant2 = PhysicalEatGrant(
        PhysicalGrantStage.ISSUE, "owner-issue",
        Provenance("test-physical-grant", "issue"),
        "intent-M", "action-M", "world-A", 12, "move-probe-12",
        binding.target_ref, True,
    )
    kw = dict(
        proposal=proposal, target=target,
        previous_probe=previous, current_probe=native,
        propose_grant=grant1, issue_grant=grant2,
        intent_owner=owner, skill_execution=skill, supervisor=supervisor,
        journal=journal, at_ns=4, provenance=prov,
        grant_real_world=True,
        acknowledge_dev_unverified_principal=True,
        evidence_timeout_s=.1, stop_probe_interval_s=.15,
    )
    return kw, session


def run(kw, session):
    return asyncio.run(issue_selected_move_dev(session, **kw))


def test_bounded_native_move_fsyncs_one_parent_before_look_and_checks_two_stop_probes(tmp_path):
    kw, session = setup(tmp_path)
    result = run(kw, session)
    assert result.status == "NATIVE_MOVE_PROGRESS_STOP_READBACK_DEV_ONLY"
    assert result.arrived_at_destination is False
    assert result.paper_stop_settled_attested is False
    assert result.terminal.state is ActionState.OUTCOME
    assert result.distance_advanced == pytest.approx(.5)
    assert result.residual_motion == pytest.approx(.01)
    assert session.wal_at_first_native_send == "PREPARED_UNRESOLVED"
    assert [x[0] for x in session.sent] == [
        "look", "set_control", "clear_controls", "observe", "observe",
    ]
    assert session.sent[2] == ("clear_controls", "action-M-stop")
    assert kw["skill_execution"].state.value == "started"
    restored = PhysicalActionJournal.restore(kw["journal"].path, self_id="self-A")
    assert restored.unresolved is False
    assert restored.records[-1]["status"] == "NATIVE_MOVE_PROGRESS_STOP_READBACK"
    assert restored.records[-1]["capability"] == "MOVE"
    assert restored.records[-1]["effect_seqs"] == [13, 14, 16]
    assert restored.records[-1]["after_seq"] == 18
    assert restored.records[-1]["motion"]["stop_probe_seqs"] == [17, 18]
    assert restored.digest == kw["journal"].digest
    with pytest.raises((PhysicalMoveRefusal, PhysicalJournalUnresolved)):
        run(kw, session)
    assert len([x for x in session.sent if x[0] == "set_control"]) == 1


@pytest.mark.parametrize("bad", [
    "look_rejected", "forward_absent", "progress_wrong_direction",
    "stop_rejected", "stop_probe_wrong_id", "unstable_stop",
    "no_second_stop_probe", "foreign_source", "cancel_after_forward",
    "forced_move", "vertical_stop_drift",
])
def test_unknown_motion_requires_stop_no_replay_and_wal_survives_restart(tmp_path, bad):
    kw, session = setup(tmp_path, bad=bad)
    with pytest.raises((RuntimeError, ValueError, asyncio.CancelledError)):
        run(kw, session)
    row = kw["journal"].records[-1]
    assert row["status"] == "PREPARED_UNRESOLVED"
    assert kw["supervisor"].get("action-M").state is ActionState.UNKNOWN
    saved = PhysicalActionJournal.restore(kw["journal"].path, self_id="self-A")
    assert saved.unresolved
    if bad in ("forward_absent", "progress_wrong_direction", "cancel_after_forward"):
        assert len([x for x in session.sent if x[0] == "clear_controls"]) == 1
    else:
        assert len([x for x in session.sent if x[0] == "clear_controls"]) <= 1
    with pytest.raises(PhysicalJournalUnresolved):
        run({**kw, "journal": saved}, session)
    assert len([x for x in session.sent if x[0] == "set_control"]) <= 1


@pytest.mark.parametrize("bad", [
    "no_grant", "stale_grant", "bad_target_geometry", "changed_native_position",
    "unstable_body", "wrong_world", "wrong_source", "busy_owner",
    "unsupported_vertical", "out_of_bounds_distance",
    "forged_yaw", "forged_horizontal_distance",
])
def test_preissue_move_negative_never_writes_wal_or_native(tmp_path, bad):
    kw, session = setup(tmp_path)
    if bad == "no_grant":
        kw["grant_real_world"] = False
    elif bad == "stale_grant":
        kw["issue_grant"] = replace(kw["issue_grant"], probe_seq=99)
    elif bad == "bad_target_geometry":
        kw["target"] = replace(
            kw["target"], destination_position=MineflayerPosition(2, 64, 0),
        )
    elif bad == "changed_native_position":
        kw["current_probe"] = shifted(kw["current_probe"], .3)
    elif bad == "unstable_body":
        kw["previous_probe"] = shifted(kw["previous_probe"], -.2)
    elif bad == "wrong_world":
        kw["current_probe"] = replace(
            kw["current_probe"], session_id="another-world",
        )
    elif bad == "wrong_source":
        kw["current_probe"] = replace(
            kw["current_probe"], seq=99,
        )
    elif bad == "busy_owner":
        kw["intent_owner"].invalidate(
            "intent-M", reason="withdrawn", at_ns=3,
            provenance=Provenance("test", "withdraw"),
        )
    elif bad == "unsupported_vertical":
        kw["target"] = replace(kw["target"], vertical_delta=2)
    elif bad == "out_of_bounds_distance":
        kw["target"] = replace(kw["target"], horizontal_distance=5)
    elif bad == "forged_yaw":
        kw["target"] = replace(kw["target"], yaw_rad=.5)
    elif bad == "forged_horizontal_distance":
        kw["target"] = replace(kw["target"], horizontal_distance=2.5)
    with pytest.raises((ValueError, RuntimeError)):
        run(kw, session)
    assert kw["journal"].records == ()
    assert kw["supervisor"].recorded_actions == ()
    assert session.sent == []


def test_unresolved_attack_or_eat_wal_prevents_new_motion(tmp_path):
    kw, session = setup(tmp_path)
    journal = kw["journal"]
    journal.prepare_move(
        kw["proposal"].binding, kw["current_probe"],
        destination_id="waypoint-1",
        destination=kw["target"].destination_position,
        destination_source=kw["target"].destination_provenance,
    )
    reopened = PhysicalActionJournal.restore(journal.path, self_id="self-A")
    assert reopened.unresolved
    with pytest.raises(PhysicalJournalUnresolved):
        run({**kw, "journal": reopened}, session)
    assert session.sent == []


def test_move_wal_validates_geometry_digest_and_three_dimensional_stop_probes(
    tmp_path,
):
    """A recalculated file checksum alone cannot validate forged MOVE evidence."""
    import copy

    kw, session = setup(tmp_path)
    effect = run(kw, session)
    assert effect.terminal.state is ActionState.OUTCOME
    body = {
        "schema": 1, "self_id": "self-A",
        "actions": [copy.deepcopy(kw["journal"].records[-1])],
    }
    _validate(body)
    for tamper in ("target", "stop_y", "wrong_command_order", "missing_stop"):
        altered = copy.deepcopy(body)
        row = altered["actions"][0]
        if tamper == "target":
            row["motion"]["target"][0] = 3.5
        elif tamper == "stop_y":
            row["motion"]["stop_probe_positions"][1][1] = 64.2
        elif tamper == "wrong_command_order":
            row["effect_seqs"][2] = row["effect_seqs"][1]
        else:
            row["effect_seqs"] = row["effect_seqs"][:2]
        with pytest.raises(PhysicalJournalError):
            _validate(altered)


def test_same_self_eat_then_move_reuses_one_physical_wal_and_seq_barrier(tmp_path):
    eat_kw, eat_session, _, _ = eat_setup(tmp_path)
    meal = eat_run(eat_kw, eat_session)
    assert meal.terminal.state is ActionState.OUTCOME
    assert eat_kw["journal"].records[0]["status"] == "NATIVE_EAT_OUTCOME"

    kw, session = setup(tmp_path)
    joined = PhysicalActionJournal.restore(
        eat_kw["journal"].path, self_id="self-A",
    )
    kw["journal"] = joined
    session.journal = joined
    # EAT last after_seq=15; MOVE native probe must advance beyond it.
    prev = replace(kw["previous_probe"], seq=21, request_id="before-next")
    cur = replace(kw["current_probe"], seq=22, request_id="next-move-probe")
    kw["previous_probe"], kw["current_probe"] = prev, cur
    kw["target"] = replace(
        kw["target"], native_seq=22,
        native_request_id="next-move-probe",
        native_probe_provenance=cur.provenance,
    )
    binding = replace(
        kw["proposal"].binding, native_seq=22,
        native_request_id="next-move-probe", native_source=cur.provenance,
    )
    readback = PhysicalReadback(
        binding.scope, cur.provenance, 22, "next-move-probe",
        (binding.target_ref,), True,
    )
    kw["proposal"] = propose_bound_physical_action(
        binding, capability=PhysicalCapability(
            "MOVE", 1, "movement", "DESTINATION", True,
        ), readback=readback, intent_owner=kw["intent_owner"],
        skill_execution=kw["skill_execution"], supervisor=kw["supervisor"],
        at_ns=3, provenance=kw["provenance"],
    )
    for k in ("propose_grant", "issue_grant"):
        kw[k] = replace(
            kw[k], probe_seq=22, probe_request_id="next-move-probe",
        )
    session.events = [replace(x, seq=x.seq + 10) for x in session.events]
    result = run(kw, session)
    assert result.terminal.state is ActionState.OUTCOME
    restored = PhysicalActionJournal.restore(joined.path, self_id="self-A")
    assert [x["capability"] for x in restored.records] == ["EAT", "MOVE"]
    assert [x["status"] for x in restored.records] == [
        "NATIVE_EAT_OUTCOME", "NATIVE_MOVE_PROGRESS_STOP_READBACK",
    ]
    assert restored.records[0]["after_seq"] < restored.records[1]["probe_seq"]
    assert restored.digest == joined.digest
    assert session.wal_at_first_native_send == "PREPARED_UNRESOLVED"


def test_move_terminal_disk_close_failure_does_not_resolve_wal(tmp_path, monkeypatch):
    """Even an in-memory Action OUTCOME must never override unresolved disk."""
    kw, session = setup(tmp_path)
    original_commit = kw["journal"]._commit

    def disk_failure(records):
        if records[-1]["status"] == "NATIVE_MOVE_PROGRESS_STOP_READBACK":
            raise OSError("simulated final journal fsync failure")
        return original_commit(records)

    monkeypatch.setattr(kw["journal"], "_commit", disk_failure)
    with pytest.raises(OSError, match="fsync"):
        run(kw, session)
    assert kw["supervisor"].get("action-M").state is ActionState.OUTCOME
    assert kw["journal"].unresolved
    reopened = PhysicalActionJournal.restore(
        kw["journal"].path, self_id="self-A",
    )
    assert reopened.records[-1]["status"] == "PREPARED_UNRESOLVED"
    with pytest.raises(PhysicalJournalUnresolved):
        run({**kw, "journal": reopened}, session)
    assert len([x for x in session.sent if x[0] == "set_control"]) == 1


class FakeQualifiedPaper(PaperMoveWitnessSession):
    """No Java/Paper process; verifies exact observer ordering only."""

    def __init__(self, session, journal, target, *, bad=None):
        self.session = session
        self.journal = journal
        self.native_start = target.native_position
        self.native_target = target.destination_position
        self.action_id = "action-M"
        self.native_session_id = "world-A"
        raw, log = paper_data()
        sample = paper_qualified(raw, log)
        self.world_uuid = sample.world_uuid
        self.actor_uuid = sample.actor_uuid
        self.proof = replace(
            sample, action_id=self.action_id, native_session_id=self.native_session_id,
            actor_name_joined=True,
        )
        self.bad = bad
        self.events = []
        self.armed = False
        self.marked = False

    async def arm(self, seconds=3.0):
        assert self.journal.records[-1]["status"] == "PREPARED_UNRESOLVED"
        assert self.session.sent == []
        self.armed = True
        self.events.append("paper-arm-before-look")

    async def mark_stop_after_ack(self, seconds=3.0):
        assert self.armed
        assert self.session.sent[-1] == ("clear_controls", "action-M-stop")
        self.marked = True
        self.events.append("paper-stop-mark-after-native-ack")

    async def finish(self, seconds=6.0):
        assert self.marked
        assert [x[0] for x in self.session.sent][-2:] == ["observe", "observe"]
        self.events.append("paper-final-16tick-proof")
        if self.bad == "unavailable":
            raise PaperMoveWitnessError("missing independent Paper trace")
        if self.bad == "foreign_action":
            return replace(self.proof, action_id="wrong-parent")
        return self.proof


def test_paper_observer_is_armed_before_native_and_checked_before_wal_close(tmp_path):
    kw, session = setup(tmp_path)
    paper = FakeQualifiedPaper(session, kw["journal"], kw["target"])
    receipt = asyncio.run(issue_selected_move_dev(
        session, paper_witness=paper, **kw,
    ))
    assert receipt.terminal.state is ActionState.OUTCOME
    assert receipt.paper_proof is paper.proof
    assert paper.events == [
        "paper-arm-before-look",
        "paper-stop-mark-after-native-ack",
        "paper-final-16tick-proof",
    ]
    restored = PhysicalActionJournal.restore(kw["journal"].path, self_id="self-A")
    assert not restored.unresolved
    assert restored.records[-1]["status"] == "NATIVE_MOVE_PROGRESS_STOP_READBACK"
    assert receipt.paper_stop_settled_attested is False
    assert receipt.arrived_at_destination is False


@pytest.mark.parametrize("failure", ["unavailable", "foreign_action"])
def test_paper_mismatch_after_native_stop_preserves_unresolved_parent(
    tmp_path, failure,
):
    kw, session = setup(tmp_path)
    paper = FakeQualifiedPaper(
        session, kw["journal"], kw["target"], bad=failure,
    )
    with pytest.raises((PhysicalMoveRefusal, PaperMoveWitnessError)):
        asyncio.run(issue_selected_move_dev(
            session, paper_witness=paper, **kw,
        ))
    assert paper.events[-1] == "paper-final-16tick-proof"
    assert kw["supervisor"].get("action-M").state is ActionState.UNKNOWN
    assert PhysicalActionJournal.restore(
        kw["journal"].path, self_id="self-A",
    ).unresolved
    assert len([x for x in session.sent if x[0] == "clear_controls"]) == 1


def test_preused_paper_watch_refused_before_wal_and_any_motor(tmp_path):
    kw, session = setup(tmp_path)
    paper = FakeQualifiedPaper(session, kw["journal"], kw["target"])
    paper.armed = True
    with pytest.raises(PhysicalMoveRefusal, match="pre-used"):
        asyncio.run(issue_selected_move_dev(
            session, paper_witness=paper, **kw,
        ))
    assert kw["journal"].records == ()
    assert session.sent == []
