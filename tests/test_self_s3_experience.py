"""S3 offline only: original typed S16 receipt becomes historical Memory context."""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_action_feedback_qualification as s17
from adapters.mineflayer.normal_action import NormalActionReceipt
from adapters.mineflayer.self_s3_experience import S3ReadOnlyExperience
from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.experience_bridge import ExperienceRejected, ReuseStatus
from relay_self.persistent_cognition import load_persistent_cognition, save_persistent_cognition
from relay_self.provenance import Provenance


def fixture():
    import test_postmain_s42_world_contrast as s42

    *_, consequence, outcome, closed = s17.executed_closed_chain()
    _, near, _, _, _ = s42._pair()
    original = consequence.before_observation
    # Synthetic sourced cue only; does not invent genuine physical World evidence.
    snapshot = replace(
        original.snapshot,
        nearby_entities=near.observation.snapshot.nearby_entities,
        nearby_entities_coverage=near.observation.snapshot.nearby_entities_coverage,
    )
    probe = replace(original, snapshot=snapshot, request_id="s2-qualified-probe")
    assert consequence.after_observation.seq == 4
    receipt = NormalActionReceipt(closed, consequence, probe.provenance, outcome)
    return receipt, probe


def test_observation_to_memory_to_next_read_only_hint(tmp_path):
    receipt, probe = fixture()
    sid = probe.session_id
    bridge = S3ReadOnlyExperience(sid)
    base = bridge.hint_for_next(probe)
    assert base.status is ReuseStatus.UNKNOWN
    assert len(bridge.snapshot.memories) == 0
    entry = bridge.observe_original(
        receipt, correlated_probe=probe, expected_action_id=receipt.terminal.action_id,
    )
    assert entry.session_id == sid
    assert entry.evidence_sha256 and len(entry.evidence_sha256) == 64
    assert len(bridge.snapshot.memories) == 1
    # Same World session, later source frame, historical reference only.
    next_probe = replace(probe, seq=5, request_id="s2-next-probe")
    hint = bridge.hint_for_next(next_probe)
    assert hint.status is ReuseStatus.RECALL
    assert hint.memory_ids == (entry.memory_id,)
    assert hint.observed_action_refs == ("MOVE_BACKWARD",)
    assert "observation_only" in hint.reason
    assert not hasattr(hint, "authorization")
    assert not hasattr(hint, "issue")
    # Existing Memory owner can persist without adding a DB or schema version.
    path = tmp_path / "owner.json"
    save_persistent_cognition(path, bridge.snapshot)
    assert load_persistent_cognition(path) == bridge.snapshot
    assert receipt.terminal.is_current_snapshot
    assert receipt.outcome_interpretation == fixture()[0].outcome_interpretation


def test_unknown_unverified_stale_no_cross_session_or_habit():
    receipt, probe = fixture()
    bridge = S3ReadOnlyExperience(probe.session_id, lookback=1)
    bridge.observe_original(
        receipt, correlated_probe=probe, expected_action_id=receipt.terminal.action_id,
    )
    late = replace(probe, seq=99, request_id="fresh-probe")
    assert bridge.hint_for_next(late).status is ReuseStatus.STALE
    assert bridge.snapshot.appraisal_dispositions == ()
    with pytest.raises(ExperienceRejected, match="source-qualified"):
        bridge.hint_for_next(replace(probe, session_id="foreign"))
    with pytest.raises(ExperienceRejected, match="source-qualified"):
        bridge.hint_for_next(replace(probe, request_id=None))
    with pytest.raises(ExperienceRejected, match="bounded"):
        S3ReadOnlyExperience(probe.session_id, lookback=65)


@pytest.mark.parametrize("tamper", [
    "missing_s16", "foreign_consequence", "foreign_probe",
    "wrong_source", "unknown", "binding", "hypothetical",
])
def test_unauthenticated_or_nonterminal_cannot_be_retained(tamper):
    receipt, probe = fixture()
    bridge = S3ReadOnlyExperience(probe.session_id)
    if tamper == "missing_s16":
        receipt = replace(receipt, outcome_interpretation=None)
    elif tamper == "foreign_consequence":
        receipt = replace(receipt, consequence=replace(
            receipt.consequence, session_id="foreign"
        ))
    elif tamper == "foreign_probe":
        probe = replace(probe, session_id="foreign")
    elif tamper == "wrong_source":
        receipt = replace(receipt, source=Provenance("fabricated", "foreign"))
    elif tamper == "unknown":
        receipt = replace(receipt, outcome_interpretation=replace(
            receipt.outcome_interpretation, disposition=ActionOutcomeDisposition.UNKNOWN
        ))
    elif tamper == "binding":
        receipt = replace(receipt, outcome_interpretation=replace(
            receipt.outcome_interpretation, binding_id="foreign-binding"
        ))
    elif tamper == "hypothetical":
        receipt = replace(receipt, outcome_interpretation=replace(
            receipt.outcome_interpretation, action_ref="hypothetical"
        ))
    with pytest.raises(ExperienceRejected):
        bridge.observe_original(
        receipt, correlated_probe=probe, expected_action_id=receipt.terminal.action_id,
    )
    assert bridge.snapshot.memories == ()


def test_no_zombie_cue_never_launders_prior_escape_into_current_context():
    receipt, probe = fixture()
    bridge = S3ReadOnlyExperience(probe.session_id)
    bridge.observe_original(
        receipt, correlated_probe=probe,
        expected_action_id=receipt.terminal.action_id,
    )
    bare = replace(probe, snapshot=receipt.consequence.before_observation.snapshot)
    with pytest.raises(ExperienceRejected, match="near-zombie"):
        S3ReadOnlyExperience(probe.session_id).observe_original(
            receipt, correlated_probe=bare,
            expected_action_id=receipt.terminal.action_id,
        )
    no_threat_next = replace(
        bare, seq=5, request_id="qualified-safe-world-probe",
    )
    hint = bridge.hint_for_next(no_threat_next)
    assert hint.status is ReuseStatus.UNKNOWN
    assert hint.observed_action_refs == ()
    import test_postmain_s42_world_contrast as s42

    _, _, far, _, _ = s42._pair()
    # An authentic but distant zombie also must not reuse a near-threat cue.
    far_snapshot = replace(
        no_threat_next.snapshot,
        nearby_entities=far.observation.snapshot.nearby_entities,
        nearby_entities_coverage=far.observation.snapshot.nearby_entities_coverage,
    )
    distant = replace(no_threat_next, snapshot=far_snapshot)
    assert bridge.hint_for_next(distant).status is ReuseStatus.UNKNOWN


def test_original_source_cannot_be_counted_twice():
    receipt, probe = fixture()
    bridge = S3ReadOnlyExperience(probe.session_id)
    bridge.observe_original(
        receipt, correlated_probe=probe, expected_action_id=receipt.terminal.action_id,
    )
    with pytest.raises(ExperienceRejected):
        bridge.observe_original(
        receipt, correlated_probe=probe, expected_action_id=receipt.terminal.action_id,
    )
    assert len(bridge.snapshot.memories) == 1


def test_future_source_or_unbounded_history_never_qualifies_current():
    receipt, probe = fixture()
    bridge = S3ReadOnlyExperience(probe.session_id)
    bridge.observe_original(
        receipt, correlated_probe=probe, expected_action_id=receipt.terminal.action_id,
    )
    earlier = replace(probe, seq=2, request_id="different-probe")
    assert bridge.hint_for_next(earlier).status is ReuseStatus.STALE
    very_late = replace(probe, seq=80, request_id="late-probe")
    assert bridge.hint_for_next(very_late).status is ReuseStatus.STALE


def test_s49_callback_reads_memory_before_current_l0_without_grant(monkeypatch, tmp_path):
    """Same S1 callback path consumes read-only context, never selects an Action."""
    import asyncio
    import json
    from types import SimpleNamespace

    import test_postmain_s42_world_contrast as s42
    from adapters.mineflayer import self_s1_runtime as s1
    from adapters.mineflayer.normal_action import NormalWorldL0
    from adapters.mineflayer.self_continuous_host import AppendOnlySessionEvents

    receipt, first_probe = fixture()
    bridge = S3ReadOnlyExperience(first_probe.session_id)
    bridge.observe_original(
        receipt, correlated_probe=first_probe,
        expected_action_id=receipt.terminal.action_id,
    )
    retained, near, _, old_event, _ = s42._pair()
    sid = first_probe.session_id
    new_event = replace(old_event, session_id=sid, seq=5)
    new_probe = replace(
        near.observation, session_id=sid, seq=6, request_id="next-s1-actual-probe",
    )
    session = SimpleNamespace(started=SimpleNamespace(session_id=sid))
    host = NormalWorldL0(
        sid, "escape-threat", retained, max_events=1, max_action_requests=1,
    )
    async def original_correlated(owner, request_id):
        assert owner is session
        return new_probe

    async def forbidden(*args):
        raise AssertionError("Memory retrieval issued an Action")

    monkeypatch.setattr(s1, "_correlated_observe", original_correlated)
    sink = AppendOnlySessionEvents(tmp_path / "s1-existing-events.jsonl", sid)
    try:
        reprobe, _, on_action = s1.s49_callbacks(
            session, host, SimpleNamespace(intent=object(), execute=forbidden),
            experience=bridge, events=sink,
        )
        result = asyncio.run(reprobe(new_event))
        assert result is new_probe
        rows = [json.loads(x) for x in sink.path.read_text().splitlines()]
        assert len(rows) == 1
        assert rows[0]["kind"] == "experience_read_only_hint"
        assert rows[0]["status"] == "recall"
        assert rows[0]["observed_action_refs"] == ["MOVE_BACKWARD"]
        assert rows[0]["action_authority"] is False
        assert rows[0]["learning_updates"] == rows[0]["habit_grants"] == 0
        assert host.events == host.action_requests == 0
        assert callable(on_action)  # Still the original owner-only callback.
    finally:
        sink.close()
